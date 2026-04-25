# ============================================================
# routes/dashboard.py — Role-Based Dashboard Pages
# ============================================================

from flask import Blueprint, render_template, redirect, url_for
from utils.decorators import get_current_user, role_required
from models.doctor import Doctor
from models.patient import Patient
from models.hospital import Hospital

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@role_required('patient', 'doctor', 'admin')
def index():
    user = get_current_user()
    if user.role == 'patient':
        return redirect(url_for('dashboard.patient_dashboard'))
    elif user.role == 'doctor':
        return redirect(url_for('dashboard.doctor_dashboard'))
    else:
        return redirect(url_for('dashboard.admin_dashboard'))


@dashboard_bp.route('/patient')
@role_required('patient')
def patient_dashboard():
    user = get_current_user()
    patient = Patient.query.filter_by(user_id=user.id).first()
    doctors = Doctor.query.filter_by(hospital_id=user.hospital_id, is_available=True).all()
    departments = sorted(set(d.department for d in doctors))
    hospital = Hospital.query.get(user.hospital_id)
    return render_template('patient/dashboard.html',
                           user=user, patient=patient, doctors=doctors,
                           departments=departments, hospital=hospital)


@dashboard_bp.route('/patient/appointments')
@role_required('patient')
def patient_appointments():
    user = get_current_user()
    patient = Patient.query.filter_by(user_id=user.id).first()
    doctors = Doctor.query.filter_by(hospital_id=user.hospital_id, is_available=True).all()
    departments = sorted(set(d.department for d in doctors))
    hospital = Hospital.query.get(user.hospital_id)
    return render_template('patient/book_appointment.html',
                           user=user, patient=patient, doctors=doctors,
                           departments=departments, hospital=hospital)


@dashboard_bp.route('/doctor')
@role_required('doctor')
def doctor_dashboard():
    user = get_current_user()
    doctor = Doctor.query.filter_by(user_id=user.id).first()
    hospital = Hospital.query.get(user.hospital_id)
    return render_template('doctor/dashboard.html',
                           user=user, doctor=doctor, hospital=hospital)


@dashboard_bp.route('/admin')
@role_required('admin')
def admin_dashboard():
    user = get_current_user()
    hospital = Hospital.query.get(user.hospital_id)
    doctors = Doctor.query.filter_by(hospital_id=user.hospital_id).all()
    departments = sorted(set(d.department for d in doctors))
    return render_template('admin/dashboard.html',
                           user=user, hospital=hospital, doctors=doctors,
                           departments=departments)


@dashboard_bp.route('/admin/logs')
@role_required('admin')
def admin_logs():
    user = get_current_user()
    hospital = Hospital.query.get(user.hospital_id)
    return render_template('admin/logs.html', user=user, hospital=hospital)


@dashboard_bp.route('/queue-display')
def queue_display():
    """Public queue display for hospital TVs / kiosks."""
    from flask import request as req
    hospital_id = req.args.get('hospital_id', 1, type=int)
    hospital = Hospital.query.get(hospital_id)
    return render_template('shared/queue_display.html', hospital=hospital)


@dashboard_bp.route('/admin/manage')
@role_required('admin')
def admin_manage():
    """Admin hospital & doctor management page."""
    user = get_current_user()
    hospital = Hospital.query.get(user.hospital_id)
    doctors = Doctor.query.filter_by(hospital_id=user.hospital_id).order_by(Doctor.department, Doctor.name).all()
    departments = sorted(set(d.department for d in doctors))
    return render_template('admin/manage.html',
                           user=user, hospital=hospital,
                           doctors=doctors, departments=departments)
