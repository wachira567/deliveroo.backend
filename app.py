# Flask App Factory
from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from extensions import db, bcrypt, jwt, mail
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()


def create_app(config=None):
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///deliveroo.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER'] = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_HOST_USER')
    app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASSWORD')
    
    # Override with provided config
    if config:
        app.config.update(config)
    
    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://localhost:3000",
                "https://deliveroo-frontend-ten.vercel.app"
            ],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    Migrate(app, db)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.orders import orders_bp
    from routes.courier import courier_bp
    from routes.admin import admin_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(orders_bp, url_prefix='/api')
    app.register_blueprint(courier_bp, url_prefix='/api')
    app.register_blueprint(admin_bp, url_prefix='/api')
    
    from routes.payments import payments_bp
    app.register_blueprint(payments_bp, url_prefix='/api/payments')

    # JWT Error handlers
    from flask import jsonify
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            "error": "Invalid token",
            "details": error
        }), 422

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            "error": "Request does not contain an access token",
            "details": error
        }), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "error": "Token has expired",
            "details": "token_expired"
        }), 401
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app


if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
