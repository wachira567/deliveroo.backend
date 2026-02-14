from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import ParcelOrder, User, Payment, Notification
from extensions import db
from utils import get_distance_matrix, get_geocode, create_notification, send_order_status_email, role_required

orders_bp = Blueprint('orders', __name__)


@orders_bp.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    import logging
    logger = logging.getLogger(__name__)
    logger.info("create_order called")
    
    try:
        current_user_id = get_jwt_identity()
        logger.info(f"create_order user_id: {current_user_id}")
        # Ensure ID is integer for DB
        try:
            current_user_id = int(current_user_id)
        except ValueError:
             return jsonify({"error": "Invalid user identity"}), 401
             
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if user.role != 'customer':
            return jsonify({"error": "Only customers can create orders"}), 403
        
        # Helper to get data regardless of content type
        if request.content_type.startswith('multipart/form-data'):
            data = request.form.to_dict()
            # Convert numeric types from strings
            if 'weight' in data: data['weight'] = float(data['weight'])
            if 'pickup_lat' in data: data['pickup_lat'] = float(data['pickup_lat']) if data['pickup_lat'] else None
            if 'pickup_lng' in data: data['pickup_lng'] = float(data['pickup_lng']) if data['pickup_lng'] else None
            if 'destination_lat' in data: data['destination_lat'] = float(data['destination_lat']) if data['destination_lat'] else None
            if 'destination_lng' in data: data['destination_lng'] = float(data['destination_lng']) if data['destination_lng'] else None
        else:
            data = request.get_json()
        
        # Validate required fields
        required_fields = ['parcel_name', 'weight', 'pickup_address', 'destination_address']
        for field in required_fields:
            if not data.get(field):
                return jsonify({"error": f"{field} is required"}), 400
        
        # Validate weight
        try:
            weight = float(data['weight'])
            if weight <= 0:
                return jsonify({"error": "Weight must be positive"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid weight"}), 400
        
        # Determine weight category
        if weight <= 1:
            weight_category = "small"
        elif weight <= 5:
            weight_category = "medium"
        elif weight <= 10:
            weight_category = "large"
        else:
            weight_category = "xlarge"
        
        # Geocode addresses
        logger.info("Geocoding addresses...")
        pickup_lat, pickup_lng = None, None
        destination_lat, destination_lng = None, None
        
        if data.get('pickup_lat') and data.get('pickup_lng'):
            pickup_lat = data['pickup_lat']
            pickup_lng = data['pickup_lng']
        else:
            pickup_lat, pickup_lng = get_geocode(data['pickup_address'])
        logger.info(f"Pickup geocode result: {pickup_lat}, {pickup_lng}")
        
        if data.get('destination_lat') and data.get('destination_lng'):
            destination_lat = data['destination_lat']
            destination_lng = data['destination_lng']
        else:
            destination_lat, destination_lng = get_geocode(data['destination_address'])
        logger.info(f"Destination geocode result: {destination_lat}, {destination_lng}")
        
        # Get distance if both coordinates are available
        distance = None
        if pickup_lat and pickup_lng and destination_lat and destination_lng:
            # Check for same location
            if (pickup_lat == destination_lat) and (pickup_lng == destination_lng):
                 distance = 0
            else:
                 try:
                    distance, _ = get_distance_matrix(
                        (pickup_lat, pickup_lng),
                        (destination_lat, destination_lng)
                    )
                 except Exception as e:
                     logger.error(f"Distance matrix error: {e}")
                     # proceed with default
            
            # Default distance if API fails
            if not distance:
                distance = 5.0
        else:
             distance = 5.0 # Default if geocoding fails
        logger.info(f"Calculated distance: {distance}")
        
        # Calculate price
        price = ParcelOrder.calculate_price(weight, distance)
        logger.info(f"Calculated price: {price}")
    
        # Generate 6-digit delivery code
        import random
        delivery_code = str(random.randint(100000, 999999))
        
        # Handle Image Upload
        parcel_image_url = None
        if request.files and 'parcel_image' in request.files:
            logger.info("Processing image upload...")
            file = request.files['parcel_image']
            if file and file.filename != '':
                from services.cloudinary_service import upload_image
                parcel_image_url = upload_image(file)
                logger.info(f"Image uploaded to: {parcel_image_url}")
        
        # Create order
        logger.info("Creating order object...")
        order = ParcelOrder(
            customer_id=current_user_id,
            parcel_name=data['parcel_name'],
            description=data.get('description'),
            weight=weight,
            weight_category=weight_category,
            pickup_address=data['pickup_address'],
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lng,
            destination_address=data['destination_address'],
            destination_lat=destination_lat,
            destination_lng=destination_lng,
            distance=distance,
            price=price,
            status="pending",
            parcel_image_url=parcel_image_url,
            delivery_code=delivery_code
        )
        
        logger.info("Adding to DB session...")
        db.session.add(order)
        logger.info("Committing to DB...")
        db.session.commit()
        logger.info(f"Order committed with ID: {order.id}")
        
        # Send email with delivery code
        try:
            from services.email_service import send_order_created_email
            # Get user email
            user_email = user.email
            order_data = order.to_dict()
            # to_dict doesn't include delivery_code for security in API, but we need it for email
            order_data['delivery_code'] = delivery_code
            
            send_order_created_email(user_email, order_data)
        except Exception as e:
            print(f"Failed to send email: {e}")
        
        # Create notification
        try:
            create_notification(
                user_id=current_user_id,
                order_id=order.id,
                message=f"Order #{order.id} created successfully",
                type_="order_created"
            )
        except Exception as e:
            print(f"Notification error: {e}")
            # Don't fail request if notification fails
        
        return jsonify({
            "message": "Order created successfully",
            "order": {
                "id": order.id,
                "parcel_name": order.parcel_name,
                "weight": order.weight,
                "weight_category": order.weight_category,
                "pickup_address": order.pickup_address,
                "destination_address": order.destination_address,
                "distance": order.distance,
                "price": order.price,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "parcel_image_url": order.parcel_image_url
            }
        }), 201

    except Exception as e:
        import traceback
        import logging
        logger = logging.getLogger(__name__)
        logger.error("ERROR IN CREATE_ORDER:")
        logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500


@orders_bp.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    # Get query parameters
    status_filter = request.args.get('status')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    query = ParcelOrder.query
    
    if user.role == 'customer':
        query = query.filter_by(customer_id=current_user_id)
    elif user.role == 'courier':
        query = query.filter_by(courier_id=current_user_id)
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    
    # Order by created_at desc
    query = query.order_by(ParcelOrder.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    orders = []
    for order in pagination.items:
        order_data = {
            "id": order.id,
            "parcel_name": order.parcel_name,
            "weight": order.weight,
            "weight_category": order.weight_category,
            "pickup_address": order.pickup_address,
            "destination_address": order.destination_address,
            "distance": order.distance,
            "price": order.price,
            "status": order.status,
            "pickup_lat": order.pickup_lat,
            "pickup_lng": order.pickup_lng,
            "destination_lat": order.destination_lat,
            "destination_lng": order.destination_lng,
            "current_lat": order.current_lat,
            "current_lng": order.current_lng,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "payment_status": "completed" if any(p.status == "completed" for p in order.payments) else (order.payments[-1].status if order.payments else "pending"),
            "parcel_image_url": order.parcel_image_url,
            "customer": {
                "id": order.customer.id,
                "full_name": order.customer.full_name,
                "phone": order.customer.phone
            } if order.customer else None,
            "courier": {
                "id": order.courier.id,
                "full_name": order.courier.full_name,
                "phone": order.courier.phone,
                "vehicle_type": order.courier.vehicle_type,
                "plate_number": order.courier.plate_number
            } if order.courier else None
        }
        orders.append(order_data)
    
    return jsonify({
        "orders": orders,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200


@orders_bp.route('/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order_detail(order_id):
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401

    user = User.query.get(current_user_id)
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    # Check access
    if user.role == 'customer' and order.customer_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403
    if user.role == 'courier' and order.courier_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403
    
    return jsonify({
        "id": order.id,
        "parcel_name": order.parcel_name,
        "description": order.description,
        "weight": order.weight,
        "weight_category": order.weight_category,
        "pickup_address": order.pickup_address,
        "pickup_lat": order.pickup_lat,
        "pickup_lng": order.pickup_lng,
        "destination_address": order.destination_address,
        "destination_lat": order.destination_lat,
        "destination_lng": order.destination_lng,
        "distance": order.distance,
        "price": order.price,
        "status": order.status,
        "current_lat": order.current_lat,
        "current_lng": order.current_lng,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "picked_up_at": order.picked_up_at.isoformat() if order.picked_up_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "payment_status": "completed" if any(p.status == "completed" for p in order.payments) else (order.payments[-1].status if order.payments else "pending"),
        "parcel_image_url": order.parcel_image_url,
        "delivery_code": order.delivery_code,
        "customer": {
            "id": order.customer.id,
            "full_name": order.customer.full_name,
            "phone": order.customer.phone,
            "email": order.customer.email
        } if order.customer else None,
        "courier": {
            "id": order.courier.id,
            "full_name": order.courier.full_name,
            "phone": order.courier.phone,
            "vehicle_type": order.courier.vehicle_type,
            "plate_number": order.courier.plate_number
        } if order.courier else None
    }), 200


@orders_bp.route('/orders/<int:order_id>/destination', methods=['PATCH'])
@jwt_required()
def update_destination(order_id):
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    if order.customer_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403
    
    if order.status != 'pending':
        return jsonify({"error": "Can only change destination before pickup"}), 400
    
    data = request.get_json()
    
    if not data.get('destination_address'):
        return jsonify({"error": "Destination address is required"}), 400
    
    # Geocode new destination
    destination_lat, destination_lng = None, None
    if data.get('destination_lat') and data.get('destination_lng'):
        destination_lat = data['destination_lat']
        destination_lng = data['destination_lng']
    else:
        destination_lat, destination_lng = get_geocode(data['destination_address'])
    
    # Recalculate distance
    distance = None
    if order.pickup_lat and order.pickup_lng and destination_lat and destination_lng:
        distance, _ = get_distance_matrix(
            (order.pickup_lat, order.pickup_lng),
            (destination_lat, destination_lng)
        )
        if not distance:
            distance = 5.0
    
    # Recalculate price
    new_price = ParcelOrder.calculate_price(order.weight, distance or order.distance or 5.0)
    
    order.destination_address = data['destination_address']
    order.destination_lat = destination_lat
    order.destination_lng = destination_lng
    order.distance = distance or order.distance
    order.price = new_price
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    # Notify courier if assigned
    if order.courier_id:
        create_notification(
            user_id=order.courier_id,
            order_id=order.id,
            message=f"Destination changed for order #{order.id}",
            type="destination_changed"
        )
    
    return jsonify({
        "message": "Destination updated successfully",
        "order": {
            "id": order.id,
            "destination_address": order.destination_address,
            "distance": order.distance,
            "price": order.price
        }
    }), 200


@orders_bp.route('/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
def cancel_order(order_id):
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    if order.customer_id != current_user_id:
        return jsonify({"error": "Access denied"}), 403
    
    if order.status != 'pending':
        return jsonify({"error": "Can only cancel before pickup"}), 400
    
    order.status = 'cancelled'
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    return jsonify({
        "message": "Order cancelled successfully"
    }), 200


@orders_bp.route('/orders/<int:order_id>/complete', methods=['POST'])
@jwt_required()
def complete_delivery(order_id):
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    # Check if user is the assigned courier (or maybe admin?)
    if order.courier_id != current_user_id:
        return jsonify({"error": "Access denied. You are not the assigned courier."}), 403
    
    if order.status != 'in_transit':
        return jsonify({"error": "Order must be in transit to be completed"}), 400
    
    data = request.get_json()
    code = data.get('code')
    
    if not code:
        return jsonify({"error": "Delivery code is required"}), 400
    
    # Verify code
    if str(code).strip() != str(order.delivery_code).strip():
        return jsonify({"error": "Invalid delivery code"}), 400
    
    # Mark as delivered
    order.status = 'delivered'
    order.delivered_at = db.func.now()
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    # Notify customer
    try:
        create_notification(
            user_id=order.customer_id,
            order_id=order.id,
            message=f"Order #{order.id} has been delivered successfully!",
            type_="order_delivered"
        )
        
        # Send email (optional, if we have email service ready for this)
        # send_order_delivered_email(...)
        
    except Exception as e:
        print(f"Notification error: {e}")

    return jsonify({
        "message": "Order delivered successfully",
        "order": {
            "id": order.id,
            "status": order.status,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
        }
    }), 200
