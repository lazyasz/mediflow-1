# ============================================================
# routes/auth.py — Authentication Routes
# ============================================================

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, make_response
from flask_jwt_extended import (
    create_access_token, set_access_cookies, unset_jwt_cookies,
    get_jwt_identity, verify_jwt_in_request
)
from services.auth_service import register_user, authenticate_user
from services.activity_service import log_activity
from models.hospital import Hospital

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET'])
def login_page():
    try:
        verify_jwt_in_request()
        return redirect(url_for('dashboard.index'))
    except Exception:
        pass
    hospitals = Hospital.query.filter_by(is_active=True).all()
    return render_template('auth/login.html', hospitals=hospitals)


@auth_bp.route('/register', methods=['GET'])
def register_page():
    hospitals = Hospital.query.filter_by(is_active=True).all()
    return render_template('auth/register.html', hospitals=hospitals)


@auth_bp.route('/login', methods=['POST'])
def login():
    from flask import current_app
    bcrypt = current_app.extensions.get('bcrypt')
    data = request.form if request.form else request.json or {}
    email = data.get('email', '').strip()
    password = data.get('password', '')

    user, error = authenticate_user(email, password, bcrypt)
    if error:
        if request.form:
            hospitals = Hospital.query.filter_by(is_active=True).all()
            return render_template('auth/login.html', error=error, hospitals=hospitals)
        return jsonify({'error': error}), 401

    # Use string identity for JWT
    token = create_access_token(identity=str(user.id))
    log_activity(user.hospital_id, 'login', f'{user.email} logged in', user.id)

    if request.form:
        resp = make_response(redirect(url_for('dashboard.index')))
        set_access_cookies(resp, token)
        return resp

    resp = jsonify({'success': True, 'role': user.role})
    set_access_cookies(resp, token)
    return resp


@auth_bp.route('/register', methods=['POST'])
def register():
    from flask import current_app
    bcrypt = current_app.extensions.get('bcrypt')
    data = request.form if request.form else request.json or {}

    email = data.get('email', '').strip()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    age = int(data.get('age', 0) or 0)
    hospital_id = int(data.get('hospital_id', 1) or 1)

    if not email or not password:
        if request.form:
            hospitals = Hospital.query.filter_by(is_active=True).all()
            return render_template('auth/register.html', error='Email and password required', hospitals=hospitals)
        return jsonify({'error': 'Email and password required'}), 400

    user, error = register_user(email, password, 'patient', hospital_id, name, age, phone, bcrypt)
    if error:
        if request.form:
            hospitals = Hospital.query.filter_by(is_active=True).all()
            return render_template('auth/register.html', error=error, hospitals=hospitals)
        return jsonify({'error': error}), 400

    log_activity(hospital_id, 'register', f'{email} registered as patient', user.id)
    token = create_access_token(identity=str(user.id))

    if request.form:
        resp = make_response(redirect(url_for('dashboard.index')))
        set_access_cookies(resp, token)
        return resp

    resp = jsonify({'success': True, 'role': user.role})
    set_access_cookies(resp, token)
    return resp


@auth_bp.route('/logout')
def logout():
    resp = make_response(redirect(url_for('auth.login_page')))
    unset_jwt_cookies(resp)
    return resp
