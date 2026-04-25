import os
from app import create_app, socketio

# Create the application instance for production
app = create_app('production')

with app.app_context():
    from models.user import User
    try:
        # If no users exist, automatically run the seed script
        if not User.query.first():
            print("[WSGI] Database is empty. Running seed script automatically...")
            # Temporarily set SEED_MODE to prevent background rebalancer conflicts
            os.environ['SEED_MODE'] = '1'
            import seed
            print("[WSGI] Seed complete!")
    except Exception as e:
        print(f"[WSGI] Could not auto-seed database: {e}")

if __name__ == "__main__":
    socketio.run(app)
