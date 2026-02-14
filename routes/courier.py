from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import ParcelOrder, User, Notification
from extensions import db
from utils import create_notification
from services.email_service import send_order_status_email
from datetime import datetime

courier_bp = Blueprint('courier', __name__)


@courier_bp.route('/courier/orders', methods=['GET'])
@jwt_required()
def get_assigned_orders():
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    user = User.query.get(current_user_id)
    if user.role != 'courier':
        return jsonify({"error": "Access denied. Courier only."}), 403
    
    # Get assigned orders
    orders = ParcelOrder.query.filter_by(courier_id=current_user_id).order_by(
        ParcelOrder.created_at.desc()
    ).all()
    
    result = []
    for order in orders:
        order_data = {
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
            "customer": {
                "id": order.customer.id,
                "full_name": order.customer.full_name,
                "phone": order.customer.phone
            } if order.customer else None
        }
        result.append(order_data)
    
    return jsonify({
        "orders": result,
        "total": len(result)
    }), 200


@courier_bp.route('/courier/orders/<int:order_id>/location', methods=['PATCH'])
@jwt_required()
def update_location(order_id):
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    user = User.query.get(current_user_id)
    if user.role != 'courier':
        return jsonify({"error": "Access denied. Courier only."}), 403
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    if order.courier_id != current_user_id:
        return jsonify({"error": "Access denied. This order is not assigned to you."}), 403
    
    data = request.get_json()
    
    if data.get('lat') is None or data.get('lng') is None:
        return jsonify({"error": "Latitude and longitude are required"}), 400
    
    try:
        lat = float(data['lat'])
        lng = float(data['lng'])
        
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid coordinate format"}), 400
    
    order.current_lat = lat
    order.current_lng = lng
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    return jsonify({
        "message": "Location updated successfully",
        "current_lat": lat,
        "current_lng": lng
    }), 200


@courier_bp.route('/courier/orders/<int:order_id>/status', methods=['PATCH'])
@jwt_required()
def update_order_status(order_id):
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    user = User.query.get(current_user_id)
    if user.role != 'courier':
        return jsonify({"error": "Access denied. Courier only."}), 403
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    if order.courier_id != current_user_id:
        return jsonify({"error": "Access denied. This order is not assigned to you."}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({"error": "Status is required"}), 400
    
    # Validate status transition
    valid_transitions = {
        "assigned": ["picked_up", "cancelled"],
        "picked_up": ["in_transit"],
        "in_transit": ["delivered"],
        "delivered": [],
        "cancelled": []
    }
    
    # Idempotency check: If status is already set, return success
    if order.status == new_status:
         return jsonify({
            "message": "Status updated successfully",
            "order": {
                "id": order.id,
                "status": order.status,
                "picked_up_at": order.picked_up_at.isoformat() if order.picked_up_at else None,
                "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
            }
        }), 200

    if new_status not in valid_transitions.get(order.status, []):
        return jsonify({
            "error": f"Invalid status transition from {order.status} to {new_status}"
        }), 400
    
    old_status = order.status
    order.status = new_status
    
    # Update timestamps
    if new_status == "picked_up":
        order.picked_up_at = datetime.utcnow()
    elif new_status == "delivered":
        order.delivered_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # Send notification and email
        create_notification(
            user_id=order.customer_id,
            order_id=order.id,
            message=f"Your order #{order.id} status changed to {new_status}",
            type="status_update"
        )
        
        if order.customer:
            send_order_status_email(order.customer.email, order.id, new_status, order.parcel_name)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    return jsonify({
        "message": "Status updated successfully",
        "order": {
            "id": order.id,
            "status": order.status,
            "picked_up_at": order.picked_up_at.isoformat() if order.picked_up_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None
        }
    }), 200


@courier_bp.route('/courier/stats', methods=['GET'])
@jwt_required()
def get_courier_stats():
    current_user_id = get_jwt_identity()
    try:
        current_user_id = int(current_user_id)
    except ValueError:
        return jsonify({"error": "Invalid user identity"}), 401
    
    user = User.query.get(current_user_id)
    if user.role != 'courier':
        return jsonify({"error": "Access denied. Courier only."}), 403
    
    from sqlalchemy import func
    
    # Get stats
    total_orders = ParcelOrder.query.filter_by(courier_id=current_user_id).count()
    delivered_orders = ParcelOrder.query.filter_by(
        courier_id=current_user_id, 
        status="delivered"
    ).count()
    in_transit_orders = ParcelOrder.query.filter_by(
        courier_id=current_user_id,
        status="in_transit"
    ).count()
    earnings = db.session.query(func.sum(ParcelOrder.price)).filter_by(
        courier_id=current_user_id,
        status="delivered"
    ).scalar() or 0
    
    return jsonify({
        "total_orders": total_orders,
        "delivered_orders": delivered_orders,
        "in_transit_orders": in_transit_orders,
        "earnings": earnings
    }), 200
