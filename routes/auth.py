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
            # Default to KE if no country code provided
            parsed = phonenumbers.parse(data['phone'], "KE")
            if not phonenumbers.is_valid_number(parsed):
                return jsonify({"error": "Enter a valid phone number"}), 400
            
            # Auto-format to E.164
            data['phone'] = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            
        except Exception as e:
            return jsonify({"error": f"Invalid phone number: {str(e)}"}), 400
    
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
        plate_number=data.get('plate_number'),
        is_verified=False  # Require verification
    )
    user.set_password(data['password'])
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Send verification email
        try:
            from services.email_service import send_magic_link, send_email
            import os
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
            
            # Create verification token
            verification_token = create_access_token(identity=str(user.id), additional_claims={"type": "verification"})
            verification_link = f"{frontend_url}/verify-email?token={verification_token}"
            
            send_email(
                user.email, 
                "Verify your Deliveroo Account",
                f"""
                <div style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Welcome to Deliveroo!</h2>
                    <p>Please verify your email address to activate your account.</p>
                    <a href="{verification_link}" style="background-color: #00CCBC; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email</a>
                    <p>Or verify using this link: {verification_link}</p>
                </div>
                """
            )
        except Exception as e:
            print(f"Failed to send email: {e}")
            # Consider rollback if email critical? For now log error.
            
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    
    return jsonify({
        "message": "User registered successfully. Please check your email to verify your account."
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
        
    if not user.is_verified:
        return jsonify({"error": "Please verify your email address first"}), 403
    
    # Create tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))
    
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


@auth_bp.route('/verify-email', methods=['POST'])
@jwt_required()
def verify_email():
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    if claims.get("type") != "verification":
        return jsonify({"error": "Invalid token type"}), 400
        
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        
    if user.is_verified:
        return jsonify({"message": "Email already verified"}), 200
        
    user.is_verified = True
    db.session.commit()
    
    return jsonify({"message": "Email verified successfully"}), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user:
        # Don't reveal user existence
        return jsonify({"message": "If an account exists, a reset link has been sent."}), 200
        
    # Send reset email
    try:
        from services.email_service import send_email
        import os
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:5173')
        
        # Create reset token (short lived)
        reset_token = create_access_token(identity=str(user.id), additional_claims={"type": "reset"}, expires_delta=False) 
        # Using default expiration or set specifically
        
        reset_link = f"{frontend_url}/reset-password?token={reset_token}"
        
        send_email(
            user.email, 
            "Reset your Password",
            f"""
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Password Reset Request</h2>
                <p>Click the link below to reset your password:</p>
                <a href="{reset_link}" style="background-color: #00CCBC; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a>
                <p>Or use this link: {reset_link}</p>
                <p>If you didn't request this, ignore this email.</p>
            </div>
            """
        )
    except Exception as e:
        print(f"Failed to send email: {e}")
        return jsonify({"error": "Failed to send email"}), 500
        
    return jsonify({"message": "If an account exists, a reset link has been sent."}), 200


@auth_bp.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password():
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    if claims.get("type") != "reset":
        return jsonify({"error": "Invalid token type"}), 400
        
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password:
        return jsonify({"error": "New password is required"}), 400
        
    user = User.query.get(current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
        

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
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=str(current_user_id))
    
    return jsonify({
        "access_token": access_token
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # In a real app, you would blacklist the token
    return jsonify({"message": "Successfully logged out"}), 200
