from app import db, User
from app import app

with app.app_context():
    db.create_all()

    # Create the admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            phone='555-1234',
            address='123 Admin St',
            sick_hours=0,
            pto_hours=0,
            hourly_rate=0,
            job_assignment='Administrator',
            hire_date='2020-01-15',
            role='admin'
        )
        admin_user.set_password('password123')  # Set the admin password
        db.session.add(admin_user)
        db.session.commit()
