from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import datetime
from ortools.sat.python import cp_model

app = Flask(__name__)
app.secret_key = 'your_secure_random_secret_key'  # Replace with a secure, randomly generated secret key

# Mock user data with roles
users = {
    'admin': {
        'password': 'password123',
        'first_name': 'Admin',
        'last_name': 'User',
        'email': 'admin@example.com',
        'phone': '555-1234',
        'address': '123 Admin St',
        'sick_hours': 10,
        'pto_hours': 15,
        'hourly_rate': 50.00,
        'job_assignment': 'Administrator',
        'username': 'admin',
        'hire_date': '2020-01-15',
        'role': 'admin'  # Role field
    },
    'user1': {
        'password': 'pass1',
        'first_name': 'John',
        'last_name': 'Doe',
        'email': 'john@example.com',
        'phone': '555-5678',
        'address': '456 Main St',
        'sick_hours': 5,
        'pto_hours': 8,
        'hourly_rate': 30.00,
        'job_assignment': 'Engineer',
        'username': 'user1',
        'hire_date': '2021-05-20',
        'role': 'employee'  # Role field
    },
    'user2': {
        'password': 'pass2',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'email': 'jane@example.com',
        'phone': '555-6789',
        'address': '789 Side St',
        'sick_hours': 7,
        'pto_hours': 12,
        'hourly_rate': 32.00,
        'job_assignment': 'Technician',
        'username': 'user2',
        'hire_date': '2021-06-15',
        'role': 'employee'
    }
}

# Global variable to store schedules
schedules = {}

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
        if 'username' not in session or users[session['username']]['role'] != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to get employee usernames
def get_employee_usernames():
    return [username for username, data in users.items() if data['role'] != 'admin']

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
    employees = get_employee_usernames()
    num_employees = len(employees)
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
    global schedules
    if status == cp_model.FEASIBLE or status == cp_model.OPTIMAL:
        schedule = {}
        for e in range(num_employees):
            employee_shifts = []
            for d in range(num_days):
                if solver.Value(shifts[(e, d)]) == 1:
                    day = week_dates[d]
                    shift_start = datetime.datetime.combine(day, datetime.time(hour=8))
                    shift_end = shift_start + datetime.timedelta(hours=8)
                    employee_shifts.append({
                        'date': day.strftime('%Y-%m-%d'),
                        'start_time': shift_start.strftime('%H:%M'),
                        'end_time': shift_end.strftime('%H:%M')
                    })
            schedule[employees[e]] = employee_shifts
        schedules = schedule
    else:
        schedules = {}
        print("No feasible schedule found.")

# Route to serve the login page
@app.route('/')
def login():
    return render_template('login.html', error=None)

# Post route to handle login logic
@app.route('/login', methods=['POST'])
def login_post():
    username = request.form['username']
    password = request.form['password']

    # Check if username exists and password is correct
    if username in users and users[username]['password'] == password:
        session['username'] = username  # Store username in session
        return redirect(url_for('home'))
    else:
        # If credentials are incorrect, return an error
        return render_template('login.html', error="Invalid username or password")

# Route for the home page
@app.route('/home')
@login_required
def home():
    username = session['username']
    role = users[username]['role']
    return render_template('home.html', username=username, role=role)

# Route for the profile page
@app.route('/profile')
@login_required
def profile():
    username = session['username']
    user_data = users[username]
    role = user_data['role']
    return render_template('profile.html', user=user_data, role=role)

# Route for editing profile
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    username = session['username']
    user_data = users[username]

    if request.method == 'POST':
        # Update user data with form data
        user_data['first_name'] = request.form['first_name']
        user_data['last_name'] = request.form['last_name']
        user_data['email'] = request.form['email']
        user_data['phone'] = request.form['phone']
        user_data['address'] = request.form['address']
        return redirect(url_for('profile'))
    return render_template('edit_profile.html', user=user_data, role=user_data['role'])

# Route for resetting password
@app.route('/reset_password', methods=['GET', 'POST'])
@login_required
def reset_password():
    username = session['username']
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Validate current password
        if users[username]['password'] != current_password:
            error = "Current password is incorrect."
            return render_template('reset_password.html', error=error)
        # Validate new passwords match
        if new_password != confirm_password:
            error = "New passwords do not match."
            return render_template('reset_password.html', error=error)

        # Update password
        users[username]['password'] = new_password
        message = "Password reset successful."
        return render_template('reset_password.html', message=message)
    return render_template('reset_password.html')

# Route to generate schedules (Admin only)
@app.route('/generate_schedules', methods=['GET', 'POST'])
@admin_required
def generate_schedules():
    username = session['username']
    role = users[username]['role']
    if request.method == 'POST':
        generate_shifts()
        return redirect(url_for('view_generated_schedule'))
    return render_template('generate_schedules.html', role=role)

# Route to view the generated schedule (Admin only)
@app.route('/view_generated_schedule')
@admin_required
def view_generated_schedule():
    username = session['username']
    role = users[username]['role']
    week_dates = get_week_dates()
    current_week = f"{week_dates[0].strftime('%B %d, %Y')} - {week_dates[-1].strftime('%B %d, %Y')}"
    return render_template('view_generated_schedule.html', schedules=schedules, week_dates=week_dates, users=users, role=role, current_week=current_week)

# Route to edit the schedule (Admin only)
@app.route('/edit_schedule', methods=['GET', 'POST'])
@admin_required
def edit_schedule():
    username = session['username']
    role = users[username]['role']
    week_dates = get_week_dates()
    current_week = f"{week_dates[0].strftime('%B %d, %Y')} - {week_dates[-1].strftime('%B %d, %Y')}"

    if request.method == 'POST':
        # Process form data to update shifts
        for employee_username in schedules.keys():
            for day in week_dates:
                date_str = day.strftime('%Y-%m-%d')
                start_time = request.form.get(f'{employee_username}_{date_str}_start')
                end_time = request.form.get(f'{employee_username}_{date_str}_end')
                if start_time and end_time:
                    # Update or add shift
                    # Find if shift exists
                    shift_exists = False
                    for shift in schedules[employee_username]:
                        if shift['date'] == date_str:
                            shift['start_time'] = start_time
                            shift['end_time'] = end_time
                            shift_exists = True
                            break
                    if not shift_exists:
                        schedules[employee_username].append({
                            'date': date_str,
                            'start_time': start_time,
                            'end_time': end_time
                        })
                else:
                    # Remove shift if exists
                    schedules[employee_username] = [shift for shift in schedules[employee_username] if shift['date'] != date_str]
        return redirect(url_for('view_generated_schedule'))
    else:
        return render_template('edit_schedule.html', schedules=schedules, week_dates=week_dates, users=users, role=role, current_week=current_week)

# Route for the view schedules page
@app.route('/view_schedules')
@login_required
def view_schedules():
    username = session['username']
    role = users[username]['role']
    week_dates = get_week_dates()
    current_week = f"{week_dates[0].strftime('%B %d, %Y')} - {week_dates[-1].strftime('%B %d, %Y')}"
    if role == 'admin':
        # For admin, show the generated schedule
        return redirect(url_for('view_generated_schedule'))
    else:
        # For employees, show their own schedule
        user_schedule = schedules.get(username, [])
        return render_template('view_schedules.html', username=username, role=role, week_dates=week_dates, user_schedule=user_schedule, current_week=current_week)

# Route to handle logout
@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
