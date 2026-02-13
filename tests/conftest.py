import pytest
import os
from app import create_app
from extensions import db, bcrypt
from models import User, ParcelOrder

os.environ['TESTING'] = 'True'


@pytest.fixture
def app():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'JWT_SECRET_KEY': 'test-jwt-secret',
        'WTF_CSRF_ENABLED': False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def test_customer(app):
    with app.app_context():
        user = User(
            full_name="Test Customer",
            email="customer@test.com",
            phone="+254700000001",
            role="customer"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        return user_id


@pytest.fixture
def test_courier(app):
    with app.app_context():
        user = User(
            full_name="Test Courier",
            email="courier@test.com",
            phone="+254700000002",
            role="courier",
            vehicle_type="Motorcycle",
            plate_number="ABC123DE"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        return user_id


@pytest.fixture
def test_admin(app):
    with app.app_context():
        user = User(
            full_name="Test Admin",
            email="admin@test.com",
            phone="+254700000003",
            role="admin"
        )
        user.set_password("password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        return user_id


@pytest.fixture
def auth_headers(client, test_customer):
    response = client.post('/api/login', json={
        'email': 'customer@test.com',
        'password': 'password123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def courier_auth_headers(client, test_courier):
    response = client.post('/api/login', json={
        'email': 'courier@test.com',
        'password': 'password123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def admin_auth_headers(client, test_admin):
    response = client.post('/api/login', json={
        'email': 'admin@test.com',
        'password': 'password123'
    })
    token = response.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}
