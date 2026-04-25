# ============================================================
# models/patient.py — Patient Profile
# ============================================================

from datetime import datetime, timezone
from models import db


class Patient(db.Model):
    __tablename__ = 'patients'

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # nullable for walk-in without account
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name        = db.Column(db.String(200), nullable=False)
    age         = db.Column(db.Integer, default=0)
    phone       = db.Column(db.String(20), default='')
    gender      = db.Column(db.String(10), default='')
    notes       = db.Column(db.Text, default='')
    created_at  = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    queue_entries = db.relationship('QueueEntry', backref='patient', lazy='dynamic')
    appointments  = db.relationship('Appointment', backref='patient', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'hospital_id': self.hospital_id,
            'name': self.name,
            'age': self.age,
            'phone': self.phone,
            'gender': self.gender,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Patient {self.name}>'
