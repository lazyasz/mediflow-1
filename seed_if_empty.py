import os
# Prevent background threads from starting during initialization
os.environ['SEED_MODE'] = '1'

from app import create_app
from models.user import User
from models import db

def main():
    print("[INIT] Checking if database needs to be seeded...")
    app = create_app('production')
    
    with app.app_context():
        # First, ensure tables exist
        db.create_all()
        
        try:
            user = User.query.first()
            if not user:
                print("[INIT] Database is completely empty. Seeding now...")
                # CRITICAL: Release the DB session transaction lock so Postgres allows dropping tables!
                db.session.remove()
                db.engine.dispose()
                # We can safely import seed because SEED_MODE is 1 and no other threads exist
                import seed
                print("[INIT] Seeding completed successfully.")
            else:
                print("[INIT] Database already contains data. Skipping seed.")
        except Exception as e:
            print(f"[INIT] Exception occurred while checking users, attempting seed anyway: {e}")
            import seed

if __name__ == '__main__':
    main()
