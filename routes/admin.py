from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import ParcelOrder, User, Payment
from extensions import db
from sqlalchemy import func
from utils import create_notification
from services.email_service import send_order_status_email

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin/users', methods=['GET'])
@jwt_required()
def get_users():
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    # Get query parameters
    role_filter = request.args.get('role')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = User.query
    
    if role_filter:
        query = query.filter_by(role=role_filter)
    
    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    users = []
    for u in pagination.items:
        users.append({
            "id": u.id,
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })
    
    return jsonify({
        "users": users,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200


@admin_bp.route('/admin/orders', methods=['GET'])
@jwt_required()
def get_all_orders():
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    # Get query parameters
    status_filter = request.args.get('status')
    courier_id = request.args.get('courier_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = ParcelOrder.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if courier_id:
        query = query.filter_by(courier_id=courier_id)
    
    query = query.order_by(ParcelOrder.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    orders = []
    for order in pagination.items:
        orders.append({
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
            "parcel_image_url": order.parcel_image_url,
            "customer": {
                "id": order.customer.id,
                "full_name": order.customer.full_name,
                "phone": order.customer.phone
            } if order.customer else None,
            "courier": {
                "id": order.courier.id,
                "full_name": order.courier.full_name,
                "phone": order.courier.phone
            } if order.courier else None
        })
    
    return jsonify({
        "orders": orders,
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages
    }), 200


@admin_bp.route('/admin/orders/<int:order_id>/assign-courier', methods=['PATCH'])
@jwt_required()
def assign_courier(order_id):
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    data = request.get_json()
    courier_id = data.get('courier_id')
    
    if not courier_id:
        return jsonify({"error": "Courier ID is required"}), 400
    
    courier = User.query.filter_by(id=courier_id, role='courier', is_active=True).first()
    
    if not courier:
        return jsonify({"error": "Active courier not found"}), 404
    
    if order.status not in ['pending', 'assigned']:
        return jsonify({"error": f"Can only assign courier to pending or assigned orders (Current status: {order.status})"}), 400
    
    order.courier_id = courier_id
    order.status = 'assigned'
    
    try:
        db.session.commit()
        
        # Notify courier
        create_notification(
            user_id=courier_id,
            order_id=order.id,
            message=f"You have been assigned order #{order.id}",
            type="assignment"
        )
        
        # Notify customer
        create_notification(
            user_id=order.customer_id,
            order_id=order.id,
            message=f"Courier assigned to your order #{order.id}",
            type="assignment"
        )
        
        if order.customer:
            send_order_status_email(order.customer.email, order.id, 'assigned', order.parcel_name)
        
    except Exception as e:
        db.session.rollback()
        print(f"Assign Courier Error: {str(e)}") # Add logging
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 400
    
    return jsonify({
        "message": "Courier assigned successfully",
        "order": {
            "id": order.id,
            "courier_id": order.courier_id,
            "status": order.status
        }
    }), 200


@admin_bp.route('/admin/orders/<int:order_id>/status', methods=['PATCH'])
@jwt_required()
def update_order_status(order_id):
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    order = ParcelOrder.query.get(order_id)
    
    if not order:
        return jsonify({"error": "Order not found"}), 404
    
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({"error": "Status is required"}), 400
    
    # Validate status
    valid_statuses = ['pending', 'assigned', 'picked_up', 'in_transit', 'delivered', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({"error": "Invalid status"}), 400
    
    old_status = order.status
    order.status = new_status
    
    try:
        db.session.commit()
        
        # Notify customer
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
            "status": order.status
        }
    }), 200


@admin_bp.route('/admin/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard():
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    # Get statistics
    total_users = User.query.count()
    total_customers = User.query.filter_by(role='customer').count()
    total_couriers = User.query.filter_by(role='courier').count()
    total_orders = ParcelOrder.query.count()
    
    # Orders by status
    pending_orders = ParcelOrder.query.filter_by(status='pending').count()
    assigned_orders = ParcelOrder.query.filter_by(status='assigned').count()
    in_transit_orders = ParcelOrder.query.filter_by(status='in_transit').count()
    delivered_orders = ParcelOrder.query.filter_by(status='delivered').count()
    cancelled_orders = ParcelOrder.query.filter_by(status='cancelled').count()
    
    # Revenue
    total_revenue = db.session.query(func.sum(ParcelOrder.price)).filter(
        ParcelOrder.status.in_(['delivered', 'in_transit'])
    ).scalar() or 0
    
    # Recent orders
    recent_orders = ParcelOrder.query.order_by(
        ParcelOrder.created_at.desc()
    ).limit(10).all()
    
    recent_orders_data = []
    for order in recent_orders:
        recent_orders_data.append({
            "id": order.id,
            "parcel_name": order.parcel_name,
            "status": order.status,
            "price": order.price,
            "parcel_image_url": order.parcel_image_url,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "customer_name": order.customer.full_name if order.customer else None,
            "courier_name": order.courier.full_name if order.courier else None
        })
    
    return jsonify({
        "stats": {
            "total_users": total_users,
            "total_customers": total_customers,
            "total_couriers": total_couriers,
            "total_orders": total_orders,
            "pending_orders": pending_orders,
            "assigned_orders": assigned_orders,
            "in_transit_orders": in_transit_orders,
            "delivered_orders": delivered_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": total_revenue
        },
        "recent_orders": recent_orders_data
    }), 200


@admin_bp.route('/admin/users/<int:user_id>/toggle-active', methods=['PATCH'])
@jwt_required()
def toggle_user_active(user_id):
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    target_user = User.query.get(user_id)
    
    if not target_user:
        return jsonify({"error": "User not found"}), 404
    
    target_user.is_active = not target_user.is_active
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    return jsonify({
        "message": f"User {'activated' if target_user.is_active else 'deactivated'} successfully",
        "is_active": target_user.is_active
    }), 200


@admin_bp.route('/admin/couriers', methods=['GET'])
@jwt_required()
def get_couriers():
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    couriers = User.query.filter_by(role='courier').all()
    
    result = []
    for courier in couriers:
        # Get courier stats
        total_deliveries = ParcelOrder.query.filter_by(
            courier_id=courier.id, 
            status='delivered'
        ).count()
        
        active_orders = ParcelOrder.query.filter_by(
            courier_id=courier.id
        ).filter(
            ParcelOrder.status.in_(['assigned', 'picked_up', 'in_transit'])
        ).count()
        
        result.append({
            "id": courier.id,
            "full_name": courier.full_name,
            "email": courier.email,
            "phone": courier.phone,
            "vehicle_type": courier.vehicle_type,
            "plate_number": courier.plate_number,
            "is_active": courier.is_active,
            "total_deliveries": total_deliveries,
            "active_orders": active_orders,
            "created_at": courier.created_at.isoformat() if courier.created_at else None
        })

    return jsonify({
        "couriers": result,
        "total": len(result)
    }), 200

@admin_bp.route('/admin/reports', methods=['GET'])
@jwt_required()
def get_reports():
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if not user or user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
        
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # 1. Revenue last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    # Only count delivered orders for revenue
    daily_revenue = db.session.query(
        func.date(ParcelOrder.created_at).label('date'),
        func.sum(ParcelOrder.price).label('revenue')
    ).filter(
        ParcelOrder.created_at >= thirty_days_ago,
        ParcelOrder.status == 'delivered'
    ).group_by(
        func.date(ParcelOrder.created_at)
    ).all()
    
    revenue_chart_data = []
    # Fill in missing days? For simplicity, just sending what we have
    for day in daily_revenue:
        revenue_chart_data.append({
            "date": str(day.date),
            "revenue": float(day.revenue) if day.revenue else 0
        })
        
    # 2. Status Distribution
    status_counts = db.session.query(
        ParcelOrder.status,
        func.count(ParcelOrder.id)
    ).group_by(ParcelOrder.status).all()
    
    status_chart_data = []
    for s in status_counts:
        status_chart_data.append({
            "name": s[0],
            "value": s[1]
        })
        
    # 3. Top Couriers (by completed deliveries)
    # Using join to get courier names
    top_couriers = db.session.query(
        User.full_name,
        func.count(ParcelOrder.id).label('deliveries')
    ).join(ParcelOrder, ParcelOrder.courier_id == User.id).filter(
        User.role == 'courier',
        ParcelOrder.status == 'delivered'
    ).group_by(User.id, User.full_name).order_by(func.count(ParcelOrder.id).desc()).limit(5).all()
    
    top_couriers_data = []
    for c in top_couriers:
        top_couriers_data.append({
            "name": c.full_name,
            "deliveries": c.deliveries
        })
        
    return jsonify({
        "revenue_trends": revenue_chart_data,
        "status_distribution": status_chart_data,
        "top_couriers": top_couriers_data
    }), 200


@admin_bp.route('/admin/users/<int:user_id>/role', methods=['PATCH'])
@jwt_required()
def change_user_role(user_id):
    current_user_id = get_jwt_identity()
    
    user = User.query.get(current_user_id)
    if not user or user.role != 'admin':
        return jsonify({"error": "Access denied. Admin only."}), 403
    
    target_user = User.query.get(user_id)
    if not target_user:
        return jsonify({"error": "User not found"}), 404
        
    if target_user.id == current_user_id:
        return jsonify({"error": "Cannot change your own role"}), 400
        
    data = request.get_json()
    new_role = data.get('role')
    
    valid_roles = ['customer', 'courier', 'admin']
    if new_role not in valid_roles:
        return jsonify({"error": "Invalid role"}), 400
        
    # Constraint handling: Couriers need vehicle/plate
    if new_role == 'courier':
        if not target_user.vehicle_type:
            target_user.vehicle_type = 'Motorbike' # Default
        if not target_user.plate_number:
            target_user.plate_number = 'PENDING' # Placeholder
            
    target_user.role = new_role
            
    try:
        db.session.commit()
        return jsonify({
            "message": f"User role updated to {new_role}",
            "user": {
                "id": target_user.id,
                "role": target_user.role
            }
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
