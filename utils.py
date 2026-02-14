import requests
import os
from flask_mail import Message
from extensions import mail, db
from models import Notification



def get_distance_matrix(origin, destination):
    """Get distance and duration using Mapbox Matrix API"""
    access_token = os.environ.get('MAPBOX_ACCESS_TOKEN')
    if not access_token:
        return None, None
    
    # Mapbox Matrix API: https://api.mapbox.com/directions-matrix/v1/mapbox/driving/{coordinates}
    # Coordinates format: lon,lat;lon,lat (semi-colon separated)
    # Note: Mapbox uses [longitude, latitude], while Google often uses [latitude, longitude]
    # Input arguments are expected to be (lat, lng) tuples
    
    coordinates = f"{origin[1]},{origin[0]};{destination[1]},{destination[0]}"
    url = f"https://api.mapbox.com/directions-matrix/v1/mapbox/driving/{coordinates}"
    
    params = {
        "access_token": access_token,
        "annotations": "distance,duration"
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("code") == "Ok" and data.get("distances"):
            # specific requirement: "Use value (meters) for accuracy"
            # Mapbox returns matrix: [[0, dist], [dist, 0]]
            # We want from origin (0) to destination (1)
            distance_meters = data["distances"][0][1]
            duration_seconds = data["durations"][0][1]
            
            if distance_meters is None:
                return None, None
                
            distance_km = distance_meters / 1000.0
            
            # Format duration text (e.g., "15 mins")
            duration_minutes = round(duration_seconds / 60)
            if duration_minutes >= 60:
                hours = duration_minutes // 60
                mins = duration_minutes % 60
                duration_text = f"{hours} hrs {mins} mins"
            else:
                duration_text = f"{duration_minutes} mins"
            
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
    # Ensure minimum fee of 10 KSH to avoid 0.0 value or too low
    return max(round(price, 2), 10.00)


def get_geocode(address):
    """Get lat/lng for an address using Mapbox Geocoding API"""
    access_token = os.environ.get('MAPBOX_ACCESS_TOKEN')
    if not access_token:
        return None, None
    
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
    params = {
        "access_token": access_token,
        "limit": 1
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get("features"):
            # Mapbox returns [lng, lat]
            center = data["features"][0]["center"]
            lng, lat = center[0], center[1]
            return lat, lng
        
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
