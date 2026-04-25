# ============================================================
# app.py — Application Factory + Entry Point
# ============================================================

import os
import sys
import threading
import time
from flask import Flask, redirect, url_for, render_template
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_socketio import SocketIO

from config import config_by_name
from models import db

# Extensions (initialized here, bound to app in create_app)
jwt = JWTManager()
bcrypt = Bcrypt()
socketio = SocketIO()


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['development']))

    # Init extensions
    db.init_app(app)
    jwt.init_app(app)
    bcrypt.init_app(app)
    CORS(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')

    # Store bcrypt in extensions for easy access
    app.extensions['bcrypt'] = bcrypt

    # JWT error handlers
    @jwt.unauthorized_loader
    def unauthorized_callback(reason):
        from flask import request as req
        if req.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Authentication required'}), 401
        return redirect(url_for('auth.login_page'))

    @jwt.expired_token_loader
    def expired_callback(jwt_header, jwt_data):
        from flask import request as req
        if req.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Token expired'}), 401
        return redirect(url_for('auth.login_page'))

    @jwt.invalid_token_loader
    def invalid_callback(reason):
        from flask import request as req
        if req.path.startswith('/api/'):
            from flask import jsonify
            return jsonify({'error': 'Invalid token'}), 401
        return redirect(url_for('auth.login_page'))

    # Register blueprints
    from routes.auth import auth_bp
    from routes.dashboard import dashboard_bp
    from routes.queue_routes import queue_bp
    from routes.appointment_routes import appt_bp
    from routes.patient_routes import patient_bp
    from routes.doctor_routes import doctor_bp
    from routes.admin_routes import admin_bp
    from routes.activity_routes import activity_bp
    from routes.management_routes import mgmt_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(queue_bp)
    app.register_blueprint(appt_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(activity_bp)
    app.register_blueprint(mgmt_bp)

    # Register socket events
    from sockets.events import register_socket_events
    register_socket_events(socketio)

    # Landing page route
    @app.route('/')
    def landing():
        try:
            from flask_jwt_extended import verify_jwt_in_request
            verify_jwt_in_request()
            return redirect(url_for('dashboard.index'))
        except Exception:
            pass
        return render_template('index.html')

    # Create tables
    with app.app_context():
        db.create_all()

    # Start background queue rebalancer (skip during seeding)
    if not os.environ.get('SEED_MODE'):
        _start_rebalancer(app, socketio)

    return app


def _start_rebalancer(app, socketio):
    """
    Background daemon thread: re-scores every waiting patient every 60 s.
    Ensures wait-time escalation is reflected in real-time priority order.
    """
    def _run():
        # Small initial delay so the first app request can complete first
        time.sleep(10)
        while True:
            try:
                with app.app_context():
                    from models.hospital import Hospital
                    from services.queue_service import rebalance_queue
                    hospitals = Hospital.query.filter_by(is_active=True).all()
                    for h in hospitals:
                        count = rebalance_queue(h.id)
                        if count > 0:
                            socketio.emit(
                                'queue_updated',
                                {'hospital_id': h.id, 'rebalanced': True},
                                room=f'hospital_{h.id}'
                            )
            except Exception as exc:
                print(f'[Rebalancer] Error: {exc}')
            time.sleep(60)

    t = threading.Thread(target=_run, daemon=True, name='queue-rebalancer')
    t.start()
    print('[Rebalancer] Background queue rebalancer started.')


# ============================================================
# Entry point
# ============================================================
if __name__ == '__main__':
    app = create_app()
    print("=" * 50)
    print("  MediFlow 2.0 — Hospital Queue Management")
    print("  Open http://localhost:5000")
    print("=" * 50)
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
