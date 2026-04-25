from app import create_app, socketio

# Create the application instance for production
app = create_app('production')

if __name__ == "__main__":
    socketio.run(app)
