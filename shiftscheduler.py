#!/usr/bin/env python3

from ortools.sat.python import cp_model

num_employees = 6
num_shifts = 2
num_days = 5
all_employees = range(num_employees)
all_shifts = range(num_shifts)
all_days = range(num_days)

model = cp_model.CpModel()

shifts = {}
for n in all_employees:
    for d in all_days:
        for s in all_shifts:
            shifts[(n, d, s)] = model.NewBoolVar(f"shift_n{n}_d{d}_s{s}")

for d in all_days:
    for s in all_shifts:
        model.AddExactlyOne(shifts[(n, d, s)] for n in all_employees)

min_shifts_per_employee = (num_shifts * num_days) // num_employees
if num_shifts * num_days % num_employees == 0:
    max_shifts_per_employee = min_shifts_per_employee
else:
    max_shifts_per_employee = min_shifts_per_employee + 1

for n in all_employees:
    shifts_worked = []
    for d in all_days:
        for s in all_shifts:
            shifts_worked.append(shifts[(n, d, s)])
    model.Add(min_shifts_per_employee <= sum(shifts_worked))
    model.Add(sum(shifts_worked) <= max_shifts_per_employee)

solver = cp_model.CpSolver()
solver.parameters.linearization_level = 0
solver.parameters.enumerate_all_solutions = True

class EmployeesPartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print intermediate solutions."""

    def __init__(self, shifts, num_employees, num_days, num_shifts, limit):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._shifts = shifts
        self._num_employees = num_employees
        self._num_days = num_days
        self._num_shifts = num_shifts
        self._solution_count = 0
        self._solution_limit = limit

    def on_solution_callback(self):
        self._solution_count += 1
        print(f"Solution {self._solution_count}")
        for d in range(self._num_days):
            print(f"Day {d}")
            for n in range(self._num_employees):
                is_working = False
                for s in range(self._num_shifts):
                    if self.Value(self._shifts[(n, d, s)]):
                        is_working = True
                        print(f"  Employee {n} works shift {s}")
                if not is_working:
                    print(f"  Employee {n} does not work")
        if self._solution_count >= self._solution_limit:
            print(f"Stop search after {self._solution_limit} solutions")
            self.StopSearch()

    def solutionCount(self):
        return self._solution_count

solution_limit = 5
solution_printer = EmployeesPartialSolutionPrinter(
    shifts, num_employees, num_days, num_shifts, solution_limit
)

solver.Solve(model, solution_printer) 
