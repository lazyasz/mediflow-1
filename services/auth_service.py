# ============================================================
# services/auth_service.py — Authentication Logic
# ============================================================

from models import db
from models.user import User
from models.patient import Patient
from models.doctor import Doctor


def register_user(email, password, role, hospital_id, name='', age=0, phone='', bcrypt=None):
    """
    Register a new user with a linked profile (Patient or Doctor).
    Returns (user, error_message).
    """
    if User.query.filter_by(email=email).first():
        return None, 'Email already registered'

    password_hash = bcrypt.generate_password_hash(password).decode('utf-8') if bcrypt else password
    user = User(
        email=email,
        password_hash=password_hash,
        role=role,
        hospital_id=hospital_id,
    )
    db.session.add(user)
    db.session.flush()  # Get user.id

    if role == 'patient':
        patient = Patient(
            user_id=user.id,
            hospital_id=hospital_id,
            name=name or email.split('@')[0],
            age=age,
            phone=phone,
        )
        db.session.add(patient)
    elif role == 'doctor':
        doctor = Doctor(
            user_id=user.id,
            hospital_id=hospital_id,
            name=name or email.split('@')[0],
            department='General OPD',
        )
        db.session.add(doctor)

    db.session.commit()
    return user, None


def authenticate_user(email, password, bcrypt=None):
    """
    Authenticate user by email/password.
    Returns (user, error_message).
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        return None, 'Invalid email or password'

    if bcrypt:
        if not bcrypt.check_password_hash(user.password_hash, password):
            return None, 'Invalid email or password'
    else:
        if user.password_hash != password:
            return None, 'Invalid email or password'

    if not user.is_active:
        return None, 'Account is deactivated'

    return user, None


def get_user_profile(user):
    """Get the linked profile (Patient or Doctor) for a user."""
    if user.role == 'patient':
        return user.patient_profile
    elif user.role == 'doctor':
        return user.doctor_profile
    return None
