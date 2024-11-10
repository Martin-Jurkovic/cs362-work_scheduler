import datetime
from ortools.sat.python import cp_model
from classes.user import User, db
from classes.schedule import Schedule

# Function to get the dates for the upcoming week (Monday to Sunday)
def get_week_dates():
    today = datetime.date.today()
    # Find the next Monday
    days_until_monday = (7 - today.weekday()) % 7
    start_day = today + datetime.timedelta(days_until_monday)
    # Get the week dates from Monday to Sunday
    week_dates = [start_day + datetime.timedelta(days=i) for i in range(7)]
    return week_dates

# Function to generate shifts using OR-Tools
def generate_shifts(day_requirements, max_shifts_per_employee=5, active_employees=None):
    """
    Generate shifts for active employees
    
    Args:
        day_requirements (dict): Shift requirements for each day
        max_shifts_per_employee (int): Maximum shifts per employee per week
        active_employees (list): List of usernames for active employees. If None, all non-admin employees are used.
    """
    week_dates = get_week_dates()
    
    # Filter employees based on active_employees parameter
    if active_employees is not None:
        employees = User.query.filter(
            User.role != 'admin',
            User.username.in_(active_employees)
        ).all()
    else:
        employees = User.query.filter(User.role != 'admin').all()
    
    num_employees = len(employees)
    if num_employees == 0:
        return False

    num_days = len(week_dates)
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

    # Define shift types and their times
    shift_types = {
        0: ("08:00", "13:00"),  # Opening
        1: ("12:00", "17:00"),  # Midday
        2: ("16:00", "22:00")   # Closing
    }

    # Create the model
    model = cp_model.CpModel()

    # Variables: shifts[e][d][s] is True if employee 'e' works on day 'd' shift type 's'
    shifts = {}
    for e in range(num_employees):
        for d in range(num_days):
            for s in range(3):
                shifts[(e, d, s)] = model.NewBoolVar(f'shift_e{e}_d{d}_s{s}')

    # Constraints:
    # 1. Required number of employees per shift type per day
    for d in range(num_days):
        day_name = days[d]
        day_req = day_requirements[day_name]
        
        # Opening shifts
        model.Add(sum(shifts[(e, d, 0)] for e in range(num_employees)) == day_req['opening'])
        # Midday shifts
        model.Add(sum(shifts[(e, d, 1)] for e in range(num_employees)) == day_req['midday'])
        # Closing shifts
        model.Add(sum(shifts[(e, d, 2)] for e in range(num_employees)) == day_req['closing'])

    # 2. Each employee can work at most one shift per day
    for e in range(num_employees):
        for d in range(num_days):
            model.Add(sum(shifts[(e, d, s)] for s in range(3)) <= 1)

    # 3. Each employee can work at most max_shifts_per_employee shifts per week
    for e in range(num_employees):
        model.Add(sum(shifts[(e, d, s)] 
                     for d in range(num_days) 
                     for s in range(3)) <= max_shifts_per_employee)

    # Solve the model
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # Clear existing schedules for the week
        Schedule.query.filter(Schedule.date.in_([d.strftime('%Y-%m-%d') for d in week_dates])).delete()

        # Create new schedules
        for d in range(num_days):
            for e in range(num_employees):
                for s in range(3):
                    if solver.Value(shifts[(e, d, s)]):
                        start_time, end_time = shift_types[s]
                        schedule = Schedule(
                            username=employees[e].username,
                            date=week_dates[d].strftime('%Y-%m-%d'),
                            start_time=start_time,
                            end_time=end_time
                        )
                        db.session.add(schedule)
        
        db.session.commit()
        return True
    return False

# Custom filter to format time in 12-hour format
def datetimeformat(value):
    try:
        # Assuming value is in 'HH:MM' format
        time_obj = datetime.datetime.strptime(value, '%H:%M')
        return time_obj.strftime('%I:%M %p')
    except Exception:
        return value