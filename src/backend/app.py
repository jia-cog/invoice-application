from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
from routes.auth import auth_bp
from routes.invoices import invoices_bp
from routes.reports import reports_bp

def create_app(config_class=None):
    app = Flask(__name__)
    app.config.from_object(config_class or Config)

    # Fail fast if required secret keys are not configured
    if not app.config.get('JWT_SECRET_KEY'):
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is required but not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    if not app.config.get('SECRET_KEY'):
        raise RuntimeError(
            "SECRET_KEY environment variable is required but not set. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(invoices_bp, url_prefix='/api/invoices')
    app.register_blueprint(reports_bp, url_prefix='/api/reports')
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy', 'message': 'Invoice API is running'}), 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        print(f"JWT Error: Token expired. Header: {jwt_header}, Payload: {jwt_payload}")
        return jsonify({'error': 'Token has expired'}), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        print(f"JWT Error: Invalid token. Error: {error}")
        return jsonify({'error': 'Invalid token', 'debug': str(error)}), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        print(f"JWT Error: Missing token. Error: {error}")
        return jsonify({'error': 'Authorization token is required'}), 401
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
