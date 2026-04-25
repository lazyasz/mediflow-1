# ============================================================
# services/queue_service.py — Queue Operations
# ============================================================

from datetime import datetime, timezone
from models import db
from models.queue_entry import QueueEntry
from models.patient import Patient
from models.doctor import Doctor
from models.hospital import Hospital
from services.priority_engine import (
    compute_priority_score, add_to_heap, pop_for_doctor,
    rebuild_heap, clear_heap
)
from utils.helpers import generate_token


def add_to_queue(patient_id, doctor_id, hospital_id, department, symptoms='',
                 priority_label='normal', is_walk_in=True, appointment_id=None):
    """
    Add a patient to the queue. Computes priority, generates token, returns QueueEntry.
    """
    patient = Patient.query.get(patient_id)
    if not patient:
        return None, 'Patient not found'

    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return None, 'Doctor not found'

    # Generate sequential token
    today_count = QueueEntry.query.filter(
        QueueEntry.hospital_id == hospital_id,
        QueueEntry.department == department,
        db.func.date(QueueEntry.check_in_time) == datetime.now(timezone.utc).date()
    ).count()
    token = generate_token(department, today_count + 1)

    # Compute priority
    score = compute_priority_score(priority_label, patient.age, wait_minutes=0)

    # Estimate wait time
    est_wait = estimate_wait_time(hospital_id, department, doctor_id, priority_label)

    entry = QueueEntry(
        token=token,
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        department=department,
        priority_label=priority_label,
        priority_score=score,
        symptoms=symptoms,
        status='waiting',
        is_walk_in=is_walk_in,
        appointment_id=appointment_id,
        est_wait_minutes=est_wait,
    )
    db.session.add(entry)
    db.session.commit()

    # Add to in-memory heap
    add_to_heap(hospital_id, entry.id, score)

    return entry, None


def call_next_patient(doctor_id, hospital_id):
    """
    Call the next highest-priority patient for a specific doctor.
    Returns (QueueEntry, error_message).
    """
    # Get all waiting entries and their doctor assignments
    waiting = QueueEntry.query.filter_by(
        hospital_id=hospital_id,
        status='waiting'
    ).all()

    waiting_map = {e.id: e.doctor_id for e in waiting}

    entry_id = pop_for_doctor(hospital_id, doctor_id, waiting_map)

    if not entry_id:
        # Fallback: direct DB query (in case heap is stale)
        entry = QueueEntry.query.filter_by(
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            status='waiting'
        ).order_by(QueueEntry.priority_score.desc(), QueueEntry.check_in_time.asc()).first()
    else:
        entry = QueueEntry.query.get(entry_id)

    if not entry:
        return None, 'No patients waiting'

    entry.status = 'called'
    entry.called_time = datetime.now(timezone.utc)
    db.session.commit()

    return entry, None


def mark_complete(queue_entry_id):
    """Mark a queue entry as completed."""
    entry = QueueEntry.query.get(queue_entry_id)
    if not entry:
        return None, 'Entry not found'

    entry.status = 'completed'
    entry.completed_time = datetime.now(timezone.utc)
    db.session.commit()

    return entry, None


def escalate_priority(queue_entry_id, reason='Emergency'):
    """Emergency override — set to maximum priority."""
    entry = QueueEntry.query.get(queue_entry_id)
    if not entry:
        return None, 'Entry not found'

    entry.priority_label = 'critical'
    entry.priority_score = 999.0  # Maximum
    entry.est_wait_minutes = 0
    db.session.commit()

    # Re-add to heap with max priority
    add_to_heap(entry.hospital_id, entry.id, 999.0)

    return entry, None


def escalate_by_token(token, hospital_id, reason='Emergency'):
    """Emergency override by token string."""
    entry = QueueEntry.query.filter_by(
        token=token, hospital_id=hospital_id, status='waiting'
    ).first()
    if not entry:
        return None, f'Token {token} not found or not waiting'
    return escalate_priority(entry.id, reason)


def transfer_patient(queue_entry_id, new_doctor_id):
    """Transfer a patient to a different doctor."""
    entry = QueueEntry.query.get(queue_entry_id)
    if not entry:
        return None, 'Entry not found'

    new_doctor = Doctor.query.get(new_doctor_id)
    if not new_doctor:
        return None, 'Doctor not found'

    entry.doctor_id = new_doctor_id
    entry.department = new_doctor.department
    db.session.commit()

    return entry, None


def get_queue(hospital_id, department=None, doctor_id=None, status='waiting'):
    """Get sorted queue entries."""
    query = QueueEntry.query.filter_by(hospital_id=hospital_id)

    if status:
        query = query.filter_by(status=status)
    if department:
        query = query.filter_by(department=department)
    if doctor_id:
        query = query.filter_by(doctor_id=doctor_id)

    return query.order_by(
        QueueEntry.priority_score.desc(),
        QueueEntry.check_in_time.asc()
    ).all()


def get_queue_position(queue_entry_id):
    """Get a patient's position in queue (1-based)."""
    entry = QueueEntry.query.get(queue_entry_id)
    if not entry or entry.status != 'waiting':
        return 0

    ahead = QueueEntry.query.filter(
        QueueEntry.hospital_id == entry.hospital_id,
        QueueEntry.doctor_id == entry.doctor_id,
        QueueEntry.status == 'waiting',
        db.or_(
            QueueEntry.priority_score > entry.priority_score,
            db.and_(
                QueueEntry.priority_score == entry.priority_score,
                QueueEntry.check_in_time < entry.check_in_time,
            )
        )
    ).count()

    return ahead + 1


def estimate_wait_time(hospital_id, department, doctor_id, priority_label):
    """Estimate wait time in minutes based on patients ahead."""
    doctor = Doctor.query.get(doctor_id)
    consult_time = doctor.avg_consult_minutes if doctor else 12

    ahead = QueueEntry.query.filter(
        QueueEntry.hospital_id == hospital_id,
        QueueEntry.doctor_id == doctor_id,
        QueueEntry.status == 'waiting',
    ).count()

    return max(1, ahead * consult_time)


def rebalance_queue(hospital_id):
    """
    Recalculate priority scores for all waiting patients
    (accounts for increased wait time) and rebuild the heap.
    """
    waiting = QueueEntry.query.filter_by(
        hospital_id=hospital_id,
        status='waiting'
    ).all()

    now = datetime.now(timezone.utc)
    entries_for_heap = []

    for entry in waiting:
        check_in = entry.check_in_time
        if check_in and check_in.tzinfo is None:
            check_in = check_in.replace(tzinfo=timezone.utc)
        wait_minutes = (now - check_in).total_seconds() / 60 if check_in else 0

        patient = entry.patient
        age = patient.age if patient else 30

        new_score = compute_priority_score(entry.priority_label, age, wait_minutes)

        # Keep emergency overrides at max
        if entry.priority_score >= 999.0:
            new_score = 999.0

        entry.priority_score = new_score
        entry.est_wait_minutes = estimate_wait_time(
            hospital_id, entry.department, entry.doctor_id, entry.priority_label
        )
        entries_for_heap.append((entry.id, new_score))

    db.session.commit()
    rebuild_heap(hospital_id, entries_for_heap)

    return len(waiting)


def auto_assign_doctor(hospital_id, department):
    """
    Find the available doctor in the given department with the shortest
    current waiting queue — implements automatic queue load-balancing.

    Returns doctor_id or None if no doctor found.
    """
    doctors = Doctor.query.filter_by(
        hospital_id=hospital_id,
        department=department,
        is_available=True,
    ).all()

    if not doctors:
        # Fallback: any available doctor in hospital
        doctors = Doctor.query.filter_by(
            hospital_id=hospital_id,
            is_available=True,
        ).all()

    if not doctors:
        return None

    # Pick doctor with minimum waiting patients
    best_doctor = min(
        doctors,
        key=lambda d: QueueEntry.query.filter_by(
            doctor_id=d.id, status='waiting'
        ).count()
    )
    return best_doctor.id


def rebalance_all_hospitals():
    """
    Convenience wrapper called by the background rebalancer thread.
    Rebalances all active hospitals and returns a summary dict.
    """
    hospitals = Hospital.query.filter_by(is_active=True).all()
    results = {}
    for h in hospitals:
        count = rebalance_queue(h.id)
        results[h.id] = count
    return results
