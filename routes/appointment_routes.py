# ============================================================
# routes/appointment_routes.py — Appointment API Endpoints
# ============================================================

from flask import Blueprint, request, jsonify
from utils.decorators import get_current_user, role_required, get_current_hospital_id
from services import appointment_service, activity_service
from models.patient import Patient
from models.doctor import Doctor

appt_bp = Blueprint('appointments', __name__, url_prefix='/api/appointments')


@appt_bp.route('', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def list_appointments():
    user = get_current_user()
    hospital_id = user.hospital_id
    patient_id = request.args.get('patient_id', type=int)
    doctor_id = request.args.get('doctor_id', type=int)
    target_date = request.args.get('date')
    status = request.args.get('status')

    if user.role == 'patient' and not patient_id:
        p = Patient.query.filter_by(user_id=user.id).first()
        patient_id = p.id if p else None

    if user.role == 'doctor' and not doctor_id:
        d = Doctor.query.filter_by(user_id=user.id).first()
        doctor_id = d.id if d else None

    appts = appointment_service.get_appointments(
        hospital_id, patient_id=patient_id, doctor_id=doctor_id,
        target_date=target_date, status=status
    )
    return jsonify([a.to_dict() for a in appts])


@appt_bp.route('/book', methods=['POST'])
@role_required('patient', 'doctor', 'admin')
def book():
    user = get_current_user()
    data = request.json or {}

    patient_id = data.get('patient_id')
    if not patient_id and user.role == 'patient':
        p = Patient.query.filter_by(user_id=user.id).first()
        patient_id = p.id if p else None
    if not patient_id:
        return jsonify({'error': 'Patient ID required'}), 400

    doctor_id = data.get('doctor_id')
    if not doctor_id:
        return jsonify({'error': 'Doctor ID required'}), 400

    appt, error = appointment_service.book_appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=user.hospital_id,
        target_date=data.get('date'),
        time_slot=data.get('time_slot'),
        appt_type=data.get('type', 'in-person'),
        notes=data.get('notes', ''),
    )
    if error:
        return jsonify({'error': error}), 400

    patient = Patient.query.get(patient_id)
    doctor = Doctor.query.get(doctor_id)
    activity_service.log_activity(
        user.hospital_id, 'appointment_booked',
        f"Appointment booked: {patient.name} with {doctor.name} on {appt.date} at {appt.time_slot}",
        user.id
    )

    try:
        from app import socketio
        socketio.emit('new_activity', {
            'message': f"📅 Appointment: {patient.name} → {doctor.name} on {appt.date}"
        }, room=f'hospital_{user.hospital_id}')
    except Exception:
        pass

    return jsonify({'success': True, 'appointment': appt.to_dict()})


@appt_bp.route('/cancel', methods=['POST'])
@role_required('patient', 'doctor', 'admin')
def cancel():
    user = get_current_user()
    data = request.json or {}
    appt_id = data.get('appointment_id')

    appt, error = appointment_service.cancel_appointment(appt_id)
    if error:
        return jsonify({'error': error}), 400

    activity_service.log_activity(
        user.hospital_id, 'appointment_cancelled',
        f"Appointment {appt_id} cancelled", user.id
    )
    return jsonify({'success': True})


@appt_bp.route('/slots', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def available_slots():
    doctor_id = request.args.get('doctor_id', type=int)
    target_date = request.args.get('date')
    if not doctor_id or not target_date:
        return jsonify({'error': 'doctor_id and date required'}), 400

    from datetime import date
    slots = appointment_service.get_available_slots(doctor_id, date.fromisoformat(target_date))
    return jsonify({'slots': slots, 'date': target_date, 'doctor_id': doctor_id})


@appt_bp.route('/doctors', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def suggest_doctors():
    hospital_id = get_current_hospital_id()
    department = request.args.get('department', '')
    target_date = request.args.get('date')
    doctors = appointment_service.suggest_doctors(department, hospital_id, target_date)
    return jsonify(doctors)


@appt_bp.route('/merge', methods=['POST'])
@role_required('doctor', 'admin')
def merge_appointment():
    """
    Merge a today's appointment into the live priority queue.
    Body: { appointment_id: int }
    """
    user = get_current_user()
    data = request.json or {}
    appt_id = data.get('appointment_id')
    if not appt_id:
        return jsonify({'error': 'appointment_id required'}), 400

    from services.appointment_service import merge_to_queue
    entry, error = merge_to_queue(appt_id, user.hospital_id)
    if error:
        return jsonify({'error': error}), 400

    from models.patient import Patient
    patient = Patient.query.get(entry.patient_id)
    activity_service.log_activity(
        user.hospital_id, 'token_generated',
        f"Appointment merged: Token {entry.token} → {patient.name if patient else 'Unknown'}",
        user.id
    )

    try:
        from app import socketio
        socketio.emit('queue_updated', {'hospital_id': user.hospital_id}, room=f'hospital_{user.hospital_id}')
        socketio.emit('new_activity', {
            'message': f"🔄 Appointment merged: {entry.token} → {patient.name if patient else 'Unknown'} (urgent)"
        }, room=f'hospital_{user.hospital_id}')
    except Exception:
        pass

    return jsonify({'success': True, 'token': entry.token, 'queue_entry_id': entry.id})
