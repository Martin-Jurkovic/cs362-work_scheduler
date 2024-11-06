from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import datetime
from ortools.sat.python import cp_model
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import click
from flask.cli import with_appcontext

from classes.user import User, db
from classes.schedule import Schedule
from core.decorators import login_required, admin_required
from core.utils import generate_shifts, get_week_dates, datetimeformat  # Import generate_shifts function
app = Flask(__name__)
app.secret_key = 'your_secure_random_secret_key'  # Replace with a secure, randomly generated secret key

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scheduler.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the database
db.init_app(app)


app.jinja_env.filters['datetimeformat'] = datetimeformat

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
            if request.form['action'] == 'generate':
                shifts_per_day = int(request.form.get('shifts_per_day', 1))
                max_shifts = int(request.form.get('max_shifts', 5))
                success = generate_shifts(shifts_per_day=shifts_per_day, max_shifts_per_employee=max_shifts)
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

@app.route('/update_shift', methods=['POST'])
@admin_required
def update_shift():
    username = request.form.get('username')
    date = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    # Update the schedule
    schedule = Schedule.query.filter_by(
        username=username,
        date=date
    ).first()

    if schedule:
        schedule.start_time = start_time
        schedule.end_time = end_time
        db.session.commit()
        flash('Shift updated successfully', 'success')
    else:
        flash('Shift not found', 'error')

    return redirect(url_for('view_schedules'))


if __name__ == '__main__':
    app.run(debug=True)
