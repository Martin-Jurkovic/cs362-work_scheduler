from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import datetime
from ortools.sat.python import cp_model
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import click
from flask.cli import with_appcontext

app = Flask(__name__)
app.secret_key = 'your_secure_random_secret_key'  # Replace with a secure, randomly generated secret key

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db = SQLAlchemy(app)

# User model
class User(db.Model):
    __tablename__ = 'users'
    username = db.Column(db.String(80), primary_key=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(80))
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    sick_hours = db.Column(db.Float, default=0)
    pto_hours = db.Column(db.Float, default=0)
    hourly_rate = db.Column(db.Float)
    job_assignment = db.Column(db.String(80))
    hire_date = db.Column(db.String(20))
    role = db.Column(db.String(20), default='employee')
    schedules = db.relationship('Schedule', backref='user', lazy=True)

    # Password methods
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Schedule model
class Schedule(db.Model):
    __tablename__ = 'schedules'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), db.ForeignKey('users.username'), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)

# Decorator to protect routes that require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to ensure the user is an admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = User.query.filter_by(username=session.get('username')).first()
        if not user or user.role != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to get the dates for the upcoming week (Monday to Sunday)
def get_week_dates():
    today = datetime.date.today()
    # Find the next Monday
    days_until_monday = (7 - today.weekday()) % 7
    start_day = today + datetime.timedelta(days=days_until_monday)
    # Get the week dates from Monday to Sunday
    week_dates = [start_day + datetime.timedelta(days=i) for i in range(7)]
    return week_dates

# Custom filter to format time in 12-hour format
def datetimeformat(value):
    try:
        # Assuming value is in 'HH:MM' format
        time_obj = datetime.datetime.strptime(value, '%H:%M')
        return time_obj.strftime('%I:%M %p')
    except Exception:
        return value

app.jinja_env.filters['datetimeformat'] = datetimeformat

# Function to generate shifts using OR-Tools
def generate_shifts():
    week_dates = get_week_dates()
    employees = User.query.filter(User.role != 'admin').all()
    num_employees = len(employees)
    if num_employees == 0:
        return False  # No employees to schedule
    num_days = len(week_dates)
    max_shifts_per_employee = 5  # No more than 5 days per week
    shifts_per_day = 1  # Assuming one shift per day

    # Create the model
    model = cp_model.CpModel()

    # Variables: shifts[e][d] is True if employee 'e' works on day 'd'
    shifts = {}
    for e in range(num_employees):
        for d in range(num_days):
            shifts[(e, d)] = model.NewBoolVar(f'shift_e{e}_d{d}')

    # Constraints:

    # Each employee works at most one shift per day (inherent with binary variables)

    # Each employee works at most 5 days in the week
    for e in range(num_employees):
        model.Add(sum(shifts[(e, d)] for d in range(num_days)) <= max_shifts_per_employee)

    # Distribute shifts evenly among employees
    min_shifts_per_employee = (num_days * shifts_per_day) // num_employees
    for e in range(num_employees):
        num_shifts_worked = sum(shifts[(e, d)] for d in range(num_days))
        model.Add(num_shifts_worked >= min_shifts_per_employee)

    # Ensure that each day has the required number of employees
    for d in range(num_days):
        model.Add(sum(shifts[(e, d)] for e in range(num_employees)) == shifts_per_day)

    # Solve the model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    # Store the schedule
    if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
        # Clear existing schedules for the week
        Schedule.query.filter(Schedule.date.in_([d.strftime('%Y-%m-%d') for d in week_dates])).delete()
        for e in range(num_employees):
            for d in range(num_days):
                if solver.Value(shifts[(e, d)]) == 1:
                    day = week_dates[d]
                    shift_start = datetime.datetime.combine(day, datetime.time(hour=8))
                    shift_end = shift_start + datetime.timedelta(hours=8)
                    schedule_entry = Schedule(
                        username=employees[e].username,
                        date=day.strftime('%Y-%m-%d'),
                        start_time=shift_start.strftime('%H:%M'),
                        end_time=shift_end.strftime('%H:%M')
                    )
                    db.session.add(schedule_entry)
        db.session.commit()
        return True
    else:
        print("No feasible schedule found.")
        return False

# Route to redirect root URL to login
@app.route('/')
def index():
    return redirect(url_for('login'))

# Route to handle login (both GET and POST methods)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Query the user from the database
        user = User.query.filter_by(username=username).first()

        # Check if user exists and password is correct
        if user and user.check_password(password):
            session['username'] = username  # Store username in session
            return redirect(url_for('home'))
        else:
            # If credentials are incorrect, return an error
            error = "Invalid username or password"
            return render_template('login.html', error=error)
    else:
        return render_template('login.html', error=None)

# Route for the home page
@app.route('/home')
@login_required
def home():
    username = session['username']
    user = User.query.filter_by(username=username).first()
    role = user.role
    return render_template('home.html', username=username, role=role)

# Route for the profile page
@app.route('/profile')
@login_required
def profile():
    username = session['username']
    user = User.query.filter_by(username=username).first()
    role = user.role
    return render_template('profile.html', user=user, role=role)

# Route for editing profile
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    username = session['username']
    user = User.query.filter_by(username=username).first()

    if request.method == 'POST':
        # Update user data with form data
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.email = request.form['email']
        user.phone = request.form['phone']
        user.address = request.form['address']
        db.session.commit()
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', user=user, role=user.role)

# Route for resetting password
@app.route('/reset_password', methods=['GET', 'POST'])
@login_required
def reset_password():
    username = session['username']
    user = User.query.filter_by(username=username).first()
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Validate current password
        if not user.check_password(current_password):
            error = "Current password is incorrect."
            return render_template('reset_password.html', error=error)
        # Validate new passwords match
        if new_password != confirm_password:
            error = "New passwords do not match."
            return render_template('reset_password.html', error=error)

        # Update password
        user.set_password(new_password)
        db.session.commit()
        message = "Password reset successful."
        return render_template('reset_password.html', message=message)
    return render_template('reset_password.html')

# Route to view and generate schedules
@app.route('/view_schedules', methods=['GET', 'POST'])
@login_required
def view_schedules():
    username = session['username']
    user = User.query.filter_by(username=username).first()
    role = user.role
    week_dates = get_week_dates()
    current_week = f"{week_dates[0].strftime('%B %d, %Y')} - {week_dates[-1].strftime('%B %d, %Y')}"

    if role == 'admin':
        if request.method == 'POST':
            employees = User.query.filter(User.role != 'admin').all()
            if not employees:
                flash('Cannot generate schedules because there are no employees.', 'error')
                return redirect(url_for('view_schedules'))
            success = generate_shifts()
            if success:
                flash('Schedules generated successfully.', 'success')
                return redirect(url_for('view_schedules'))
            else:
                flash('No feasible schedule found.', 'error')
                return redirect(url_for('view_schedules'))
        else:
            # Display the current schedules
            employees = User.query.filter(User.role != 'admin').all()
            schedules = {}
            for employee in employees:
                employee_schedule = Schedule.query.filter_by(username=employee.username).filter(
                    Schedule.date.in_([d.strftime('%Y-%m-%d') for d in week_dates])).all()
                # Build a date-to-shift mapping
                date_to_shift = {s.date: s for s in employee_schedule}
                schedules[employee.username] = date_to_shift
            return render_template('admin_view_schedules.html', schedules=schedules, week_dates=week_dates,
                                   users=employees, role=role, current_week=current_week)
    else:
        # For regular users, display their own schedules
        user_schedule = Schedule.query.filter_by(username=username).filter(
            Schedule.date.in_([d.strftime('%Y-%m-%d') for d in week_dates])).all()
        # Build a date-to-shift mapping for the user
        date_to_shift = {s.date: s for s in user_schedule}
        return render_template('view_schedules.html', username=username, role=role, week_dates=week_dates,
                               user_schedule=date_to_shift, current_week=current_week)

# Route to handle logout
@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Route to manage employees (Admin only)
@app.route('/manage_employees')
@admin_required
def manage_employees():
    employees = User.query.filter(User.role != 'admin').all()
    return render_template('manage_employees.html', employees=employees, role='admin')

# Route to add a new employee (Admin only)
@app.route('/add_employee', methods=['GET', 'POST'])
@admin_required
def add_employee():
    if request.method == 'POST':
        # Get form data
        username = request.form['username']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        address = request.form['address']
        hire_date = request.form['hire_date']
        job_assignment = request.form['job_assignment']
        hourly_rate = request.form['hourly_rate']
        sick_hours = request.form.get('sick_hours', 0)
        pto_hours = request.form.get('pto_hours', 0)
        role = 'employee'  # Default role

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different username.', 'error')
            return redirect(url_for('add_employee'))

        # Create new user
        new_user = User(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            address=address,
            hire_date=hire_date,
            job_assignment=job_assignment,
            hourly_rate=hourly_rate,
            sick_hours=sick_hours,
            pto_hours=pto_hours,
            role=role
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Employee added successfully.', 'success')
        return redirect(url_for('manage_employees'))
    return render_template('add_employee.html', role='admin')

# Route to edit an existing employee (Admin only)
@app.route('/edit_employee/<username>', methods=['GET', 'POST'])
@admin_required
def edit_employee(username):
    user = User.query.filter_by(username=username).first()
    if not user or user.role == 'admin':
        flash('Employee not found.', 'error')
        return redirect(url_for('manage_employees'))

    if request.method == 'POST':
        # Update user data
        user.first_name = request.form['first_name']
        user.last_name = request.form['last_name']
        user.email = request.form['email']
        user.phone = request.form['phone']
        user.address = request.form['address']
        user.hire_date = request.form['hire_date']
        user.job_assignment = request.form['job_assignment']
        user.hourly_rate = request.form['hourly_rate']
        user.sick_hours = request.form.get('sick_hours', 0)
        user.pto_hours = request.form.get('pto_hours', 0)
        password = request.form.get('password')
        if password:
            user.set_password(password)
        db.session.commit()
        flash('Employee updated successfully.', 'success')
        return redirect(url_for('manage_employees'))

    return render_template('edit_employee.html', user=user, role='admin')

# Route to delete an employee (Admin only)
@app.route('/delete_employee/<username>', methods=['POST'])
@admin_required
def delete_employee(username):
    user = User.query.filter_by(username=username).first()
    if not user or user.role == 'admin':
        flash('Employee not found.', 'error')
        return redirect(url_for('manage_employees'))

    # Delete user's schedules
    Schedule.query.filter_by(username=username).delete()
    db.session.delete(user)
    db.session.commit()
    flash('Employee deleted successfully.', 'success')
    return redirect(url_for('manage_employees'))

# Custom command to initialize the database and create the admin user
@app.cli.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database and create the admin user."""
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
        click.echo("Initialized the database and created the admin user.")
    else:
        click.echo("Admin user already exists.")

if __name__ == '__main__':
    app.run(debug=True)
