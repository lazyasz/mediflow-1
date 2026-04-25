# ============================================================
# utils/helpers.py — Shared Utility Functions
# ============================================================

from datetime import datetime, timezone


def generate_token(department, sequence_number):
    """
    Generate a queue token from department name and sequence.
    Format: {PREFIX}-{NUMBER}  e.g. C-047, G-033, E-001
    """
    prefix_map = {
        'Cardiology': 'C',
        'General OPD': 'G',
        'Orthopaedics': 'O',
        'Neurology': 'N',
        'Dermatology': 'D',
        'Paediatrics': 'P',
        'ENT': 'E',
        'Ophthalmology': 'OP',
        'Gynaecology': 'GY',
        'Psychiatry': 'PS',
    }
    prefix = prefix_map.get(department, department[0].upper() if department else 'X')
    return f"{prefix}-{str(sequence_number).zfill(3)}"


def format_time_ago(dt):
    """Format a datetime as a human-readable 'time ago' string."""
    if not dt:
        return 'unknown'
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return 'just now'
    elif seconds < 3600:
        mins = seconds // 60
        return f'{mins}m ago'
    elif seconds < 86400:
        hours = seconds // 3600
        return f'{hours}h ago'
    else:
        days = seconds // 86400
        return f'{days}d ago'


def get_slot_times(start_hour=9, end_hour=17, duration_minutes=30):
    """Generate time slot strings for a working day."""
    slots = []
    hour = start_hour
    minute = 0
    while hour < end_hour:
        slots.append(f"{str(hour).zfill(2)}:{str(minute).zfill(2)}")
        minute += duration_minutes
        if minute >= 60:
            hour += minute // 60
            minute = minute % 60
    return slots
