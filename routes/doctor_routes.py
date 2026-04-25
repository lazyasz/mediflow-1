# ============================================================
# routes/doctor_routes.py — Doctor API
# ============================================================

from flask import Blueprint, request, jsonify
from utils.decorators import role_required, get_current_hospital_id
from models.doctor import Doctor

doctor_bp = Blueprint('doctors', __name__, url_prefix='/api/doctors')


@doctor_bp.route('', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def list_doctors():
    hospital_id = get_current_hospital_id()
    dept = request.args.get('department')
    query = Doctor.query.filter_by(hospital_id=hospital_id)
    if dept:
        query = query.filter_by(department=dept)
    return jsonify([d.to_dict() for d in query.all()])


@doctor_bp.route('/<int:did>', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def get_doctor(did):
    d = Doctor.query.get_or_404(did)
    return jsonify(d.to_dict())


@doctor_bp.route('/<int:did>/schedule', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def doctor_schedule(did):
    from services.appointment_service import get_doctor_schedule
    start = request.args.get('start_date')
    days = request.args.get('days', 7, type=int)
    schedule = get_doctor_schedule(did, start, days)
    return jsonify(schedule)
