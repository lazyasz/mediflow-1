# ============================================================
# services/analytics_service.py — Stats & Analytics
# ============================================================

from datetime import datetime, date, timezone, timedelta
from sqlalchemy import func
from models import db
from models.queue_entry import QueueEntry
from models.appointment import Appointment
from models.doctor import Doctor


def get_dashboard_stats(hospital_id):
    today = date.today()
    waiting = QueueEntry.query.filter_by(hospital_id=hospital_id, status='waiting').count()
    critical = QueueEntry.query.filter_by(hospital_id=hospital_id, status='waiting', priority_label='critical').count()
    tele = Appointment.query.filter(
        Appointment.hospital_id == hospital_id,
        Appointment.date == today,
        Appointment.type == 'telemedicine',
        Appointment.status.in_(['scheduled', 'confirmed']),
    ).count()

    avg_wait_result = db.session.query(func.avg(QueueEntry.est_wait_minutes)).filter(
        QueueEntry.hospital_id == hospital_id, QueueEntry.status == 'waiting'
    ).scalar()
    avg_wait = round(float(avg_wait_result), 1) if avg_wait_result else 0

    dept_loads = db.session.query(
        QueueEntry.department, func.count(QueueEntry.id)
    ).filter(
        QueueEntry.hospital_id == hospital_id, QueueEntry.status == 'waiting'
    ).group_by(QueueEntry.department).all()

    completed_today = QueueEntry.query.filter(
        QueueEntry.hospital_id == hospital_id,
        QueueEntry.status == 'completed',
        func.date(QueueEntry.completed_time) == today,
    ).count()

    return {
        'total_waiting': waiting,
        'critical_count': critical,
        'avg_wait_minutes': avg_wait,
        'telemedicine_active': tele,
        'completed_today': completed_today,
        'department_loads': [{'department': d, 'count': c} for d, c in dept_loads],
    }


def get_doctor_efficiency(hospital_id):
    doctors = Doctor.query.filter_by(hospital_id=hospital_id).all()
    results = []
    today = date.today()
    for doc in doctors:
        completed = QueueEntry.query.filter(
            QueueEntry.doctor_id == doc.id,
            QueueEntry.status == 'completed',
            func.date(QueueEntry.completed_time) == today,
        ).count()
        waiting = QueueEntry.query.filter_by(doctor_id=doc.id, status='waiting').count()
        results.append({
            'doctor_id': doc.id, 'name': doc.name,
            'department': doc.department,
            'completed_today': completed, 'waiting': waiting,
            'avg_consult_minutes': doc.avg_consult_minutes,
        })
    return results


def get_peak_hours(hospital_id, days=7):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    entries = QueueEntry.query.filter(
        QueueEntry.hospital_id == hospital_id,
        QueueEntry.check_in_time >= cutoff,
    ).all()

    hours = [0] * 24
    for e in entries:
        if e.check_in_time:
            hours[e.check_in_time.hour] += 1
    return [{'hour': h, 'count': c} for h, c in enumerate(hours)]
