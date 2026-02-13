import pytest
from models import ParcelOrder, User
from extensions import db


class TestOrders:
    def test_create_order_success(self, client, test_customer, auth_headers):
        response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'description': 'A test package',
            'weight': 2.5,
            'pickup_address': '123 Main St, Nairobi',
            'destination_address': '456 Oak Ave, Nairobi'
        }, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['order']['parcel_name'] == 'Test Package'
        assert data['order']['weight'] == 2.5
        assert data['order']['status'] == 'pending'
        assert 'price' in data['order']

    def test_create_order_missing_fields(self, client, test_customer, auth_headers):
        response = client.post('/api/orders', json={
            'parcel_name': 'Test Package'
        }, headers=auth_headers)
        
        assert response.status_code == 400

    def test_create_order_invalid_weight(self, client, test_customer, auth_headers):
        response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': -5,
            'pickup_address': '123 Main St',
            'destination_address': '456 Oak Ave'
        }, headers=auth_headers)
        
        assert response.status_code == 400

    def test_create_order_courier_forbidden(self, client, test_courier, courier_auth_headers):
        response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': 2.5,
            'pickup_address': '123 Main St',
            'destination_address': '456 Oak Ave'
        }, headers=courier_auth_headers)
        
        assert response.status_code == 403
        assert 'Only customers can create orders' in response.get_json()['error']

    def test_get_orders(self, client, test_customer, auth_headers):
        # Create an order first
        client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': 2.5,
            'pickup_address': '123 Main St, Nairobi',
            'destination_address': '456 Oak Ave, Nairobi'
        }, headers=auth_headers)
        
        response = client.get('/api/orders', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['orders']) >= 1
        assert data['orders'][0]['parcel_name'] == 'Test Package'

    def test_get_order_detail(self, client, test_customer, auth_headers):
        # Create an order
        create_response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': 2.5,
            'pickup_address': '123 Main St, Nairobi',
            'destination_address': '456 Oak Ave, Nairobi'
        }, headers=auth_headers)
        order_id = create_response.get_json()['order']['id']
        
        response = client.get(f'/api/orders/{order_id}', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['parcel_name'] == 'Test Package'
        assert data['description'] is not None

    def test_get_order_detail_not_found(self, client, test_customer, auth_headers):
        response = client.get('/api/orders/99999', headers=auth_headers)
        
        assert response.status_code == 404

    def test_get_order_detail_wrong_user(self, client, app, auth_headers):
        # Create an order with another user
        with app.app_context():
            other_user = User(
                full_name='Other User',
                email='other@test.com',
                role='customer'
            )
            other_user.set_password('password123')
            db.session.add(other_user)
            db.session.commit()
            
            order = ParcelOrder(
                customer_id=other_user.id,
                parcel_name='Other Package',
                weight=1.0,
                pickup_address='123 Main St',
                destination_address='456 Oak Ave',
                price=50.0,
                status='pending'
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id
        
        # Try to access as different user
        response = client.get(f'/api/orders/{order_id}', headers=auth_headers)
        
        assert response.status_code == 403

    def test_update_destination(self, client, test_customer, auth_headers):
        # Create an order
        create_response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': 2.5,
            'pickup_address': '123 Main St, Nairobi',
            'destination_address': '456 Oak Ave, Nairobi'
        }, headers=auth_headers)
        order_id = create_response.get_json()['order']['id']
        
        response = client.patch(f'/api/orders/{order_id}/destination', json={
            'destination_address': '789 Pine Rd, Nairobi'
        }, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert '789 Pine Rd' in data['order']['destination_address']

    def test_update_destination_after_pickup(self, client, test_customer, auth_headers):
        # Create an order
        create_response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': 2.5,
            'pickup_address': '123 Main St, Nairobi',
            'destination_address': '456 Oak Ave, Nairobi'
        }, headers=auth_headers)
        order_id = create_response.get_json()['order']['id']
        
        # Manually update status to picked_up (via admin in real app)
        with client.application.app_context():
            order = ParcelOrder.query.get(order_id)
            order.status = 'picked_up'
            db.session.commit()
        
        response = client.patch(f'/api/orders/{order_id}/destination', json={
            'destination_address': '789 Pine Rd, Nairobi'
        }, headers=auth_headers)
        
        assert response.status_code == 400
        assert 'Can only change destination before pickup' in response.get_json()['error']

    def test_cancel_order(self, client, test_customer, auth_headers):
        # Create an order
        create_response = client.post('/api/orders', json={
            'parcel_name': 'Test Package',
            'weight': 2.5,
            'pickup_address': '123 Main St, Nairobi',
            'destination_address': '456 Oak Ave, Nairobi'
        }, headers=auth_headers)
        order_id = create_response.get_json()['order']['id']
        
        response = client.delete(f'/api/orders/{order_id}', headers=auth_headers)
        
        assert response.status_code == 200
        
        # Verify order is cancelled
        with client.application.app_context():
            order = ParcelOrder.query.get(order_id)
            assert order.status == 'cancelled'

    def test_cancel_after_pickup(self, client, test_customer, auth_headers, app):
        # Create an order
        with app.app_context():
            order = ParcelOrder(
                customer_id=test_customer,
                parcel_name='Test Package',
                weight=2.5,
                pickup_address='123 Main St',
                destination_address='456 Oak Ave',
                price=50.0,
                status='picked_up'
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id
        
        response = client.delete(f'/api/orders/{order_id}', headers=auth_headers)
        
        assert response.status_code == 400
        assert 'Can only cancel before pickup' in response.get_json()['error']
