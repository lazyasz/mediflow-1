# ============================================================
# routes/admin_routes.py — Admin API
# ============================================================

from flask import Blueprint, request, jsonify
from utils.decorators import role_required, get_current_hospital_id, get_current_user
from services.analytics_service import get_dashboard_stats, get_doctor_efficiency, get_peak_hours

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/stats', methods=['GET'])
@role_required('admin')
def stats():
    hospital_id = get_current_hospital_id()
    return jsonify(get_dashboard_stats(hospital_id))


@admin_bp.route('/analytics/doctors', methods=['GET'])
@role_required('admin')
def doctor_analytics():
    hospital_id = get_current_hospital_id()
    return jsonify(get_doctor_efficiency(hospital_id))


@admin_bp.route('/analytics/peak-hours', methods=['GET'])
@role_required('admin')
def peak_hours():
    hospital_id = get_current_hospital_id()
    days = request.args.get('days', 7, type=int)
    return jsonify(get_peak_hours(hospital_id, days))
