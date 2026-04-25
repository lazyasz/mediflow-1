# ============================================================
# routes/patient_routes.py — Patient API
# ============================================================

from flask import Blueprint, request, jsonify
from utils.decorators import role_required, get_current_hospital_id
from models import db
from models.patient import Patient

patient_bp = Blueprint('patients', __name__, url_prefix='/api/patients')


@patient_bp.route('', methods=['GET'])
@role_required('doctor', 'admin')
def list_patients():
    hospital_id = get_current_hospital_id()
    q = request.args.get('q', '').strip()
    query = Patient.query.filter_by(hospital_id=hospital_id)
    if q:
        query = query.filter(
            db.or_(Patient.name.ilike(f'%{q}%'), Patient.phone.ilike(f'%{q}%'))
        )
    patients = query.order_by(Patient.name.asc()).all()
    return jsonify([p.to_dict() for p in patients])


@patient_bp.route('/<int:pid>', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def get_patient(pid):
    p = Patient.query.get_or_404(pid)
    return jsonify(p.to_dict())
