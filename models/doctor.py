# ============================================================
# models/doctor.py — Doctor Profile
# ============================================================

from datetime import datetime, timezone
from models import db


class Doctor(db.Model):
    __tablename__ = 'doctors'

    id                  = db.Column(db.Integer, primary_key=True)
    user_id             = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    hospital_id         = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name                = db.Column(db.String(200), nullable=False)
    specialization      = db.Column(db.String(200), default='')
    department          = db.Column(db.String(200), nullable=False)
    avg_consult_minutes = db.Column(db.Integer, default=12)
    is_available        = db.Column(db.Boolean, default=True)
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    queue_entries = db.relationship('QueueEntry', backref='doctor', lazy='dynamic')
    appointments  = db.relationship('Appointment', backref='doctor', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'hospital_id': self.hospital_id,
            'name': self.name,
            'specialization': self.specialization,
            'department': self.department,
            'avg_consult_minutes': self.avg_consult_minutes,
            'is_available': self.is_available,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Doctor {self.name} ({self.department})>'
