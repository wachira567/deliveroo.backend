import requests
import os
from flask_mail import Message
from extensions import mail, db
from models import Notification


def get_distance_matrix(origin, destination):
    """Get distance and duration using Google Maps API"""
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        return None, None
    
    url = f"https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": f"{origin[0]},{origin[1]}",
        "destinations": f"{destination[0]},{destination[1]}",
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "OK" and data["rows"][0]["elements"][0]["status"] == "OK":
            # Use value (meters) for accuracy
            distance_meters = element["distance"]["value"]
            distance_km = distance_meters / 1000.0
            
            return distance_km, duration_text
        
        return None, None
    except Exception as e:
        print(f"Error getting distance: {e}")
        return None, None


def calculate_delivery_price(distance_km):
    """Calculate delivery price based on distance (1 KSH per km)"""
    if distance_km is None:
        return 0
    
    rate_per_km = 1.0
    price = distance_km * rate_per_km
    
    # specific requirement: "Lets set the fee at 1ksh per kilometre"
    return round(price, 2)


def get_geocode(address):
    """Get lat/lng for an address using Google Maps API"""
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        return None, None
    
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": api_key
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("status") == "OK" and data["results"]:
            location = data["results"][0]["geometry"]["location"]
            return location["lat"], location["lng"]
        
        return None, None
    except Exception as e:
        print(f"Error geocoding: {e}")
        return None, None


def send_email(to, subject, body):
    """Send email notification"""
    try:
        msg = Message(subject, recipients=[to], body=body)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def create_notification(user_id, order_id, message, type_):
    """Create a notification record"""
    notification = Notification(
        user_id=user_id,
        order_id=order_id,
        message=message,
        type=type_
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def send_order_status_email(user, order, status):
    """Send email when order status changes"""
    status_messages = {
        "assigned": f"Your order #{order.id} has been assigned a courier.",
        "picked_up": f"Your order #{order.id} has been picked up by the courier.",
        "in_transit": f"Your order #{order.id} is on its way!",
        "delivered": f"Your order #{order.id} has been delivered successfully!",
        "cancelled": f"Your order #{order.id} has been cancelled."
    }
    
    subject = f"Deliveroo - Order #{order.id} Status Update"
    body = status_messages.get(status, f"Your order #{order.id} status has been updated to: {status}")
    
    send_email(user.email, subject, body)


def role_required(*roles):
    """Decorator to require specific roles"""
    def decorator(f):
        from flask_jwt_extended import get_jwt_identity
        from models import User
        
        def wrapper(*args, **kwargs):
            current_user_id = get_jwt_identity()
            user = User.query.get(current_user_id)
            
            if not user:
                return {"error": "User not found"}, 404
            
            if user.role not in roles:
                return {"error": f"Access denied. Required roles: {roles}"}, 403
            
            return f(*args, **kwargs)
        
        wrapper.__name__ = f.__name__
        return wrapper
    
    return decorator
