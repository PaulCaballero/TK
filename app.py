from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine, text 
from datetime import datetime
import io
import ibm_db
import csv
from flask import Response
from sqlalchemy.exc import SQLAlchemyError
from database_operations import DatabaseOperations

app = Flask(__name__)
app.secret_key = '!m@Tim3Keep3r' 

db_ops = DatabaseOperations()

@app.route('/')
def home():
    if 'user_id' in session:
        # user_name = get_user_name(session['user_id'])
        return redirect(url_for('add_time_entry'))
    else:
        return redirect(url_for('login'))
    
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
    company = request.form.get('company')
    try:
        row = db_ops.get_user_credentials(username, password, company)

        # Fetch the first row
        print(row)
        if row:
            # Store user ID in session for authentication
            # user_id = row[0]
            # sk_emp = row[1]
            session['user_id'] = row[0]
            session['sk_emp'] = row[1]
            print("Invoke AddTimeEntry module")
            return redirect(url_for('add_time_entry'))  # Redirect to add_time_entry on successful login
            
        else:
            return render_template('login.html', error_message='Invalid credentials')

    except SQLAlchemyError as e:
        return render_template('login.html', error_message=f"Database error: {str(e)}")

# ADDING TIME ENTRY
@app.route('/add_time_entry', methods=['GET', 'POST'])
def add_time_entry():
    user_id = session.get('user_id')
    sk_emp = session.get('sk_emp')
    message = None  

    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    if request.method == 'POST':
        try:
            if 'time_in' in request.form:
                # Process time-in logic
                existing_entry=db_ops.get_time_in(user_id)
                if existing_entry:
                    message = 'Time-in entry already recorded for today'
                else: 
                    db_ops.insert_time_in(sk_emp)
                    message = 'Time-in recorded successfully'
                    
            elif 'time_out' in request.form:
                # Process time-out logic
                existing_entry=db_ops.get_time_out(user_id)
                if existing_entry:
                    db_ops.insert_time_out(existing_entry[0])
                    message = 'Time-out recorded successfully'
                else:
                    message = 'No time-in entry found for today to clock out.'
                    
            
        except SQLAlchemyError as e:
            message = f"Database error: {str(e)}"
    # This part will execute for both GET and POST requests
    time_entries = db_ops.select_time_entries(user_id)
    processed_entries = process_time_entries(time_entries)
    print(processed_entries)
    

    # Use a dictionary to pass all variables to the template at once
    return render_template('index.html', time_entries=processed_entries, message=message, user_id=user_id)

def process_time_entries(time_entries):
    # Process time entries to extract date, time-in, time-out, and calculate total_hours
    processed_entries = []
    for entry in time_entries:
        clockin_datetime, clockout_datetime, total_hours, status = entry  # Unpack the tuple
        print(status)
        total_hours = calculate_total_hours(clockin_datetime, clockout_datetime)

        date = format_datetime(clockin_datetime, '%Y-%m-%d')
        time_in = format_datetime(clockin_datetime, '%H:%M:%S')
        time_out = format_datetime(clockout_datetime, '%H:%M:%S')

        processed_entries.append((date, time_in, time_out, total_hours, status))
    return processed_entries

def calculate_total_hours(clockin, clockout):
    # Calculate total_hours only if both clock-in and clock-out are datetime objects
    if isinstance(clockin, datetime) and isinstance(clockout, datetime):
        total_seconds = (clockout - clockin).total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"
    return 'N/A'

def format_datetime(dt, format_string):
    # Format datetime object to string if it's not None, otherwise return 'N/A'
    return dt.strftime(format_string) if isinstance(dt, datetime) else 'N/A'


@app.route('/download')
def download_time_entries():
    time_entries = [...]  # Fetch your time entries here
    si = io.StringIO()  # Creates an in-memory file-like string buffer
    cw = csv.writer(si)
    cw.writerow(['Date', 'Time-In', 'Time-Out', 'Total Hours'])  # CSV Header

    for entry in time_entries:
        cw.writerow([entry[0], entry[1], entry[2], entry[3] or 'N/A'])  # Write each row

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=time_entries.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
