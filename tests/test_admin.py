import pytest
from models import ParcelOrder, User
from extensions import db


class TestAdmin:
    def test_get_users_forbidden_for_customer(self, client, test_customer, auth_headers):
        response = client.get('/api/admin/users', headers=auth_headers)
        
        assert response.status_code == 403

    def test_get_users_forbidden_for_courier(self, client, test_courier, courier_auth_headers):
        response = client.get('/api/admin/users', headers=courier_auth_headers)
        
        assert response.status_code == 403

    def test_get_users_as_admin(self, client, test_admin, admin_auth_headers):
        response = client.get('/api/admin/users', headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'users' in data
        assert 'total' in data

    def test_get_all_orders_as_admin(self, client, test_admin, admin_auth_headers):
        response = client.get('/api/admin/orders', headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'orders' in data

    def test_assign_courier(self, client, test_admin, test_customer, admin_auth_headers, auth_headers):
        # Create an order first
        create_response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': 2.5,
            'pickup_address': '123 Main St, Nairobi',
            'destination_address': '456 Oak Ave, Nairobi'
        }, headers=auth_headers)
        order_id = create_response.get_json()['order']['id']
        
        # Create a courier
        with client.application.app_context():
            courier = User(
                full_name='Test Courier 2',
                email='courier2@test.com',
                phone='+254700000009',
                role='courier',
                vehicle_type='Bicycle',
                plate_number='BIKE123'
            )
            courier.set_password('password123')
            db.session.add(courier)
            db.session.commit()
            courier_id = courier.id
        
        # Assign courier to order
        response = client.patch(f'/api/admin/orders/{order_id}/assign-courier', json={
            'courier_id': courier_id
        }, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['order']['courier_id'] == courier_id
        assert data['order']['status'] == 'assigned'

    def test_assign_courier_to_assigned_order(self, client, test_admin, app, admin_auth_headers):
        with app.app_context():
            courier = User(
                full_name='Test Courier 3',
                email='courier3@test.com',
                phone='+254700000010',
                role='courier',
                vehicle_type='Car',
                plate_number='CAR123X'
            )
            courier.set_password('password123')
            db.session.add(courier)
            
            order = ParcelOrder(
                customer_id=test_admin,
                parcel_name='Test Package',
                weight=1.0,
                pickup_address='123 Main St',
                destination_address='456 Oak Ave',
                price=50.0,
                status='assigned'
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id
            courier_id = courier.id
        
        # Try to assign another courier
        response = client.patch(f'/api/admin/orders/{order_id}/assign-courier', json={
            'courier_id': courier_id
        }, headers=admin_auth_headers)
        
        assert response.status_code == 400
        assert 'Can only assign courier to pending orders' in response.get_json()['error']

    def test_update_order_status_as_admin(self, client, test_admin, admin_auth_headers, app):
        with app.app_context():
            order = ParcelOrder(
                customer_id=test_admin,
                parcel_name='Test Package',
                weight=1.0,
                pickup_address='123 Main St',
                destination_address='456 Oak Ave',
                price=50.0,
                status='pending'
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id
        
        response = client.patch(f'/api/admin/orders/{order_id}/status', json={
            'status': 'cancelled'
        }, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['order']['status'] == 'cancelled'

    def test_get_dashboard(self, client, test_admin, admin_auth_headers):
        response = client.get('/api/admin/dashboard', headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'stats' in data
        assert 'recent_orders' in data
        assert 'total_users' in data['stats']
        assert 'total_orders' in data['stats']

    def test_toggle_user_active(self, client, test_admin, test_courier, admin_auth_headers):
        response = client.patch(f'/api/admin/users/{test_courier}/toggle-active', json={}, headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['is_active'] == False
        
        # Toggle back
        response = client.patch(f'/api/admin/users/{test_courier}/toggle-active', json={}, headers=admin_auth_headers)
        
        assert response.status_code == 200
        assert response.get_json()['is_active'] == True

    def test_get_couriers(self, client, test_admin, test_courier, admin_auth_headers):
        response = client.get('/api/admin/couriers', headers=admin_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'couriers' in data
        assert len(data['couriers']) >= 1
