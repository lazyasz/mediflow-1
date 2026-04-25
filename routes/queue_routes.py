# ============================================================
# routes/queue_routes.py — Queue API Endpoints
# ============================================================

from flask import Blueprint, request, jsonify
from utils.decorators import get_current_user, role_required, get_current_hospital_id
from services import queue_service, activity_service
from services.queue_service import auto_assign_doctor
from models.queue_entry import QueueEntry
from models.patient import Patient
from models.doctor import Doctor

queue_bp = Blueprint('queue', __name__, url_prefix='/api/queue')


@queue_bp.route('', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def get_queue():
    hospital_id = get_current_hospital_id()
    dept = request.args.get('department')
    doctor_id = request.args.get('doctor_id', type=int)
    entries = queue_service.get_queue(hospital_id, department=dept, doctor_id=doctor_id)
    return jsonify([e.to_dict() for e in entries])


@queue_bp.route('/checkin', methods=['POST'])
@role_required('patient', 'doctor', 'admin')
def checkin():
    user = get_current_user()
    hospital_id = user.hospital_id
    data = request.json or {}

    patient_id = data.get('patient_id')
    if not patient_id and user.role == 'patient':
        p = Patient.query.filter_by(user_id=user.id).first()
        patient_id = p.id if p else None

    if not patient_id:
        return jsonify({'error': 'Patient ID required'}), 400

    doctor_id = data.get('doctor_id')
    if not doctor_id:
        dept = data.get('department', 'General OPD')
        # Auto-assign: pick doctor with shortest queue in department
        doctor_id = auto_assign_doctor(hospital_id, dept)
    if not doctor_id:
        return jsonify({'error': 'No available doctor in this department'}), 400

    entry, error = queue_service.add_to_queue(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        department=data.get('department', 'General OPD'),
        symptoms=data.get('symptoms', ''),
        priority_label=data.get('priority', 'normal'),
    )
    if error:
        return jsonify({'error': error}), 400

    patient = Patient.query.get(patient_id)
    activity_service.log_activity(
        hospital_id, 'token_generated',
        f"Token {entry.token} issued to {patient.name} ({entry.priority_label})",
        user.id
    )

    # Emit WebSocket event
    try:
        from app import socketio
        socketio.emit('queue_updated', {'hospital_id': hospital_id}, room=f'hospital_{hospital_id}')
        socketio.emit('new_activity', {
            'message': activity_service.format_feed_message(
                'token_generated', f"Token {entry.token} → {patient.name} ({entry.priority_label})")
        }, room=f'hospital_{hospital_id}')
    except Exception:
        pass

    return jsonify({
        'success': True,
        'token': entry.token,
        'est_wait': entry.est_wait_minutes,
        'doctor': entry.doctor.name if entry.doctor else 'Unknown',
        'position': queue_service.get_queue_position(entry.id),
        'queue_entry_id': entry.id,
    })


@queue_bp.route('/call-next', methods=['POST'])
@role_required('doctor', 'admin')
def call_next():
    user = get_current_user()
    hospital_id = user.hospital_id
    data = request.json or {}

    doctor_id = data.get('doctor_id')
    if not doctor_id and user.role == 'doctor':
        doc = Doctor.query.filter_by(user_id=user.id).first()
        doctor_id = doc.id if doc else None
    if not doctor_id:
        return jsonify({'error': 'Doctor ID required'}), 400

    entry, error = queue_service.call_next_patient(doctor_id, hospital_id)
    if error:
        return jsonify({'success': False, 'message': error})

    activity_service.log_activity(
        hospital_id, 'patient_called',
        f"Calling {entry.token} — {entry.patient.name}",
        user.id
    )

    try:
        from app import socketio
        socketio.emit('queue_updated', {'hospital_id': hospital_id}, room=f'hospital_{hospital_id}')
        socketio.emit('new_activity', {
            'message': activity_service.format_feed_message(
                'patient_called', f"Calling {entry.token} — {entry.patient.name}")
        }, room=f'hospital_{hospital_id}')
    except Exception:
        pass

    return jsonify({
        'success': True,
        'token': entry.token,
        'name': entry.patient.name if entry.patient else 'Unknown',
        'queue_entry_id': entry.id,
    })


@queue_bp.route('/complete', methods=['POST'])
@role_required('doctor', 'admin')
def complete():
    user = get_current_user()
    data = request.json or {}
    entry_id = data.get('queue_entry_id')
    if not entry_id:
        return jsonify({'error': 'queue_entry_id required'}), 400

    entry, error = queue_service.mark_complete(entry_id)
    if error:
        return jsonify({'error': error}), 400

    activity_service.log_activity(
        user.hospital_id, 'patient_completed',
        f"Completed {entry.token} — {entry.patient.name}",
        user.id
    )

    try:
        from app import socketio
        socketio.emit('queue_updated', {'hospital_id': user.hospital_id}, room=f'hospital_{user.hospital_id}')
    except Exception:
        pass

    return jsonify({'success': True, 'token': entry.token})


@queue_bp.route('/override', methods=['POST'])
@role_required('doctor', 'admin')
def override():
    user = get_current_user()
    data = request.json or {}
    token = data.get('token', '').strip()
    reason = data.get('reason', 'Emergency')
    auth_by = data.get('authorized_by', user.email)

    if not token:
        return jsonify({'error': 'Token required'}), 400

    entry, error = queue_service.escalate_by_token(token, user.hospital_id, reason)
    if error:
        return jsonify({'error': error}), 404

    msg = f"⚡ {token} escalated to CRITICAL. Reason: {reason}. Auth: {auth_by}"
    activity_service.log_activity(user.hospital_id, 'priority_override', msg, user.id)

    try:
        from app import socketio
        socketio.emit('queue_updated', {'hospital_id': user.hospital_id}, room=f'hospital_{user.hospital_id}')
        socketio.emit('new_activity', {'message': msg}, room=f'hospital_{user.hospital_id}')
    except Exception:
        pass

    return jsonify({'success': True, 'message': msg})


@queue_bp.route('/transfer', methods=['POST'])
@role_required('doctor', 'admin')
def transfer():
    user = get_current_user()
    data = request.json or {}
    entry_id = data.get('queue_entry_id')
    new_doctor_id = data.get('new_doctor_id')

    entry, error = queue_service.transfer_patient(entry_id, new_doctor_id)
    if error:
        return jsonify({'error': error}), 400

    activity_service.log_activity(
        user.hospital_id, 'transfer',
        f"Transferred {entry.token} to {entry.doctor.name}",
        user.id
    )

    try:
        from app import socketio
        socketio.emit('queue_updated', {'hospital_id': user.hospital_id}, room=f'hospital_{user.hospital_id}')
    except Exception:
        pass

    return jsonify({'success': True, 'token': entry.token, 'new_doctor': entry.doctor.name})


@queue_bp.route('/position/<int:entry_id>', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def get_position(entry_id):
    pos = queue_service.get_queue_position(entry_id)
    entry = QueueEntry.query.get(entry_id)
    return jsonify({
        'position': pos,
        'est_wait_minutes': entry.est_wait_minutes if entry else 0,
        'status': entry.status if entry else 'unknown',
    })


@queue_bp.route('/stats', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def stats():
    from services.analytics_service import get_dashboard_stats
    hospital_id = get_current_hospital_id()
    return jsonify(get_dashboard_stats(hospital_id))
