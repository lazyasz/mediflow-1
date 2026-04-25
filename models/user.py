# ============================================================
# models/user.py — User (Authentication Entity)
# ============================================================

from datetime import datetime, timezone
from models import db


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default='patient')  # patient | doctor | admin
    hospital_id   = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    is_active     = db.Column(db.Boolean, default=True)
    is_superadmin = db.Column(db.Boolean, default=False)
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    patient_profile = db.relationship('Patient', backref='user', uselist=False)
    doctor_profile  = db.relationship('Doctor', backref='user', uselist=False)
    activity_logs   = db.relationship('ActivityLog', backref='user', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'hospital_id': self.hospital_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
