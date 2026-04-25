# ============================================================
# routes/management_routes.py — Admin CRUD for Hospitals & Doctors
# ============================================================

from flask import Blueprint, request, jsonify
from utils.decorators import role_required, get_current_hospital_id, get_current_user
from models import db
from models.hospital import Hospital
from models.doctor import Doctor
from models.user import User

mgmt_bp = Blueprint('management', __name__, url_prefix='/api/manage')


# ─────────────────────────────────────────────────────────────
# HOSPITAL
# ─────────────────────────────────────────────────────────────

@mgmt_bp.route('/hospital', methods=['GET'])
@role_required('admin')
def get_hospital():
    """Get current hospital details."""
    hospital_id = get_current_hospital_id()
    h = Hospital.query.get_or_404(hospital_id)
    return jsonify(h.to_dict())


@mgmt_bp.route('/hospital', methods=['PUT'])
@role_required('admin')
def update_hospital():
    """Update hospital settings (name, address, phone, logo)."""
    hospital_id = get_current_hospital_id()
    h = Hospital.query.get_or_404(hospital_id)
    data = request.json or {}

    if 'name' in data and data['name'].strip():
        h.name = data['name'].strip()
    if 'address' in data:
        h.address = data['address'].strip()
    if 'phone' in data:
        h.phone = data['phone'].strip()
    if 'logo_url' in data:
        h.logo_url = data['logo_url'].strip()

    db.session.commit()
    return jsonify({'success': True, 'hospital': h.to_dict()})


# ─────────────────────────────────────────────────────────────
# DOCTORS
# ─────────────────────────────────────────────────────────────

@mgmt_bp.route('/doctors', methods=['GET'])
@role_required('admin')
def list_doctors():
    """List all doctors in the hospital."""
    hospital_id = get_current_hospital_id()
    doctors = Doctor.query.filter_by(hospital_id=hospital_id).order_by(Doctor.department, Doctor.name).all()
    return jsonify([d.to_dict() for d in doctors])


@mgmt_bp.route('/doctors', methods=['POST'])
@role_required('admin')
def add_doctor():
    """
    Add a new doctor. Creates a user account + doctor profile.
    Body: { name, email, password, department, specialization, avg_consult_minutes }
    """
    from flask import current_app
    bcrypt = current_app.extensions.get('bcrypt')
    hospital_id = get_current_hospital_id()
    data = request.json or {}

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', 'doctor123')
    department = data.get('department', 'General OPD').strip()
    specialization = data.get('specialization', department).strip()
    avg_consult = int(data.get('avg_consult_minutes', 12))

    if not name or not email:
        return jsonify({'error': 'name and email are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    pw_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, password_hash=pw_hash, role='doctor', hospital_id=hospital_id)
    db.session.add(user)
    db.session.flush()

    doctor = Doctor(
        user_id=user.id,
        hospital_id=hospital_id,
        name=name,
        department=department,
        specialization=specialization,
        avg_consult_minutes=avg_consult,
    )
    db.session.add(doctor)
    db.session.commit()

    from services.activity_service import log_activity
    user_ctx = get_current_user()
    log_activity(hospital_id, 'system', f'Doctor added: {name} ({department})', user_ctx.id if user_ctx else None)

    return jsonify({'success': True, 'doctor': doctor.to_dict()}), 201


@mgmt_bp.route('/doctors/<int:did>', methods=['PUT'])
@role_required('admin')
def update_doctor(did):
    """Update doctor profile fields."""
    hospital_id = get_current_hospital_id()
    doctor = Doctor.query.filter_by(id=did, hospital_id=hospital_id).first_or_404()
    data = request.json or {}

    if 'name' in data and data['name'].strip():
        doctor.name = data['name'].strip()
    if 'department' in data and data['department'].strip():
        doctor.department = data['department'].strip()
    if 'specialization' in data:
        doctor.specialization = data['specialization'].strip()
    if 'avg_consult_minutes' in data:
        doctor.avg_consult_minutes = max(1, int(data['avg_consult_minutes']))

    db.session.commit()
    return jsonify({'success': True, 'doctor': doctor.to_dict()})


@mgmt_bp.route('/doctors/<int:did>/availability', methods=['POST'])
@role_required('admin')
def toggle_availability(did):
    """Toggle doctor availability on/off."""
    hospital_id = get_current_hospital_id()
    doctor = Doctor.query.filter_by(id=did, hospital_id=hospital_id).first_or_404()
    doctor.is_available = not doctor.is_available
    db.session.commit()
    return jsonify({'success': True, 'is_available': doctor.is_available, 'doctor': doctor.to_dict()})


@mgmt_bp.route('/doctors/<int:did>', methods=['DELETE'])
@role_required('admin')
def delete_doctor(did):
    """
    Soft-delete: deactivate doctor account. Does not delete records
    to preserve audit history.
    """
    hospital_id = get_current_hospital_id()
    doctor = Doctor.query.filter_by(id=did, hospital_id=hospital_id).first_or_404()
    doctor.is_available = False
    if doctor.user_id:
        u = User.query.get(doctor.user_id)
        if u:
            u.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': f'Dr. {doctor.name} deactivated'})


# ─────────────────────────────────────────────────────────────
# DEPARTMENTS
# ─────────────────────────────────────────────────────────────

@mgmt_bp.route('/departments', methods=['GET'])
@role_required('admin')
def list_departments():
    """List distinct departments for this hospital."""
    hospital_id = get_current_hospital_id()
    doctors = Doctor.query.filter_by(hospital_id=hospital_id).all()
    departments = sorted(set(d.department for d in doctors))
    # Enrich with stats
    from models.queue_entry import QueueEntry
    result = []
    for dept in departments:
        doc_count = Doctor.query.filter_by(hospital_id=hospital_id, department=dept, is_available=True).count()
        waiting = QueueEntry.query.filter_by(hospital_id=hospital_id, department=dept, status='waiting').count()
        result.append({'department': dept, 'doctors': doc_count, 'waiting': waiting})
    return jsonify(result)


# ─────────────────────────────────────────────────────────────
# MANUAL REBALANCE TRIGGER
# ─────────────────────────────────────────────────────────────

@mgmt_bp.route('/rebalance', methods=['POST'])
@role_required('admin')
def manual_rebalance():
    """Trigger an immediate queue priority rebalance for this hospital."""
    hospital_id = get_current_hospital_id()
    from services.queue_service import rebalance_queue
    count = rebalance_queue(hospital_id)
    try:
        from app import socketio
        socketio.emit('queue_updated', {'hospital_id': hospital_id, 'rebalanced': True}, room=f'hospital_{hospital_id}')
    except Exception:
        pass
    return jsonify({'success': True, 'patients_rebalanced': count})
