# ============================================================
# routes/activity_routes.py — Activity Feed & Logs API
# ============================================================

from flask import Blueprint, request, jsonify, make_response
from utils.decorators import role_required, get_current_hospital_id
from services.activity_service import get_feed, get_logs, format_feed_message
import csv
import io

activity_bp = Blueprint('activity', __name__, url_prefix='/api/activity')


@activity_bp.route('/feed', methods=['GET'])
@role_required('patient', 'doctor', 'admin')
def feed():
    hospital_id = get_current_hospital_id()
    limit = request.args.get('limit', 30, type=int)
    entries = get_feed(hospital_id, limit)
    return jsonify([{
        'id': e.id,
        'message': format_feed_message(e.action, e.details),
        'action': e.action,
        'timestamp': e.timestamp.isoformat() if e.timestamp else None,
    } for e in entries])


@activity_bp.route('/logs', methods=['GET'])
@role_required('admin')
def logs():
    hospital_id = get_current_hospital_id()
    action = request.args.get('action')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    result = get_logs(hospital_id, action, page, per_page)
    return jsonify({
        'logs': [e.to_dict() for e in result.items],
        'total': result.total,
        'pages': result.pages,
        'page': result.page,
    })


@activity_bp.route('/export', methods=['GET'])
@role_required('admin')
def export_logs():
    """Download all activity logs for this hospital as a CSV file."""
    hospital_id = get_current_hospital_id()
    action = request.args.get('action')  # optional filter

    # Pull all matching logs (no pagination — it's a file download)
    from models.activity_log import ActivityLog
    query = ActivityLog.query.filter_by(hospital_id=hospital_id)
    if action:
        query = query.filter_by(action=action)
    entries = query.order_by(ActivityLog.timestamp.desc()).all()

    # Build CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Action', 'Details', 'User', 'IP Address', 'Timestamp'])
    for e in entries:
        writer.writerow([
            e.id,
            e.action,
            e.details,
            e.user.email if e.user else 'system',
            e.ip_address or '',
            e.timestamp.isoformat() if e.timestamp else '',
        ])

    output.seek(0)
    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv; charset=utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename="mediflow_logs.csv"'
    return resp
