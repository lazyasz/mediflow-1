# ============================================================
# models/appointment.py — Specialist Appointment
# ============================================================

from datetime import datetime, timezone
from models import db


class Appointment(db.Model):
    __tablename__ = 'appointments'

    id               = db.Column(db.Integer, primary_key=True)
    patient_id       = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id        = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    hospital_id      = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    department       = db.Column(db.String(200), nullable=False)
    date             = db.Column(db.Date, nullable=False)
    time_slot        = db.Column(db.String(10), nullable=False)  # "09:00", "09:30", etc.
    duration_minutes = db.Column(db.Integer, default=30)
    type             = db.Column(db.String(20), default='in-person')  # in-person | telemedicine
    status           = db.Column(db.String(20), default='scheduled')  # scheduled | confirmed | cancelled | completed | merged
    notes            = db.Column(db.Text, default='')
    created_at       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Reverse link from queue entry
    queue_entries    = db.relationship('QueueEntry', backref='appointment', lazy='dynamic')

    def to_dict(self):
        patient = self.patient
        doctor = self.doctor
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': patient.name if patient else 'Unknown',
            'doctor_id': self.doctor_id,
            'doctor_name': doctor.name if doctor else 'Unknown',
            'hospital_id': self.hospital_id,
            'department': self.department,
            'date': self.date.isoformat() if self.date else None,
            'time_slot': self.time_slot,
            'duration_minutes': self.duration_minutes,
            'type': self.type,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Appointment {self.id} on {self.date} at {self.time_slot}>'
