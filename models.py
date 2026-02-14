from extensions import db, bcrypt
from sqlalchemy.orm import validates
from sqlalchemy import CheckConstraint
import phonenumbers
from datetime import datetime


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(
        db.Enum("courier", "customer", "admin", name="user_roles"),
        default="customer",
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "(role != 'courier') OR (vehicle_type IS NOT NULL AND plate_number IS NOT NULL)",
            name="ck_courier_vehicle_required",
        ),
    )

    vehicle_type = db.Column(db.String(50), nullable=True)
    plate_number = db.Column(db.String(20), nullable=True)
    plate_number = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    @validates("plate_number")
    def validate_plate_number(self, key, number):
        if number is None or number.strip() == "":
            if self.role == "courier":
                raise ValueError("Plate number is required for couriers")
            return number
        plate = number.strip().upper()
        if len(plate) < 7:
            raise ValueError("Plate number must be at least 7 characters")
        return plate

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)
    
    @validates("email")
    def validate_email(self, key, address):
        if "@" not in address:
            raise ValueError("Invalid email address")
        return address
    
    @validates("phone")
    def validate_phone(self, key, number):
        if number is None or number == "":
            return number
        
        parsed = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("Enter a valid phone number")
        if "+" not in number:
            raise ValueError("Phone number must include country code")
        return number

    @validates("vehicle_type")
    def validate_vehicle_type(self, key, vehicle):
        vehicle = (vehicle or "").strip()
        if self.role == "courier" and not vehicle:
            raise ValueError("Vehicle type is required for couriers")
        return vehicle

    def to_dict(self, exclude_password=True):
        data = {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "role": self.role,
            "vehicle_type": self.vehicle_type,
            "plate_number": self.plate_number,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if exclude_password:
            del data["password_hash"]
        return data


class ParcelOrder(db.Model):
    __tablename__ = "parcel_orders"

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    courier_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    # Parcel details
    parcel_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    weight = db.Column(db.Float, nullable=False)
    weight_category = db.Column(db.String(50), nullable=False)
    
    # Addresses
    pickup_address = db.Column(db.Text, nullable=False)
    pickup_lat = db.Column(db.Float, nullable=True)
    pickup_lng = db.Column(db.Float, nullable=True)
    
    destination_address = db.Column(db.Text, nullable=False)
    destination_lat = db.Column(db.Float, nullable=True)
    destination_lng = db.Column(db.Float, nullable=True)
    
    # Pricing
    distance = db.Column(db.Float, nullable=True)
    price = db.Column(db.Float, nullable=False)
    
    # Status
    status = db.Column(
        db.Enum("pending", "assigned", "picked_up", "in_transit", "delivered", "cancelled", name="order_status"),
        default="pending",
        nullable=False,
    )
    
    # Courier location updates
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    picked_up_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    customer = db.relationship("User", foreign_keys=[customer_id], backref="orders")
    courier = db.relationship("User", foreign_keys=[courier_id], backref="deliveries")
    payments = db.relationship("Payment", backref="order", lazy=True)
    notifications = db.relationship("Notification", backref="order", lazy=True)

    @staticmethod
    def calculate_price(weight, distance):
        """Calculate price based on distance (1 KSH per km, min 10 KSH)"""
        # specific requirement: "1ksh per kilometre"
        # Ensure minimum fee of 10 KSH
        if not distance:
            return 10.00
            
        price = distance * 1.0
        return max(round(price, 2), 10.00)

    def to_dict(self):
        return {
            "id": self.id,
            "parcel_name": self.parcel_name,
            "description": self.description,
            "weight": self.weight,
            "weight_category": self.weight_category,
            "pickup_address": self.pickup_address,
            "pickup_lat": self.pickup_lat,
            "pickup_lng": self.pickup_lng,
            "destination_address": self.destination_address,
            "destination_lat": self.destination_lat,
            "destination_lng": self.destination_lng,
            "distance": self.distance,
            "price": self.price,
            "status": self.status,
            "current_lat": self.current_lat,
            "current_lng": self.current_lng,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "picked_up_at": self.picked_up_at.isoformat() if self.picked_up_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "payment_status": self.payments[-1].status if self.payments else "pending"
        }


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("parcel_orders.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), default="mpesa")
    transaction_id = db.Column(db.String(100), unique=True, nullable=True)
    status = db.Column(
        db.Enum("pending", "completed", "failed", name="payment_status"),
        default="pending",
        nullable=False,
    )
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "amount": self.amount,
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("parcel_orders.id"), nullable=True)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship("User", backref="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "order_id": self.order_id,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
