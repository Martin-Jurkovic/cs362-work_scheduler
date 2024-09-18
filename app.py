# app.py

from flask import Flask, request, redirect, url_for, session
from login import User, users, create_user, verify_login
from shiftscheduler import generate_shift_schedule

app = Flask(__name__)
app.secret_key = 'some_secret_key'  # Replace with a secure key in production

@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        return f"""
            <h1>Welcome, {username}!</h1>
            <a href='/schedule_shifts'>Schedule Shifts</a><br>
            <a href='/logout'>Logout</a>
        """
    return '''
        <h1>Welcome to the App</h1>
        <a href="/login">Login</a><br>
        <a href="/create_account">Create Account</a>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login_route():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = verify_login(username, password)
        if user:
            session['username'] = user.username
            return redirect(url_for('home'))
        else:
            return '''
                <h1>Invalid username or password.</h1>
                <a href="/login">Try again</a>
            '''
    else:
        return '''
            <h1>Login</h1>
            <form method="post">
                Username: <input type='text' name='username'><br>
                Password: <input type='password' name='password'><br>
                <input type='submit' value='Login'>
            </form>
            <a href='/'>Back to Home</a>
        '''

@app.route('/create_account', methods=['GET', 'POST'])
def create_account_route():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = create_user(username, password)
        if new_user:
            return f'''
                <h1>User '{username}' created successfully!</h1>
                <a href='/login'>Login now</a>
            '''
        else:
            return '''
                <h1>This username is already taken. Please choose a different username.</h1>
                <a href="/create_account">Try again</a>
            '''
    else:
        return '''
            <h1>Create Account</h1>
            <form method="post">
                Username: <input type='text' name='username'><br>
                Password: <input type='password' name='password'><br>
                <input type='submit' value='Create Account'>
            </form>
            <a href='/'>Back to Home</a>
        '''

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/schedule_shifts', methods=['GET', 'POST'])
def schedule_shifts():
    if 'username' not in session:
        return redirect(url_for('login_route'))

    if request.method == 'POST':
        # Get parameters from the form.
        try:
            num_employees = int(request.form['num_employees'])
            num_shifts = int(request.form['num_shifts'])
            num_days = int(request.form['num_days'])
            solution_limit = int(request.form['solution_limit'])
        except ValueError:
            return '''
                <h1>Invalid input. Please enter integer values.</h1>
                <a href="/schedule_shifts">Try again</a>
            '''

        # Call the shift scheduler function.
        solutions = generate_shift_schedule(num_employees, num_shifts, num_days, solution_limit)

        # Prepare the results.
        output = '<h1>Shift Scheduling Results</h1>'
        if solutions:
            for idx, solution in enumerate(solutions):
                output += f'<h2>Solution {idx + 1}</h2>'
                for d in range(num_days):
                    output += f'<strong>Day {d + 1}:</strong><br>'
                    day_schedule = solution.get(d, [])
                    for n, s in day_schedule:
                        output += f'Employee {n} works shift {s}<br>'
                    output += '<br>'
        else:
            output += '<p>No solutions found.</p>'
        output += '<a href="/schedule_shifts">Back</a>'
        return output
    else:
        # Show the form to input scheduling parameters.
        return '''
            <h1>Shift Scheduler</h1>
            <form method="post">
                <label>Number of Employees:</label>
                <input type='number' name='num_employees' required><br>
                <label>Number of Shifts per Day:</label>
                <input type='number' name='num_shifts' required><br>
                <label>Number of Days:</label>
                <input type='number' name='num_days' required><br>
                <label>Solution Limit:</label>
                <input type='number' name='solution_limit' value='5' required><br><br>
                <input type='submit' value='Generate Schedule'>
            </form>
            <a href='/'>Back to Home</a>
        '''

if __name__ == '__main__':
    app.run(debug=True)
