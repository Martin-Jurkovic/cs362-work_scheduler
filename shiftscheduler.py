#!/usr/bin/env python3


from ortools.sat.python import cp_model

def generate_shift_schedule(num_employees, num_shifts, num_days, solution_limit=5):
    """
    Generates shift schedules based on the provided parameters.

    Args:
        num_employees (int): Number of employees.
        num_shifts (int): Number of shifts per day.
        num_days (int): Number of days to schedule.
        solution_limit (int): Maximum number of solutions to return.

    Returns:
        List[Dict]: A list of solutions, each solution is a dictionary with day numbers as keys and lists of (employee, shift) tuples as values.
    """
    all_employees = range(num_employees)
    all_shifts = range(num_shifts)
    all_days = range(num_days)

    model = cp_model.CpModel()

    # Create shift variables.
    shifts = {}
    for n in all_employees:
        for d in all_days:
            for s in all_shifts:
                shifts[(n, d, s)] = model.NewBoolVar(f'shift_n{n}_d{d}_s{s}')

    # Each shift is assigned to exactly one employee per day.
    for d in all_days:
        for s in all_shifts:
            model.AddExactlyOne(shifts[(n, d, s)] for n in all_employees)

    # Fair distribution of shifts among employees.
    min_shifts_per_employee = (num_shifts * num_days) // num_employees
    max_shifts_per_employee = min_shifts_per_employee + (1 if (num_shifts * num_days) % num_employees > 0 else 0)

    for n in all_employees:
        num_shifts_worked = sum(shifts[(n, d, s)] for d in all_days for s in all_shifts)
        model.Add(min_shifts_per_employee <= num_shifts_worked)
        model.Add(num_shifts_worked <= max_shifts_per_employee)

    # Solver setup.
    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 0
    solver.parameters.enumerate_all_solutions = True

    # Solution collector.
    class SolutionPrinter(cp_model.CpSolverSolutionCallback):
        def __init__(self, shifts, num_employees, num_days, num_shifts, limit):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self._shifts = shifts
            self._num_employees = num_employees
            self._num_days = num_days
            self._num_shifts = num_shifts
            self._solution_count = 0
            self._solution_limit = limit
            self.solutions = []

        def on_solution_callback(self):
            self._solution_count += 1
            solution = {}
            for d in range(self._num_days):
                day_assignments = []
                for n in range(self._num_employees):
                    for s in range(self._num_shifts):
                        if self.Value(self._shifts[(n, d, s)]):
                            day_assignments.append((n, s))
                solution[d] = day_assignments
            self.solutions.append(solution)
            if self._solution_count >= self._solution_limit:
                self.StopSearch()

        def solution_count(self):
            return self._solution_count

    solution_printer = SolutionPrinter(shifts, num_employees, num_days, num_shifts, solution_limit)
    solver.Solve(model, solution_printer)

    # Return the collected solutions.
    return solution_printer.solutions
