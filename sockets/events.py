# ============================================================
# sockets/events.py — SocketIO Event Handlers
# ============================================================

from flask_socketio import join_room, leave_room, emit


def register_socket_events(socketio):
    """Register all SocketIO event handlers."""

    @socketio.on('connect')
    def handle_connect():
        emit('connected', {'message': 'Connected to MediFlow'})

    @socketio.on('join_hospital')
    def handle_join_hospital(data):
        hospital_id = data.get('hospital_id')
        if hospital_id:
            room = f'hospital_{hospital_id}'
            join_room(room)
            emit('joined', {'room': room})

    @socketio.on('leave_hospital')
    def handle_leave_hospital(data):
        hospital_id = data.get('hospital_id')
        if hospital_id:
            room = f'hospital_{hospital_id}'
            leave_room(room)

    @socketio.on('disconnect')
    def handle_disconnect():
        pass
