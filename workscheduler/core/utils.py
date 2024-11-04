import datetime
from ortools.sat.python import cp_model
from classes.user import User, db
from classes.schedule import Schedule

# Function to get the dates for the upcoming week (Monday to Sunday)
def get_week_dates():
    today = datetime.date.today()
    # Find the next Monday
    days_until_monday = (7 - today.weekday()) % 7
    start_day = today + datetime.timedelta(days=days_until_monday)
    # Get the week dates from Monday to Sunday
    week_dates = [start_day + datetime.timedelta(days=i) for i in range(7)]
    return week_dates


# Function to generate shifts using OR-Tools
def generate_shifts(shifts_per_day=1, max_shifts_per_employee=5):
    week_dates = get_week_dates()
    employees = User.query.filter(User.role != 'admin').all()
    num_employees = len(employees)
    if num_employees == 0:
        return False  # No employees to schedule
    num_days = len(week_dates)
    # max_shifts_per_employee = 5  # No more than 5 days per week
    # shifts_per_day = 1  # Assuming one shift per day

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

# Custom filter to format time in 12-hour format
def datetimeformat(value):
    try:
        # Assuming value is in 'HH:MM' format
        time_obj = datetime.datetime.strptime(value, '%H:%M')
        return time_obj.strftime('%I:%M %p')
    except Exception:
        return value