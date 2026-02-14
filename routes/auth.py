from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, 
    jwt_required, get_jwt_identity, get_jwt
)
from models import User
from extensions import db, bcrypt
from utils import create_notification

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['full_name', 'email', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field} is required"}), 400
    
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 400
    
    # Validate phone if provided
    if data.get('phone'):
        try:
            # Parse and validate phone number
            import phonenumbers
            parsed = phonenumbers.parse(data['phone'], None)
            if not phonenumbers.is_valid_number(parsed):
                return jsonify({"error": "Enter a valid phone number"}), 400
            if "+" not in data['phone']:
                return jsonify({"error": "Phone number must include country code"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    # Validate vehicle for courier
    role = data.get('role', 'customer')
    if role == 'courier':
        if not data.get('vehicle_type') or not data.get('plate_number'):
            return jsonify({"error": "Vehicle type and plate number are required for couriers"}), 400
    
    # Create user
    user = User(
        full_name=data['full_name'],
        email=data['email'],
        phone=data.get('phone'),
        role=role,
        vehicle_type=data.get('vehicle_type'),
        plate_number=data.get('plate_number')
    )
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email
        try:
            from services.email_service import send_magic_link
            import os
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            magic_link = f"{frontend_url}/login"
            send_magic_link(user.email, magic_link)
        except Exception as e:
            print(f"Failed to send email: {e}")
            # Continue even if email fails
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    # Create access and refresh tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "message": "User registered successfully",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        },
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({"error": "Invalid email or password"}), 401
    
    if not user.is_active:
        return jsonify({"error": "Account is deactivated"}), 403
    
    # Create tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role
        },
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "vehicle_type": user.vehicle_type,
        "plate_number": user.plate_number,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    
    return jsonify({
        "access_token": access_token
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In a real app, you would blacklist the token
    return jsonify({"message": "Successfully logged out"}), 200
