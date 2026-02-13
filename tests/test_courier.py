import pytest
from models import ParcelOrder, User
from extensions import db


class TestCourier:
    def test_get_assigned_orders(self, client, test_courier, courier_auth_headers):
        response = client.get('/api/courier/orders', headers=courier_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'orders' in data
        assert 'total' in data

    def test_get_assigned_orders_forbidden_for_customer(self, client, test_customer, auth_headers):
        response = client.get('/api/courier/orders', headers=auth_headers)
        
        assert response.status_code == 403

    def test_update_location(self, client, test_courier, courier_auth_headers):
        # Assign an order to courier first
        with client.application.app_context():
            order = ParcelOrder(
                customer_id=test_courier,  # Using courier as customer for test
                courier_id=test_courier,
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
        
        response = client.patch(f'/api/orders/{order_id}/location', json={
            'lat': -1.286389,
            'lng': 36.817223
        }, headers=courier_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['current_lat'] == -1.286389
        assert data['current_lng'] == 36.817223

    def test_update_location_invalid_coordinates(self, client, test_courier, courier_auth_headers):
        with client.application.app_context():
            order = ParcelOrder(
                customer_id=test_courier,
                courier_id=test_courier,
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
        
        response = client.patch(f'/api/orders/{order_id}/location', json={
            'lat': 100,  # Invalid latitude
            'lng': 0
        }, headers=courier_auth_headers)
        
        assert response.status_code == 400
        assert 'Invalid coordinates' in response.get_json()['error']

    def test_update_status_picked_up(self, client, test_courier, courier_auth_headers):
        with client.application.app_context():
            order = ParcelOrder(
                customer_id=test_courier,
                courier_id=test_courier,
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
        
        response = client.patch(f'/api/orders/{order_id}/status', json={
            'status': 'picked_up'
        }, headers=courier_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['order']['status'] == 'picked_up'

    def test_update_status_invalid_transition(self, client, test_courier, courier_auth_headers):
        with client.application.app_context():
            order = ParcelOrder(
                customer_id=test_courier,
                courier_id=test_courier,
                parcel_name='Test Package',
                weight=1.0,
                pickup_address='123 Main St',
                destination_address='456 Oak Ave',
                price=50.0,
                status='pending'  # Can't transition from pending
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id
        
        response = client.patch(f'/api/orders/{order_id}/status', json={
            'status': 'picked_up'
        }, headers=courier_auth_headers)
        
        assert response.status_code == 400

    def test_update_status_delivered(self, client, test_courier, courier_auth_headers):
        with client.application.app_context():
            order = ParcelOrder(
                customer_id=test_courier,
                courier_id=test_courier,
                parcel_name='Test Package',
                weight=1.0,
                pickup_address='123 Main St',
                destination_address='456 Oak Ave',
                price=50.0,
                status='in_transit'
            )
            db.session.add(order)
            db.session.commit()
            order_id = order.id
        
        response = client.patch(f'/api/orders/{order_id}/status', json={
            'status': 'delivered'
        }, headers=courier_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['order']['status'] == 'delivered'
        assert data['order']['delivered_at'] is not None

    def test_get_courier_stats(self, client, test_courier, courier_auth_headers):
        response = client.get('/api/courier/stats', headers=courier_auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'total_orders' in data
        assert 'delivered_orders' in data
        assert 'earnings' in data
