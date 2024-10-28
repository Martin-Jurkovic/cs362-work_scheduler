# cs362-work_scheduler

Create a virtual environment: (Optional but Recommended)

- python3 -m venv venv
- source venv/bin/activate
- For Windows: venv\Scripts\activate

After install these packages below:

- python3 -m pip install Flask

- python3 -m pip install Flask-Login

- python3 -m pip install Flask-SQLAlchemy

- python3 -m pip install Werkzeug

- python3 -m pip install ortools

Initialize the Database in bash:
- flask init-db
- Creates the database file for the website
- Default admin user credentials
    - Username: admin
    - Password: password123
- It will create the database file in the instance folder, you would have to create your own set of employees to test out the entire program functionality. If you do not want to create a set of employees, drag the database file from the sample folder into the instance folder.

Run the code from app.py, then go to http://127.0.0.1:5000/ in your web browser
