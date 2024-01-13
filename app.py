from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text 
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
app = Flask(__name__)
app.secret_key = '!m@Tim3Keep3r' 

# Configure DB2 Connection
conn_str = "db2://qqw84224:EbkZsMdg4x5dlfpC@9938aec0-8105-433e-8bf9-0fbb7e483086.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud:32459/bludb?SECURITY=ssl"
conn=create_engine(conn_str).connect()




@app.route('/')
def home():
    if 'user_id' in session:
        return f'Welcome, user: {session["user_id"]}! <a href="{url_for("logout")}">Logout</a>'
    else:
        return f'Welcome to Timekeeping App. <a href="{url_for("login")}">Login</a>'
    
@app.route('/login', methods=['GET', 'POST'])  # Allow both GET and POST methods
def login():
    if request.method == 'POST':
        return redirect(url_for('authenticate'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/time_entry')
def time_entry():
    return render_template('time_entry.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    username = request.form.get('username')
    password = request.form.get('password')

    try:
        stmt_select = text("""
            SELECT EMPLOYEE_ID FROM UserAccount
            WHERE USERNAME = :username AND PASSWORD = :password
        """).bindparams(username=username, password=password)

        result = conn.execute(stmt_select)

        # Fetch the first row
        row = result.fetchone()
        print(row)
        if row:
            # Store user ID in session for authentication
            user_id = row[0]
            session['user_id'] = user_id
            return redirect(url_for('add_time_entry'))  # Redirect to add_time_entry on successful login
            # return redirect(url_for('home'))
        else:
            return render_template('login.html', message='Invalid credentials')

    except SQLAlchemyError as e:
        return render_template('login.html', message=f"Database error: {str(e)}")



# ADDING TIME ENTRY
@app.route('/add_time_entry', methods=['GET', 'POST'])
def add_time_entry():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    try:
        # Check if there is an existing time entry for the user today
        stmt_check_entry = text("""
            SELECT ENTRY_ID FROM TimeEntries
            WHERE EMPLOYEE_ID = :user_id
            AND DATE(CLOCKIN_DATETIME) = CURRENT DATE
        """).bindparams(user_id=user_id)

        result_check_entry = conn.execute(stmt_check_entry)
        existing_entry = result_check_entry.fetchone()

        if existing_entry:
            return render_template('index.html', message='Time-in entry already recorded for today')

        # If no existing entry, create a new time entry (considered as time-in)
        stmt_insert_entry = text("""
            INSERT INTO TimeEntries (EMPLOYEE_ID, CLOCKIN_DATETIME)
            VALUES (:user_id, CURRENT TIMESTAMP)
        """).bindparams(user_id=user_id)

        conn.execute(stmt_insert_entry)

        return redirect(url_for('home'))

    except SQLAlchemyError as e:
        return render_template('index.html', message=f"Database error: {str(e)}")

@app.route('/track_time', methods=['GET', 'POST'])
def track_time():
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    try:
        # Fetch time entries for the logged-in employee
        stmt_select_entries = text("""
            SELECT CLOCKIN_DATETIME, CLOCKOUT_DATETIME, TOTAL_HRS
            FROM TimeEntries
            WHERE EMPLOYEE_ID = :user_id
            ORDER BY CLOCKIN_DATETIME DESC
        """).bindparams(user_id=user_id)

        result_entries = conn.execute(stmt_select_entries)
        time_entries = result_entries.fetchall()
        print(time_entries)
        return render_template('track_time.html', time_entries=time_entries)

    except SQLAlchemyError as e:
        return render_template('track_time.html', message=f"Database error: {str(e)}")


if __name__ == '__main__':
    app.run(debug=True)
