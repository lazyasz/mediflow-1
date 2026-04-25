# ============================================================
# services/priority_engine.py — heapq-Based Priority Scoring
# ============================================================
#
# Priority Score Formula:
#   score = (severity × W1) + (wait_time_factor × W2) + (age_factor × W3)
#
# Higher score = higher priority.
# heapq is a min-heap, so we negate scores for max-priority ordering.
# ============================================================

import heapq
import math
from datetime import datetime, timezone

# --- Weights (tunable) ---
W_SEVERITY = 4.0
W_WAIT     = 2.5
W_AGE      = 1.5

# --- Severity mapping ---
SEVERITY_SCORES = {
    'critical': 10.0,
    'urgent':   7.0,
    'normal':   3.0,
}

# --- In-memory priority heap per hospital ---
# Structure: { hospital_id: [ (-score, sequence, queue_entry_id), ... ] }
_heaps = {}
_sequence = 0  # Global tie-breaker (FIFO for same priority)


def _get_heap(hospital_id):
    """Get or create the heap for a hospital."""
    if hospital_id not in _heaps:
        _heaps[hospital_id] = []
    return _heaps[hospital_id]


def compute_priority_score(severity_label, age, wait_minutes=0):
    """
    Compute composite priority score.

    Args:
        severity_label: 'critical', 'urgent', or 'normal'
        age: patient age in years
        wait_minutes: how long the patient has been waiting

    Returns:
        float priority score (higher = more urgent)
    """
    # Severity component
    severity = SEVERITY_SCORES.get(severity_label, 3.0)
    severity_component = severity * W_SEVERITY

    # Age factor: boost for children (<12) and elderly (>65)
    if age < 12:
        age_factor = 1.0 + max(0, (12 - age) / 12 * 0.5)
    elif age > 65:
        age_factor = 1.0 + max(0, (age - 65) / 35 * 0.5)
    else:
        age_factor = 1.0
    age_component = age_factor * W_AGE

    # Wait time escalation: logarithmic increase
    wait_factor = math.log(1 + wait_minutes / 10.0)
    wait_component = wait_factor * W_WAIT

    return severity_component + age_component + wait_component


def add_to_heap(hospital_id, queue_entry_id, priority_score):
    """
    Add a queue entry to the priority heap.
    Uses negated score since heapq is a min-heap.
    """
    global _sequence
    _sequence += 1
    heap = _get_heap(hospital_id)
    heapq.heappush(heap, (-priority_score, _sequence, queue_entry_id))


def pop_highest_priority(hospital_id, valid_ids=None):
    """
    Pop the highest-priority entry from the heap.

    Args:
        hospital_id: which hospital's heap
        valid_ids: set of currently valid (waiting) queue_entry_ids.
                   Entries not in this set are discarded (lazy deletion).

    Returns:
        queue_entry_id or None
    """
    heap = _get_heap(hospital_id)
    while heap:
        neg_score, seq, entry_id = heapq.heappop(heap)
        if valid_ids is None or entry_id in valid_ids:
            return entry_id
    return None


def pop_for_doctor(hospital_id, doctor_id, waiting_entries):
    """
    Pop the highest-priority entry for a specific doctor.

    Args:
        hospital_id: which hospital
        doctor_id: which doctor to filter for
        waiting_entries: dict of {queue_entry_id: doctor_id} for all waiting entries

    Returns:
        queue_entry_id or None
    """
    heap = _get_heap(hospital_id)
    skipped = []
    result = None

    while heap:
        item = heapq.heappop(heap)
        neg_score, seq, entry_id = item

        if entry_id not in waiting_entries:
            # Entry no longer waiting, discard (lazy deletion)
            continue

        if waiting_entries[entry_id] == doctor_id:
            result = entry_id
            break
        else:
            skipped.append(item)

    # Push back skipped items
    for item in skipped:
        heapq.heappush(heap, item)

    return result


def rebuild_heap(hospital_id, entries):
    """
    Rebuild the entire heap for a hospital from fresh data.
    Called during periodic rebalancing.

    Args:
        entries: list of (queue_entry_id, priority_score) tuples
    """
    global _sequence
    heap = []
    for entry_id, score in entries:
        _sequence += 1
        heap.append((-score, _sequence, entry_id))
    heapq.heapify(heap)
    _heaps[hospital_id] = heap


def clear_heap(hospital_id):
    """Clear the heap for a hospital."""
    _heaps[hospital_id] = []


def get_heap_size(hospital_id):
    """Get the number of entries in a hospital's heap."""
    return len(_get_heap(hospital_id))
