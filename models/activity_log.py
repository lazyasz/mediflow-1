# ============================================================
# models/activity_log.py — Activity / Audit Log
# ============================================================

from datetime import datetime, timezone
from models import db


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id          = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action      = db.Column(db.String(50), nullable=False)
    # Actions: login, register, checkin, token_generated, appointment_booked,
    #          appointment_cancelled, priority_override, patient_called,
    #          patient_completed, transfer, system
    details     = db.Column(db.Text, default='')
    ip_address  = db.Column(db.String(50), default='')
    timestamp   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'hospital_id': self.hospital_id,
            'user_id': self.user_id,
            'user_email': self.user.email if self.user else None,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }

    def __repr__(self):
        return f'<ActivityLog {self.action} at {self.timestamp}>'
