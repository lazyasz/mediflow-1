# ============================================================
# seed.py — Database Seeder (Multi-Hospital Demo Data)
# ============================================================
import os
os.environ['SEED_MODE'] = '1'   # Suppress background rebalancer during seeding

from app import create_app, bcrypt
from models import db
from models.hospital import Hospital
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.queue_entry import QueueEntry
from models.appointment import Appointment
from models.activity_log import ActivityLog
from services.priority_engine import compute_priority_score, add_to_heap
from utils.helpers import generate_token
from datetime import datetime, date, timezone

app = create_app()

with app.app_context():
    db.drop_all()
    db.create_all()
    print("[SEED] Tables created.")

    # ── HOSPITAL 1 ─────────────────────────────────────────
    h1 = Hospital(name='City General Hospital', code='city-general',
                  address='42 MG Road, Bengaluru, Karnataka', phone='080-12345678')
    db.session.add(h1)

    # ── HOSPITAL 2 ─────────────────────────────────────────
    h2 = Hospital(name='Apollo Specialty Hospital', code='apollo-specialty',
                  address='21 Jubilee Hills, Hyderabad, Telangana', phone='040-98765432')
    db.session.add(h2)
    db.session.flush()
    print(f"[SEED] Hospitals: {h1.name} (ID={h1.id}), {h2.name} (ID={h2.id})")

    # ── SUPER ADMIN (hospital 1) ────────────────────────────
    admin_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
    admin1 = User(email='admin@mediflow.com', password_hash=admin_pw,
                  role='admin', hospital_id=h1.id, is_superadmin=True)
    db.session.add(admin1)

    # ── ADMIN HOSPITAL 2 ────────────────────────────────────
    admin2 = User(email='admin@apollo.com', password_hash=admin_pw,
                  role='admin', hospital_id=h2.id)
    db.session.add(admin2)
    db.session.flush()
    print("[SEED] Admins created")

    # ── DOCTORS HOSPITAL 1 ──────────────────────────────────
    doctors_h1_data = [
        ('Dr. Mehta',   'Cardiology',    'mehta@mediflow.com',   14),
        ('Dr. Rajan',   'General OPD',   'rajan@mediflow.com',   10),
        ('Dr. Rao',     'Orthopaedics',  'rao@mediflow.com',     12),
        ('Dr. Verma',   'Neurology',     'verma@mediflow.com',   15),
        ('Dr. Kapoor',  'Dermatology',   'kapoor@mediflow.com',  10),
        ('Dr. Pillai',  'Paediatrics',   'pillai@mediflow.com',  12),
        ('Dr. Sheikh',  'ENT',           'sheikh@mediflow.com',   8),
    ]
    doc_pw = bcrypt.generate_password_hash('doctor123').decode('utf-8')
    doctors_h1 = []
    for name, dept, email, consult in doctors_h1_data:
        u = User(email=email, password_hash=doc_pw, role='doctor', hospital_id=h1.id)
        db.session.add(u); db.session.flush()
        d = Doctor(user_id=u.id, hospital_id=h1.id, name=name,
                   department=dept, specialization=dept, avg_consult_minutes=consult)
        db.session.add(d); db.session.flush()
        doctors_h1.append(d)
        print(f"[SEED]   Doctor H1: {email} / doctor123 -> {name} ({dept})")

    # ── DOCTORS HOSPITAL 2 ──────────────────────────────────
    doctors_h2_data = [
        ('Dr. Sharma',  'Cardiology',    'sharma@apollo.com',    12),
        ('Dr. Nair',    'General OPD',   'nair@apollo.com',      10),
        ('Dr. Gupta',   'Gynaecology',   'gupta@apollo.com',     15),
        ('Dr. Reddy',   'Neurology',     'reddy@apollo.com',     12),
    ]
    doctors_h2 = []
    for name, dept, email, consult in doctors_h2_data:
        u = User(email=email, password_hash=doc_pw, role='doctor', hospital_id=h2.id)
        db.session.add(u); db.session.flush()
        d = Doctor(user_id=u.id, hospital_id=h2.id, name=name,
                   department=dept, specialization=dept, avg_consult_minutes=consult)
        db.session.add(d); db.session.flush()
        doctors_h2.append(d)

    print(f"[SEED] {len(doctors_h2)} doctors created for H2")

    # ── PATIENTS HOSPITAL 1 ─────────────────────────────────
    pat_pw = bcrypt.generate_password_hash('patient123').decode('utf-8')
    patients_h1_data = [
        ('Arjun Shah',     54, '9800001111', 'Heart history',       'arjun@mail.com'),
        ('Priya Iyer',     41, '9800002222', 'Post angioplasty',    'priya@mail.com'),
        ('Ravi Kumar',     33, '9800003333', 'Fever 3 days',        'ravi@mail.com'),
        ('Sunita Rao',     62, '9800004444', 'Knee follow-up',      'sunita@mail.com'),
        ('Deepak Nair',    47, '9800005555', 'Migraine',            'deepak@mail.com'),
        ('Meena Pillai',   29, '9800006666', 'Routine checkup',     'meena@mail.com'),
        ('Anil Desai',     70, '9800007777', 'Chest discomfort',    'anil@mail.com'),
        ('Farhan Qureshi', 38, '9800008888', 'Back pain',           'farhan@mail.com'),
        ('Lakshmi Sharma', 55, '9800009999', 'Diabetes follow-up',  'lakshmi@mail.com'),
        ('Mohan Das',      44, '9800010000', 'Shoulder injury',     'mohan@mail.com'),
        ('Geeta Singh',     8, '9800011111', 'Ear infection',       'geeta@mail.com'),
        ('Ramesh Babu',    78, '9800012222', 'BP check',            'ramesh@mail.com'),
    ]
    patients_h1 = []
    for name, age, phone, notes, email in patients_h1_data:
        u = User(email=email, password_hash=pat_pw, role='patient', hospital_id=h1.id)
        db.session.add(u); db.session.flush()
        p = Patient(user_id=u.id, hospital_id=h1.id, name=name, age=age, phone=phone, notes=notes)
        db.session.add(p); db.session.flush()
        patients_h1.append(p)
    print(f"[SEED] {len(patients_h1)} patients created for H1 (password: patient123)")

    # ── PATIENTS HOSPITAL 2 ─────────────────────────────────
    patients_h2_data = [
        ('Kavita Reddy', 35, '9900001111', 'Cardiac checkup', 'kavita@mail.com'),
        ('Suresh Menon', 50, '9900002222', 'Neurology consult', 'suresh@mail.com'),
    ]
    patients_h2 = []
    for name, age, phone, notes, email in patients_h2_data:
        u = User(email=email, password_hash=pat_pw, role='patient', hospital_id=h2.id)
        db.session.add(u); db.session.flush()
        p = Patient(user_id=u.id, hospital_id=h2.id, name=name, age=age, phone=phone, notes=notes)
        db.session.add(p); db.session.flush()
        patients_h2.append(p)

    # ── QUEUE ENTRIES HOSPITAL 1 ────────────────────────────
    queue_data = [
        (0, 0, 'critical', 'Chest pain, shortness of breath'),
        (1, 0, 'urgent',   'Post-surgery follow-up, elevated BP'),
        (2, 1, 'normal',   'Fever, sore throat'),
        (3, 2, 'normal',   'Knee pain, difficulty walking'),
        (4, 3, 'urgent',   'Severe headache, vision issues'),
        (5, 1, 'normal',   'Routine annual checkup'),
        (6, 0, 'normal',   'Mild chest discomfort'),
        (10, 6, 'urgent',  'Child ear pain, 2 days'),   # Geeta (age 8) - child boost
        (11, 0, 'urgent',  'Elderly hypertension'),      # Ramesh (age 78) - elderly boost
    ]
    for p_idx, d_idx, priority, symptoms in queue_data:
        patient = patients_h1[p_idx]
        doctor  = doctors_h1[d_idx]
        score   = compute_priority_score(priority, patient.age, wait_minutes=0)
        dept    = doctor.department
        count   = QueueEntry.query.filter_by(hospital_id=h1.id, department=dept).count()
        token   = generate_token(dept, count + 1)
        entry   = QueueEntry(
            token=token, patient_id=patient.id, doctor_id=doctor.id,
            hospital_id=h1.id, department=dept,
            priority_label=priority, priority_score=score,
            symptoms=symptoms, status='waiting',
            est_wait_minutes=max(1, count * doctor.avg_consult_minutes),
        )
        db.session.add(entry); db.session.flush()
        add_to_heap(h1.id, entry.id, score)
    print(f"[SEED] Queue entries created for H1")

    # ── APPOINTMENTS HOSPITAL 1 ─────────────────────────────
    today = date.today()
    appt_data = [
        (0, 0, '09:00', 'in-person'),
        (1, 0, '09:30', 'in-person'),
        (2, 1, '10:00', 'in-person'),
        (3, 2, '10:30', 'in-person'),
        (4, 3, '11:00', 'in-person'),
        (5, 1, '11:30', 'telemedicine'),
        (6, 0, '14:00', 'telemedicine'),
        (7, 4, '09:00', 'in-person'),   # Farhan -> Dermatology
        (8, 5, '10:00', 'in-person'),   # Lakshmi -> Paediatrics
    ]
    for p_idx, d_idx, time_slot, appt_type in appt_data:
        if p_idx >= len(patients_h1) or d_idx >= len(doctors_h1):
            continue
        a = Appointment(
            patient_id=patients_h1[p_idx].id,
            doctor_id=doctors_h1[d_idx].id,
            hospital_id=h1.id,
            department=doctors_h1[d_idx].department,
            date=today, time_slot=time_slot,
            type=appt_type, status='scheduled',
        )
        db.session.add(a)
    print(f"[SEED] Appointments created for H1")

    # ── ACTIVITY LOGS ───────────────────────────────────────
    logs = [
        (h1.id, 'system', 'MediFlow 2.0 initialized. Multi-hospital mode active.'),
        (h1.id, 'system', f'{len(queue_data)} patients loaded into priority queue.'),
        (h1.id, 'system', 'Background queue rebalancer started.'),
        (h2.id, 'system', 'Apollo Specialty Hospital initialized.'),
    ]
    for hid, action, details in logs:
        db.session.add(ActivityLog(hospital_id=hid, action=action, details=details))

    db.session.commit()
    print("\n[SEED] Database seeded successfully!")
    print("\n=== LOGIN CREDENTIALS ===")
    print("Admin H1:   admin@mediflow.com  / admin123")
    print("Admin H2:   admin@apollo.com    / admin123")
    print("Doctor H1:  mehta@mediflow.com  / doctor123")
    print("Doctor H1:  rajan@mediflow.com  / doctor123")
    print("Patient H1: arjun@mail.com      / patient123")
    print("Patient H1: geeta@mail.com      / patient123  (child - priority boost)")
    print("=========================")
