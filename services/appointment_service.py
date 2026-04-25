# ============================================================
# services/appointment_service.py — Specialist Booking
# ============================================================

from datetime import datetime, date, timedelta, timezone
from models import db
from models.appointment import Appointment
from models.doctor import Doctor
from models.patient import Patient
from utils.helpers import get_slot_times
from flask import current_app


def get_available_slots(doctor_id, target_date):
    """
    Get available time slots for a doctor on a specific date.
    Returns list of available slot strings like ["09:00", "10:30", ...].
    """
    all_slots = get_slot_times()

    # Get booked slots
    booked = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == target_date,
        Appointment.status.in_(['scheduled', 'confirmed']),
    ).all()

    booked_times = {a.time_slot for a in booked}
    available = [s for s in all_slots if s not in booked_times]

    return available


def book_appointment(patient_id, doctor_id, hospital_id, target_date, time_slot,
                     appt_type='in-person', notes=''):
    """
    Book a specialist appointment with conflict detection.
    Returns (Appointment, error_message).
    """
    doctor = Doctor.query.get(doctor_id)
    if not doctor:
        return None, 'Doctor not found'

    # Validate date range (up to 30 days in advance)
    today = date.today()
    max_date = today + timedelta(days=current_app.config.get('MAX_ADVANCE_BOOKING_DAYS', 30))

    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    if target_date < today:
        return None, 'Cannot book appointments in the past'
    if target_date > max_date:
        return None, f'Cannot book more than {current_app.config.get("MAX_ADVANCE_BOOKING_DAYS", 30)} days in advance'

    # Check for conflicts
    existing = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == target_date,
        Appointment.time_slot == time_slot,
        Appointment.status.in_(['scheduled', 'confirmed']),
    ).first()

    if existing:
        return None, f'Slot {time_slot} is already booked for {doctor.name} on {target_date}'

    # Check if patient already has appointment at same time
    patient_conflict = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.date == target_date,
        Appointment.time_slot == time_slot,
        Appointment.status.in_(['scheduled', 'confirmed']),
    ).first()

    if patient_conflict:
        return None, f'You already have an appointment at {time_slot} on {target_date}'

    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        department=doctor.department,
        date=target_date,
        time_slot=time_slot,
        type=appt_type,
        notes=notes,
        status='scheduled',
    )
    db.session.add(appointment)
    db.session.commit()

    return appointment, None


def cancel_appointment(appointment_id):
    """Cancel an appointment."""
    appt = Appointment.query.get(appointment_id)
    if not appt:
        return None, 'Appointment not found'
    if appt.status in ('cancelled', 'completed'):
        return None, f'Appointment is already {appt.status}'

    appt.status = 'cancelled'
    db.session.commit()
    return appt, None


def get_appointments(hospital_id, patient_id=None, doctor_id=None,
                     target_date=None, status=None):
    """Get filtered list of appointments."""
    query = Appointment.query.filter_by(hospital_id=hospital_id)

    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    if doctor_id:
        query = query.filter_by(doctor_id=doctor_id)
    if target_date:
        if isinstance(target_date, str):
            target_date = date.fromisoformat(target_date)
        query = query.filter_by(date=target_date)
    if status:
        query = query.filter_by(status=status)

    return query.order_by(Appointment.date.asc(), Appointment.time_slot.asc()).all()


def suggest_doctors(department, hospital_id, target_date=None):
    """
    Suggest doctors in a department, ranked by availability.
    Returns list of dicts with doctor info + available_slots count.
    """
    doctors = Doctor.query.filter_by(
        hospital_id=hospital_id,
        department=department,
        is_available=True,
    ).all()

    if not target_date:
        target_date = date.today()
    elif isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    results = []
    for doc in doctors:
        slots = get_available_slots(doc.id, target_date)
        results.append({
            **doc.to_dict(),
            'available_slots': len(slots),
            'slots': slots,
        })

    # Sort by most available
    results.sort(key=lambda x: x['available_slots'], reverse=True)
    return results


def get_doctor_schedule(doctor_id, start_date=None, days=7):
    """Get a doctor's schedule for a date range."""
    if not start_date:
        start_date = date.today()
    elif isinstance(start_date, str):
        start_date = date.fromisoformat(start_date)

    schedule = {}
    for i in range(days):
        d = start_date + timedelta(days=i)
        day_key = d.isoformat()
        appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.date == d,
            Appointment.status.in_(['scheduled', 'confirmed']),
        ).order_by(Appointment.time_slot.asc()).all()

        all_slots = get_slot_times()
        booked_times = {a.time_slot for a in appointments}

        schedule[day_key] = {
            'date': day_key,
            'appointments': [a.to_dict() for a in appointments],
            'available_slots': [s for s in all_slots if s not in booked_times],
            'booked_count': len(appointments),
            'total_slots': len(all_slots),
        }

    return schedule


def merge_to_queue(appointment_id, hospital_id):
    """
    Merge a scheduled appointment into the live walk-in queue.
    The appointment must be for today and in 'scheduled' status.

    Returns (QueueEntry, error_message).
    """
    appt = Appointment.query.get(appointment_id)
    if not appt:
        return None, 'Appointment not found'
    if appt.hospital_id != hospital_id:
        return None, 'Appointment does not belong to this hospital'
    if appt.status not in ('scheduled', 'confirmed'):
        return None, f'Appointment is already {appt.status}'
    if appt.date != date.today():
        return None, 'Only today\'s appointments can be merged into the queue'

    # Ensure patient exists
    patient = Patient.query.get(appt.patient_id)
    if not patient:
        return None, 'Patient not found'

    from services.queue_service import add_to_queue

    # Pre-booked patients get an 'urgent' priority boost as default
    # (receptionist / doctor can still override with escalate)
    entry, error = add_to_queue(
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        hospital_id=hospital_id,
        department=appt.department,
        symptoms=appt.notes or 'Pre-booked appointment',
        priority_label='urgent',   # boost for appointment holders
        is_walk_in=False,
        appointment_id=appt.id,
    )
    if error:
        return None, error

    # Mark appointment as merged
    appt.status = 'merged'
    db.session.commit()

    return entry, None
