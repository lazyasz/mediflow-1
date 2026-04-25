# ============================================================
# models/hospital.py — Hospital (Multi-Tenant Root)
# ============================================================

from datetime import datetime, timezone
from models import db


class Hospital(db.Model):
    __tablename__ = 'hospitals'

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(200), nullable=False)
    code       = db.Column(db.String(50), unique=True, nullable=False)  # URL-safe slug
    address    = db.Column(db.String(500), default='')
    phone      = db.Column(db.String(20), default='')
    logo_url   = db.Column(db.String(500), default='')
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    users        = db.relationship('User', backref='hospital', lazy='dynamic')
    patients     = db.relationship('Patient', backref='hospital', lazy='dynamic')
    doctors      = db.relationship('Doctor', backref='hospital', lazy='dynamic')
    queue_entries = db.relationship('QueueEntry', backref='hospital', lazy='dynamic')
    appointments = db.relationship('Appointment', backref='hospital', lazy='dynamic')
    activity_logs = db.relationship('ActivityLog', backref='hospital', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'address': self.address,
            'phone': self.phone,
            'logo_url': self.logo_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Hospital {self.name}>'
