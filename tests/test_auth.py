import pytest
from extensions import db, bcrypt
from models import User


class TestAuth:
    def test_register_success(self, client):
        response = client.post('/api/register', json={
            'full_name': 'New User',
            'email': 'newuser@test.com',
            'password': 'password123',
            'phone': '+254700000000'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['user']['email'] == 'newuser@test.com'
        assert 'access_token' in data
        assert 'refresh_token' in data

    def test_register_missing_fields(self, client):
        response = client.post('/api/register', json={
            'full_name': 'Test User'
        })
        assert response.status_code == 400

    def test_register_duplicate_email(self, client, test_customer):
        response = client.post('/api/register', json={
            'full_name': 'Duplicate User',
            'email': 'customer@test.com',
            'password': 'password123'
        })
        assert response.status_code == 400
        assert 'already registered' in response.get_json()['error']

    def test_register_courier_without_vehicle(self, client):
        response = client.post('/api/register', json={
            'full_name': 'Courier User',
            'email': 'newcourier@test.com',
            'password': 'password123',
            'role': 'courier'
        })
        assert response.status_code == 400
        assert 'Vehicle type and plate number are required' in response.get_json()['error']

    def test_register_courier_with_vehicle(self, client):
        response = client.post('/api/register', json={
            'full_name': 'Courier User',
            'email': 'newcourier@test.com',
            'password': 'password123',
            'role': 'courier',
            'vehicle_type': 'Motorcycle',
            'plate_number': 'XYZ123AB'
        })
        assert response.status_code == 201
        data = response.get_json()
        assert data['user']['role'] == 'courier'

    def test_login_success(self, client, test_customer):
        response = client.post('/api/login', json={
            'email': 'customer@test.com',
            'password': 'password123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert data['user']['email'] == 'customer@test.com'

    def test_login_wrong_password(self, client, test_customer):
        response = client.post('/api/login', json={
            'email': 'customer@test.com',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post('/api/login', json={
            'email': 'nonexistent@test.com',
            'password': 'password123'
        })
        assert response.status_code == 401

    def test_get_current_user(self, client, test_customer, auth_headers):
        response = client.get('/api/me', headers=auth_headers)
        assert response.status_code == 200
        data = response.get_json()
        assert data['email'] == 'customer@test.com'
        assert data['role'] == 'customer'

    def test_get_current_user_unauthorized(self, client):
        response = client.get('/api/me')
        assert response.status_code == 401

    def test_refresh_token(self, client, test_customer):
        # First login to get refresh token
        login_response = client.post('/api/login', json={
            'email': 'customer@test.com',
            'password': 'password123'
        })
        refresh_token = login_response.get_json()['refresh_token']
        
        # Use refresh token to get new access token
        response = client.post('/api/refresh', json={
            'refresh_token': refresh_token
        })
        assert response.status_code == 200
        assert 'access_token' in response.get_json()

    def test_logout(self, client, test_customer, auth_headers):
        response = client.post('/api/logout', headers=auth_headers)
        assert response.status_code == 200
        assert 'Successfully logged out' in response.get_json()['message']
