# ============================================================
# services/activity_service.py — Event Logging & Feed
# ============================================================

from models import db
from models.activity_log import ActivityLog


def log_activity(hospital_id, action, details='', user_id=None, ip_address=''):
    entry = ActivityLog(
        hospital_id=hospital_id, user_id=user_id,
        action=action, details=details, ip_address=ip_address,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def get_feed(hospital_id, limit=50):
    return ActivityLog.query.filter_by(
        hospital_id=hospital_id
    ).order_by(ActivityLog.timestamp.desc()).limit(limit).all()


def get_logs(hospital_id, action=None, page=1, per_page=50):
    query = ActivityLog.query.filter_by(hospital_id=hospital_id)
    if action:
        query = query.filter_by(action=action)
    return query.order_by(ActivityLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False)


def format_feed_message(action, details):
    icons = {
        'login': '🔐', 'register': '👤', 'checkin': '🏥',
        'token_generated': '🎫', 'appointment_booked': '📅',
        'appointment_cancelled': '❌', 'priority_override': '⚡',
        'patient_called': '📣', 'patient_completed': '✅',
        'transfer': '🔄', 'system': '⚙️',
    }
    return f"{icons.get(action, '📌')} {details}"
