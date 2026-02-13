#!/usr/bin/env python3
"""
Seed script to populate the database with test data.
Run: python seed.py
"""
from app import create_app
from extensions import db, bcrypt
from models import User, ParcelOrder, Payment, Notification
from datetime import datetime

def seed_database():
    app = create_app()
    
    with app.app_context():
        try:
            print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # Drop all tables and recreate
            print("Dropping all tables...")
            db.drop_all()
            print("Creating all tables...")
            db.create_all()
            
            print("Creating users...")
            
            # Create admin
            admin = User(
                full_name="Admin User",
                email="admin@test.com",
                phone="+254700000003",
                role="admin"
            )
            admin.set_password("password123")
            db.session.add(admin)
            
            # Create customers
            customer1 = User(
                full_name="John Doe",
                email="customer@test.com",
                phone="+254700000001",
                role="customer"
            )
            customer1.set_password("password123")
            db.session.add(customer1)
            
            customer2 = User(
                full_name="Jane Smith",
                email="jane@test.com",
                phone="+254700000002",
                role="customer"
            )
            customer2.set_password("password123")
            db.session.add(customer2)
            
            # Create couriers
            courier1 = User(
                full_name="Mike Courier",
                email="courier@test.com",
                phone="+254700000004",
                role="courier",
                vehicle_type="Motorcycle",
                plate_number="ABC123DE"
            )
            courier1.set_password("password123")
            db.session.add(courier1)
            
            courier2 = User(
                full_name="Sarah Rider",
                email="sarah@test.com",
                phone="+254700000005",
                role="courier",
                vehicle_type="Bicycle",
                plate_number="BIKE1234"
            )
            courier2.set_password("password123")
            db.session.add(courier2)
            
            db.session.commit()
            print("Users created successfully!")
            print(f"Admin ID: {admin.id}")
            
            # Verify users
            users = User.query.all()
            print(f"\nTotal users in database: {len(users)}")
            for u in users:
                print(f"  - {u.email} ({u.role})")
            
            # Create sample orders
            print("\nCreating sample orders...")
            orders = [
                # Pending order (no courier assigned)
                ParcelOrder(
                    customer_id=customer1.id,
                    parcel_name="Laptop Charger",
                    description="Apple MacBook charger",
                    weight=0.5,
                    weight_category="small",
                    pickup_address="123 Main Street, Nairobi",
                    pickup_lat=-1.286389,
                    pickup_lng=36.817223,
                    destination_address="456 Oak Avenue, Nairobi",
                    destination_lat=-1.2921,
                    destination_lng=36.8219,
                    distance=5.2,
                    price=85.0,
                    status="pending"
                ),
                # Assigned order
                ParcelOrder(
                    customer_id=customer1.id,
                    courier_id=courier1.id,
                    parcel_name="Textbooks",
                    description="University textbooks for biology",
                    weight=3.5,
                    weight_category="medium",
                    pickup_address="789 University Road, Nairobi",
                    pickup_lat=-1.2789,
                    pickup_lng=36.8123,
                    destination_address="101 College Street, Nairobi",
                    destination_lat=-1.2833,
                    destination_lng=36.8200,
                    distance=3.8,
                    price=145.0,
                    status="assigned"
                ),
                # Picked up order
                ParcelOrder(
                    customer_id=customer2.id,
                    courier_id=courier1.id,
                    parcel_name="Office Supplies",
                    description="Printer paper and ink cartridges",
                    weight=2.0,
                    weight_category="medium",
                    pickup_address="456 Business Park, Nairobi",
                    pickup_lat=-1.2900,
                    pickup_lng=36.8150,
                    destination_address="789 Corporate Tower, Nairobi",
                    destination_lat=-1.2950,
                    destination_lng=36.8250,
                    distance=2.5,
                    price=125.0,
                    status="picked_up",
                    picked_up_at=datetime.utcnow()
                ),
                # In transit order
                ParcelOrder(
                    customer_id=customer2.id,
                    courier_id=courier2.id,
                    parcel_name="Electronics",
                    description="Wireless headphones and phone case",
                    weight=1.2,
                    weight_category="small",
                    pickup_address="555 Tech Hub, Nairobi",
                    pickup_lat=-1.2800,
                    pickup_lng=36.8100,
                    destination_address="888 Residence, Nairobi",
                    destination_lat=-1.2850,
                    destination_lng=36.8300,
                    distance=4.0,
                    price=110.0,
                    status="in_transit",
                    current_lat=-1.2820,
                    current_lng=36.8200
                ),
                # Delivered order
                ParcelOrder(
                    customer_id=customer1.id,
                    courier_id=courier1.id,
                    parcel_name="Clothing Package",
                    description="Winter jacket and sweaters",
                    weight=2.5,
                    weight_category="medium",
                    pickup_address="200 Fashion Street, Nairobi",
                    pickup_lat=-1.2750,
                    pickup_lng=36.8050,
                    destination_address="300 Home Street, Nairobi",
                    destination_lat=-1.2780,
                    destination_lng=36.8150,
                    distance=6.5,
                    price=155.0,
                    status="delivered",
                    picked_up_at=datetime.utcnow(),
                    delivered_at=datetime.utcnow()
                ),
                # Cancelled order
                ParcelOrder(
                    customer_id=customer2.id,
                    parcel_name="Wrong Order",
                    description="Accidental order",
                    weight=1.0,
                    weight_category="small",
                    pickup_address="100 Start Avenue, Nairobi",
                    destination_address="200 End Road, Nairobi",
                    distance=3.0,
                    price=95.0,
                    status="cancelled"
                )
            ]
            
            for order in orders:
                db.session.add(order)
            
            db.session.commit()
            
            print("✓ Seed data created successfully!")
            print("\n" + "="*50)
            print("Demo Accounts:")
            print("="*50)
            print("  Admin:    admin@test.com / password123")
            print("  Customer: customer@test.com / password123")
            print("  Courier:  courier@test.com / password123")
            print("="*50)
            print("\n6 sample orders have been created with various statuses.")
            print("Restart the backend server to test login.")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    seed_database()
