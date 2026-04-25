# ============================================================
# utils/decorators.py — Auth & Scope Decorators
# ============================================================

from functools import wraps
from flask import jsonify, redirect, url_for, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from models.user import User


def role_required(*roles):
    """
    Decorator that restricts access to specific user roles.
    Usage: @role_required('admin', 'doctor')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                verify_jwt_in_request()
            except Exception:
                # For page routes, redirect to login; for API routes, return 401
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('auth.login_page'))

            user_id = get_jwt_identity()
            user = User.query.get(int(user_id))

            if not user or not user.is_active:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Account inactive or not found'}), 403
                return redirect(url_for('auth.login_page'))

            if user.role not in roles and not user.is_superadmin:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'Insufficient permissions'}), 403
                return redirect(url_for('auth.login_page'))

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def get_current_user():
    """Get the current authenticated user from JWT."""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        return User.query.get(int(user_id))
    except Exception:
        return None


def get_current_hospital_id():
    """Get the hospital_id of the current authenticated user."""
    user = get_current_user()
    return user.hospital_id if user else None
