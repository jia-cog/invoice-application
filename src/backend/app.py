from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_identity, verify_jwt_in_request
from config import Config
from models import db, RequestLog
from routes.auth import auth_bp
from routes.invoices import invoices_bp
from routes.reports import reports_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app, origins=Config.CORS_ORIGINS)
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
    
    # Request logging middleware
    @app.after_request
    def log_request(response):
        if request.path.startswith('/api/'):
            user_id = None
            try:
                verify_jwt_in_request(optional=True)
                identity = get_jwt_identity()
                if identity:
                    user_id = int(identity)
            except Exception:
                pass

            log_entry = RequestLog(
                endpoint=request.path,
                method=request.method,
                user_id=user_id,
                status_code=response.status_code
            )
            try:
                db.session.add(log_entry)
                db.session.commit()
            except Exception:
                db.session.rollback()

        return response

    # Create tables
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5001)
