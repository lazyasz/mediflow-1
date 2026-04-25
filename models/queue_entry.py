# ============================================================
# models/queue_entry.py — Queue Entry (Token + Priority)
# ============================================================

from datetime import datetime, timezone
from models import db


class QueueEntry(db.Model):
    __tablename__ = 'queue_entries'

    id              = db.Column(db.Integer, primary_key=True)
    token           = db.Column(db.String(20), nullable=False)
    patient_id      = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id       = db.Column(db.Integer, db.ForeignKey('doctors.id'), nullable=False)
    hospital_id     = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    department      = db.Column(db.String(200), nullable=False)

    # Priority
    priority_label  = db.Column(db.String(20), nullable=False, default='normal')  # critical | urgent | normal
    priority_score  = db.Column(db.Float, nullable=False, default=0.0)
    symptoms        = db.Column(db.Text, default='')

    # Status
    status          = db.Column(db.String(20), nullable=False, default='waiting')  # waiting | called | in_progress | completed | cancelled
    is_walk_in      = db.Column(db.Boolean, default=True)
    appointment_id  = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)

    # Timestamps
    check_in_time   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    called_time     = db.Column(db.DateTime, nullable=True)
    completed_time  = db.Column(db.DateTime, nullable=True)
    est_wait_minutes = db.Column(db.Integer, default=0)

    def to_dict(self):
        patient = self.patient
        doctor = self.doctor
        return {
            'id': self.id,
            'token': self.token,
            'patient_id': self.patient_id,
            'patient_name': patient.name if patient else 'Unknown',
            'patient_age': patient.age if patient else 0,
            'doctor_id': self.doctor_id,
            'doctor_name': doctor.name if doctor else 'Unknown',
            'hospital_id': self.hospital_id,
            'department': self.department,
            'priority_label': self.priority_label,
            'priority_score': round(self.priority_score, 2),
            'symptoms': self.symptoms,
            'status': self.status,
            'is_walk_in': self.is_walk_in,
            'appointment_id': self.appointment_id,
            'check_in_time': self.check_in_time.isoformat() if self.check_in_time else None,
            'called_time': self.called_time.isoformat() if self.called_time else None,
            'completed_time': self.completed_time.isoformat() if self.completed_time else None,
            'est_wait_minutes': self.est_wait_minutes,
        }

    def __repr__(self):
        return f'<QueueEntry {self.token} [{self.priority_label}]>'
