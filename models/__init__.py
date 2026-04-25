# ============================================================
# models/__init__.py — SQLAlchemy DB instance + model imports
# ============================================================

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import all models so they register with SQLAlchemy
from models.hospital import Hospital
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.queue_entry import QueueEntry
from models.appointment import Appointment
from models.activity_log import ActivityLog
