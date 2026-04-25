# MediFlow 2.0 — Hospital Queue Management System

> **Intelligent, Priority-Based Hospital Queue Management for Multi-Tenant SaaS Environments**

---

## Software Requirements Specification (SRS)

---

## 5.1 Introduction

### 5.1.1 Purpose

This document specifies the software requirements for **MediFlow 2.0**, a web-based Hospital Queue Management System designed to digitize and intelligently manage patient flow in hospitals. It serves as a reference for developers, system architects, and stakeholders involved in the development, deployment, and maintenance of the system.

### 5.1.2 Background

Traditional hospital queuing systems rely on manual token distribution, paper registers, and first-come-first-serve logic — leading to long wait times, mismanaged critical cases, and poor patient experience. MediFlow 2.0 replaces this with an intelligent, priority-driven, real-time queue system accessible via any web browser.

### 5.1.3 Definitions & Acronyms

| Term | Definition |
|------|-----------|
| **OPD** | Outpatient Department |
| **JWT** | JSON Web Token — used for secure session authentication |
| **SRS** | Software Requirements Specification |
| **heapq** | Python's heap queue algorithm (min-heap) |
| **SaaS** | Software as a Service |
| **SocketIO** | Real-time bidirectional event-based communication |
| **ORM** | Object Relational Mapper (SQLAlchemy) |
| **API** | Application Programming Interface |
| **REST** | Representational State Transfer |
| **CRUD** | Create, Read, Update, Delete |
| **Walk-in** | A patient who arrives without a prior appointment |
| **Token** | A unique queue identifier assigned to each patient on check-in |

---

## 5.2 Project Scope

### 5.2.1 What MediFlow 2.0 Does

MediFlow 2.0 is a full-stack web application that manages two parallel patient flows simultaneously:

1. **Walk-in Queue (Token-Based)** — patients arrive, check in, and receive a token. The system assigns them a priority position based on severity, age, and wait time — not just arrival time.

2. **Specialist Appointment System** — patients book time-slotted appointments with specialist doctors up to 30 days in advance. Booked appointments can be merged into the live walk-in queue on the day of visit.

### 5.2.2 Multi-Hospital SaaS Architecture

The system is designed for deployment as a **multi-tenant SaaS platform** where multiple hospitals operate on the same codebase with complete data isolation. Each hospital's data is segregated by `hospital_id` at every database query level.

### 5.2.3 In Scope

- Smart priority queue engine (heapq-based) with dynamic reordering
- Role-based dashboards for Patients, Doctors, and Admins
- Real-time queue updates via WebSockets (Flask-SocketIO)
- Specialist appointment booking with conflict detection
- Admin management of hospitals, doctors, and departments
- Activity logging and audit trail with CSV export
- Public kiosk/TV queue display screen
- Background auto-rebalancing of priority scores every 60 seconds
- Mobile-responsive UI

### 5.2.4 Out of Scope (Current Version)

- Native mobile applications (iOS/Android)
- Payment gateway integration
- Electronic Health Record (EHR) integration
- AI/ML-based symptom severity prediction
- SMS/Email notification system
- Video telemedicine infrastructure

---

## 5.3 User Requirements

MediFlow 2.0 serves three distinct user roles:

### 5.3.1 Patient

- Register an account with name, age, phone, and hospital selection
- Log in and view personal dashboard
- Check in as a walk-in patient by selecting department, doctor, and describing symptoms
- Receive a unique token (e.g. `C-007`) with estimated wait time
- View live queue position and status in real time
- Receive a prominent on-screen alert when their token is called
- Book specialist appointments up to 30 days in advance
- Choose available time slots and appointment type (in-person / telemedicine)
- View and manage existing appointments

### 5.3.2 Doctor

- Log in and view personal dashboard showing only their assigned patients
- See patients sorted by priority (Critical → Urgent → Normal)
- Call the next highest-priority patient with one click
- Mark a patient as completed after consultation
- Perform emergency override — escalate any patient to Critical priority instantly
- Transfer a patient to another available doctor
- View today's scheduled appointments and merge them into the live queue
- Monitor live activity feed in real time

### 5.3.3 Administrator

- Log in and view a hospital-wide dashboard with all stats
- See queue snapshot across all doctors and departments
- Call the next patient for any doctor from the admin panel
- View department-wise patient load with visual bar charts
- View doctor efficiency metrics (completed today, currently waiting)
- Trigger immediate priority queue rebalancing manually
- Access and filter complete activity/audit logs
- Export logs to CSV for reporting
- Manage hospital settings (name, address, phone)
- Add, edit, and deactivate doctors (creates login accounts automatically)
- Monitor peak hour analytics (last 7 days)
- Open the public kiosk queue display for waiting area TVs

---

## 5.4 Functional Requirements

### FR-01: User Authentication
- The system shall support user registration and login via email and password
- Passwords shall be hashed using bcrypt before storage
- Sessions shall be managed using JWT stored in HTTP-only cookies
- JWT tokens shall expire after 8 hours
- The system shall redirect unauthenticated users to the login page
- Role-based access control shall restrict pages and APIs based on role (patient / doctor / admin)

### FR-02: Smart Priority Queue
- The system shall assign a numeric priority score to each patient using the formula:
  ```
  Score = (Severity × 4.0) + (WaitTime_minutes × 2.5) + (AgeFactor × 1.5)
  ```
  Where:
  - Severity: Critical=10, Urgent=6, Normal=2
  - AgeFactor: age < 12 or age > 65 → +5 boost (elderly/child priority)
  - WaitTime: minutes elapsed since check-in
- The system shall use a min-heap (Python `heapq`) for O(log n) queue operations
- Patients with equal priority scores shall be ordered by check-in time (FIFO fallback)
- The system shall automatically rebalance all priority scores every 60 seconds in a background thread to reflect increasing wait times

### FR-03: Token Generation
- The system shall generate a unique token per patient per visit
- Token format: `{DEPT_PREFIX}-{SEQUENCE}` (e.g. `C-007`, `G-031`, `N-004`)
- Tokens shall reset per department per day

### FR-04: Walk-in Check-in
- Patients shall select department, doctor (optional), priority level, and symptoms
- If no doctor is selected, the system shall auto-assign the available doctor in the department with the shortest current queue
- The system shall calculate estimated wait time based on patients ahead and average consultation duration
- Check-in shall emit a real-time `queue_updated` WebSocket event to all connected clients

### FR-05: Appointment Booking
- Patients shall book appointments by selecting department, doctor, date, and time slot
- The system shall generate available slots based on doctor working hours (09:00–17:00, 30-minute intervals)
- The system shall detect and prevent double-booking conflicts
- Appointments shall be bookable up to 30 days in advance

### FR-06: Appointment-to-Queue Merge
- Doctors and admins shall be able to merge a today's scheduled appointment into the live priority queue
- Merged appointments shall receive an `urgent` priority level by default
- The original appointment status shall be updated to `merged`

### FR-07: Emergency Override
- Doctors and admins shall be able to escalate any patient token to `critical` priority
- The override reason shall be logged in the activity log
- The queue shall be immediately reordered to reflect the escalation

### FR-08: Patient Transfer
- Doctors shall be able to transfer a waiting patient to another available doctor
- The transfer shall be logged in the activity log
- The transferred patient shall retain their current priority score

### FR-09: Real-time Updates
- The system shall use WebSocket rooms named `hospital_{id}` to broadcast updates only within the correct hospital tenant
- Events emitted: `queue_updated`, `new_activity`, `patient_called`
- Clients shall fall back to 15-second polling if WebSocket is unavailable

### FR-10: Activity Logging
- Every significant system action shall be logged: login, register, check-in, token generated, patient called, completed, transfer, override, appointment booked/cancelled
- Logs shall be filterable by action type and paginated
- Admins shall be able to export all logs as a CSV file

### FR-11: Analytics
- The system shall provide peak hour charts (patient counts by hour, last 7 days)
- The system shall provide doctor efficiency metrics (patients completed today, currently waiting)
- The system shall display department-wise load as percentage progress bars

### FR-12: Admin Management
- Admins shall be able to update hospital profile (name, address, phone)
- Admins shall be able to add new doctors (automatically creates a login user account)
- Admins shall be able to edit doctor details (name, department, specialization, consultation duration)
- Admins shall be able to toggle doctor availability on/off
- Admins shall be able to soft-deactivate doctors (preserves historical data)

### FR-13: Kiosk Display
- The system shall provide a public queue display page accessible without login
- The display shall show all currently waiting patients with token, name, department, doctor, and priority
- The display shall update automatically via WebSocket + 10-second polling fallback
- The display shall show a live clock

---

## 5.5 Non-Functional Requirements

### NFR-01: Performance
- API response time shall be under 300ms for all queue and stats endpoints under normal load
- The priority heap operations shall complete in O(log n) time
- The system shall handle at least 500 concurrent WebSocket connections per hospital
- Database queries shall use indexed columns (`hospital_id`, `status`, `doctor_id`)

### NFR-02: Reliability
- The background rebalancer thread shall be fault-tolerant — errors shall be caught and logged, and the thread shall continue running
- The heap shall be reconstructable from the database at any time via `rebalance_queue()`
- The system shall not lose committed patient data on server restart

### NFR-03: Scalability
- The multi-tenant architecture shall support unlimited hospitals on a single deployment
- Switching from SQLite to PostgreSQL/MySQL requires only a single connection string change
- The application factory pattern (`create_app()`) supports horizontal scaling behind a load balancer

### NFR-04: Usability
- The UI shall load and be interactive within 2 seconds on a standard broadband connection
- All dashboards shall auto-refresh without requiring a manual page reload
- The patient dashboard shall display a full-screen alert when their token is called
- The interface shall be mobile-responsive with a slide-in sidebar on small screens

### NFR-05: Maintainability
- Code shall be modular — separated into `models/`, `routes/`, `services/`, `sockets/`, `utils/`, `templates/`
- All business logic shall live in `services/` — routes shall only handle HTTP concerns
- Database models shall define `to_dict()` for consistent API serialization

### NFR-06: Availability
- The system is designed for 24/7 operation as a daemon process
- The background rebalancer is a daemon thread and will terminate cleanly with the main process

---

## 5.6 Hardware Requirements

### Minimum (Development / Small Hospital)

| Component | Minimum Spec |
|-----------|-------------|
| CPU | Dual-core 2.0 GHz |
| RAM | 4 GB |
| Storage | 20 GB HDD |
| Network | 10 Mbps broadband |
| OS | Windows 10 / Ubuntu 20.04 / macOS 12+ |

### Recommended (Production / Multi-Hospital)

| Component | Recommended Spec |
|-----------|-----------------|
| CPU | Quad-core 2.5 GHz+ |
| RAM | 8–16 GB |
| Storage | 100 GB SSD |
| Network | 100 Mbps dedicated |
| OS | Ubuntu 22.04 LTS (server) |

### Client (End User Devices)
- Any device with a modern web browser (Chrome 90+, Firefox 88+, Edge 90+, Safari 14+)
- Minimum screen resolution: 768×1024
- For kiosk display: any HDMI-connected TV/monitor with browser

---

## 5.7 Software Requirements

### Server-Side

| Software | Version | Purpose |
|---------|---------|---------|
| Python | 3.11+ | Runtime |
| Flask | 3.1+ | Web framework |
| Flask-SocketIO | 5.6+ | Real-time WebSocket server |
| Flask-SQLAlchemy | 3.1+ | ORM / database abstraction |
| Flask-JWT-Extended | 4.7+ | JWT authentication |
| Flask-Bcrypt | 1.0+ | Password hashing |
| Flask-CORS | 6.0+ | Cross-origin resource sharing |
| SQLite | 3.x | Default development database |
| MySQL / PostgreSQL | 8.0+ / 14+ | Production database (optional) |
| PyMySQL | 1.1+ | MySQL driver (if using MySQL) |

### Client-Side (loaded via CDN)

| Software | Version | Purpose |
|---------|---------|---------|
| Socket.IO Client | 4.7.4 | WebSocket communication |
| Google Fonts | — | Typography (Syne, DM Sans, DM Mono) |

### Development Tools

| Tool | Purpose |
|------|---------|
| VS Code | Code editor |
| SQLite Viewer (VS Code ext.) | Database inspection |
| Postman / Thunder Client | API testing |
| Git | Version control |

---

## 5.8 System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                          │
│  Patient Browser  │  Doctor Browser  │  Admin Browser        │
│         └──────────────────────────────────┘                 │
│                    Kiosk Display (TV)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │  HTTP / WebSocket
┌───────────────────────────▼─────────────────────────────────┐
│                      FLASK APPLICATION                        │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │   Routes    │  │   Services   │  │   SocketIO Events  │  │
│  │ auth        │  │ queue_svc    │  │ join_hospital       │  │
│  │ dashboard   │  │ appt_svc     │  │ queue_updated       │  │
│  │ queue       │  │ activity_svc │  │ new_activity        │  │
│  │ appointment │  │ priority_eng │  │ patient_called      │  │
│  │ admin       │  │              │  │                    │  │
│  │ management  │  └──────────────┘  └────────────────────┘  │
│  │ activity    │         │                                   │
│  └─────────────┘         │                                   │
│         │                │                                   │
│  ┌──────▼────────────────▼───────────────────────────────┐  │
│  │                Priority Engine (heapq)                  │  │
│  │  compute_priority_score() │ add_to_heap()               │  │
│  │  pop_for_doctor()         │ rebuild_heap()              │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │          Background Rebalancer Thread (60s)            │  │
│  │  Recalculates all scores → emits queue_updated         │  │
│  └───────────────────────────────────────────────────────┘  │
└───────────────────────────┬─────────────────────────────────┘
                            │  SQLAlchemy ORM
┌───────────────────────────▼─────────────────────────────────┐
│                       DATABASE LAYER                          │
│                                                               │
│  hospitals │ users │ patients │ doctors │ queue_entries       │
│  appointments │ activity_logs                                 │
│                                                               │
│  [ SQLite (dev) ]  or  [ MySQL / PostgreSQL (prod) ]         │
└─────────────────────────────────────────────────────────────┘
```

### Module Structure

```
mediflow/
├── app.py                  ← Application factory + entry point
├── config.py               ← Environment-based configuration
├── seed.py                 ← Database seeder (dev/demo data)
├── models/
│   ├── hospital.py         ← Multi-tenant root model
│   ├── user.py             ← Authentication entity
│   ├── patient.py          ← Patient profile
│   ├── doctor.py           ← Doctor profile
│   ├── queue_entry.py      ← Queue token + priority data
│   ├── appointment.py      ← Specialist appointment
│   └── activity_log.py     ← Audit trail
├── routes/
│   ├── auth.py             ← Login, register, logout
│   ├── dashboard.py        ← HTML page routes
│   ├── queue_routes.py     ← Queue API (checkin, call-next, etc.)
│   ├── appointment_routes.py
│   ├── admin_routes.py     ← Stats and analytics API
│   ├── management_routes.py← Hospital/doctor CRUD API
│   └── activity_routes.py  ← Logs + CSV export API
├── services/
│   ├── priority_engine.py  ← heapq + scoring formula
│   ├── queue_service.py    ← Queue business logic
│   ├── appointment_service.py
│   └── activity_service.py
├── sockets/
│   └── events.py           ← WebSocket event handlers
├── utils/
│   ├── helpers.py          ← Token generation, time formatting
│   └── decorators.py       ← JWT role decorators
├── templates/
│   ├── base.html           ← Shared layout (sidebar, topbar)
│   ├── index.html          ← Landing page
│   ├── auth/               ← Login, Register pages
│   ├── patient/            ← Patient dashboard, appointments
│   ├── doctor/             ← Doctor dashboard
│   ├── admin/              ← Admin dashboard, logs, manage
│   └── shared/             ← Kiosk queue display
└── static/
    ├── css/style.css       ← Complete design system
    └── js/
        ├── app.js          ← Global utilities (api(), toast(), etc.)
        └── socket.js       ← SocketIO client
```

### Priority Queue Data Flow

```
Patient Check-in
      │
      ▼
compute_priority_score(severity, age, wait_minutes)
      │   Score = (Severity×4.0) + (Wait×2.5) + (AgeFactor×1.5)
      ▼
QueueEntry saved to DB  +  add_to_heap(hospital_id, entry_id, score)
      │
      ▼
Doctor clicks "Call Next"
      │
      ▼
pop_for_doctor(hospital_id, doctor_id) ← O(log n) heap pop
      │
      ▼
QueueEntry.status = 'called' → DB commit
      │
      ▼
SocketIO emits 'queue_updated' + 'patient_called' to hospital room
      │
      ▼
All connected browsers refresh queue in real-time
```

---

## 5.9 Assumptions and Constraints

### Assumptions
- Each hospital has at least one admin user who manages the system
- Doctors are pre-registered by the hospital admin (patients cannot create doctor accounts)
- A patient belongs to exactly one hospital (determined at registration)
- Working hours are 09:00–17:00 with 30-minute appointment slots
- Average consultation time is 12 minutes (configurable per doctor)
- The server has a stable internet connection for WebSocket support
- All end users have access to a web browser on a device connected to the hospital's network or internet

### Constraints
- **SQLite limitation**: SQLite supports only one concurrent write operation — for high-traffic production use, MySQL or PostgreSQL is required
- **In-memory heap**: The heapq priority heap is per-process in-memory — horizontal scaling across multiple server processes requires a shared cache (Redis) which is not implemented in the current version
- **No offline mode**: The system requires a live server connection — it does not support offline operation
- **Session duration**: JWT tokens expire after 8 hours — long sessions require re-login
- **Booking window**: Appointments can only be booked up to 30 days in advance (configurable in `config.py`)
- **Browser requirement**: The UI uses modern CSS features (CSS variables, Grid, Flexbox) — Internet Explorer is not supported

---

## 5.10 Security Requirements

### SR-01: Authentication
- All passwords stored as bcrypt hashes (cost factor 12) — plaintext passwords never stored
- JWT tokens stored in HTTP-only cookies — not accessible via JavaScript (`XSS` protection)
- `JWT_COOKIE_SECURE = True` in production — cookies only sent over HTTPS

### SR-02: Authorization
- Every API endpoint decorated with `@role_required('patient'|'doctor'|'admin')`
- Multi-tenant isolation: all database queries include `hospital_id` filter — cross-hospital data access is architecturally impossible
- Admin-only endpoints (management, analytics, logs) return 403 if accessed by patient/doctor roles

### SR-03: Data Isolation
- Hospital data is scoped by `hospital_id` foreign key on every model
- No global queries exist — all service functions require `hospital_id` as a parameter

### SR-04: Input Validation
- All API inputs parsed via `request.json` with explicit field extraction — no raw dict passing to DB
- SQL injection impossible — SQLAlchemy ORM uses parameterized queries exclusively

### SR-05: Production Hardening
- `DEBUG = False` in `ProductionConfig` — disables the interactive debugger and detailed error pages
- `JWT_COOKIE_CSRF_PROTECT = True` in production
- `SECRET_KEY` and `JWT_SECRET_KEY` must be set via environment variables (minimum 32 random characters)
- `.env` file must never be committed to version control (add to `.gitignore`)

### SR-06: Audit Trail
- Every authentication event, queue operation, and administrative action is logged to `activity_logs` with timestamp, user, and IP address
- Logs are immutable — no delete endpoint exists for activity logs

---

## 5.11 Summary

MediFlow 2.0 is a production-ready, multi-tenant Hospital Queue Management System that replaces manual, first-come-first-serve queuing with an intelligent, priority-driven digital system.

### Key Highlights

| Feature | Implementation |
|---------|---------------|
| Priority Algorithm | heapq min-heap + weighted scoring (severity, age, wait time) |
| Real-time Updates | Flask-SocketIO with WebSocket rooms per hospital |
| Authentication | Flask-JWT-Extended with HTTP-only cookie storage |
| Multi-tenancy | hospital_id scoping on all models and queries |
| Database | SQLAlchemy ORM — SQLite (dev), MySQL/PostgreSQL (prod) |
| Background Jobs | Python daemon thread for 60s queue rebalancing |
| UI | Vanilla CSS design system, dark theme, mobile responsive |

### Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@mediflow.com | admin123 |
| Doctor | mehta@mediflow.com | doctor123 |
| Patient | arjun@mail.com | patient123 |

### Quick Start

```powershell
cd c:\Users\dhruv\Downloads\medikflow\mediflow

# First time setup
py -3.13 seed.py

# Run the server
py -3.13 app.py

# Open in browser
# http://localhost:5000
```

---

*MediFlow 2.0 — Built with Python Flask, SQLAlchemy, Flask-SocketIO, and heapq*
*Designed for scalable, multi-hospital SaaS deployment*
