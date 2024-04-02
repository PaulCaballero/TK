from flask import Flask, render_template, request, redirect, url_for, session, Response, g
from datetime import datetime, date, timedelta
import io
import ibm_db
import csv
from sqlalchemy.exc import SQLAlchemyError
from database_operations import DatabaseOperations

app = Flask(__name__)
app.secret_key = '!m@Tim3Keep3r' 
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=6)


@app.before_request
def before_request():
    """Ensure database connection is available throughout the request if user is logged in."""
    if 'company' in session:
        g.db_ops = DatabaseOperations()
    else:
        g.db_ops = None

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
    if 'company' in session:
        g.db_ops.close()
    session.clear()
    return redirect(url_for('login'))

@app.route('/authenticate', methods=['POST'])
def authenticate():
    username = request.form.get('username')
    password = request.form.get('password')
    company = request.form.get('company')
    
    g.db_ops = DatabaseOperations(company)
    try:
        row = g.db_ops.get_user_credentials(username, password, company)
        session['company'] = company
        
        # Fetch the first row
        if row:
            # Store user ID in session for authentication
            session['user_id'] = row[0]
            session['sk_emp'] = row[1]
            session['pos'] = row[2]
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
    pos = session.get('pos')
    company = session.get('company')
    message = None  
    page = request.args.get('page', 1, type=int)
    per_page = 10
    g.db_ops = DatabaseOperations(company)
    total_entries = g.db_ops.count_time_entries(user_id)

    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if not authenticated
    
    if request.method == 'POST':
        try:
            if 'time_in' in request.form:
                # Process time-in logic
                existing_entry=g.db_ops.get_time_in(user_id)
                if existing_entry:
                    message = 'Time-in entry already recorded for today'
                else: 
                    g.db_ops.insert_time_in(sk_emp)
                    message = 'Time-in recorded successfully'
                    
            elif 'time_out' in request.form:
                # Process time-out logic
                existing_entry=g.db_ops.get_time_out(user_id)
                if existing_entry:
                    g.db_ops.insert_time_out(existing_entry[0])
                    message = 'Time-out recorded successfully'
                else:
                    message = 'No time-in entry found for today to clock out / Time-in entry already recorded for today.'
                    
        except SQLAlchemyError as e:
            message = f"Database error: {str(e)}"

    # This part will execute for both GET and POST requests
    time_entries = g.db_ops.select_time_entries(user_id, page, per_page)
    processed_entries = process_time_entries(time_entries)
   
    # Use a dictionary to pass all variables to the template at once
    return render_template('index.html', time_entries=processed_entries, message=message, user_id=user_id, pos=pos, total_pages=(total_entries // per_page + (total_entries % per_page > 0)),
                           current_page=page)

@app.route('/download_csv')
def download_csv():
    user_id = session.get('user_id')
    company = session.get('company')
    g.db_ops = DatabaseOperations(company)
    if not user_id:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    # Retrieve start and end dates from query parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    # Convert start and end dates from string to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d') if start_date else None
    end_date = datetime.strptime(end_date, '%Y-%m-%d') if end_date else None

    # Modify this function to filter based on the provided dates
    time_entries = g.db_ops.select_time_entries_for_csv(user_id, start_date, end_date)
    headers = ['Employee Name', 'Date', 'Time-In', 'Time-Out', 'Total Hours(hh:mm)', 'OT(hh:mm)'] # Define the CSV headers

    # Create a generator for CSV data
    def generate_csv():
        yield ','.join(headers) + '\n'  # First yield the headers
        for entry in time_entries:
            # Format Time-In and Time-Out
            total_hrs = calculate_total_hours(entry[2], entry[3])
            ot = calculate_total_hours(entry[7], entry[3])
            formatted_entry = [
                entry[0],
                format_date(entry[1]),  # Date
                format_datetime(entry[2], '%H:%M:%S'),  # Time-In
                format_datetime(entry[3], '%H:%M:%S'),  # Time-Out
                total_hrs,  # Total Hours
                ot   # OT_UT
            ]
            yield ','.join(formatted_entry) + '\n'

    # Create a response with the CSV data
    return Response(
        generate_csv(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=time_entries.csv'}
    )

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))  # Redirect to login if not authenticated

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']


        if new_password != confirm_password:
            return render_template('reset_password.html', error="New passwords do not match.")

        company = session.get('company')
        g.db_ops = DatabaseOperations(company)
        if not g.db_ops.verify_current_password(session['user_id'], current_password):
            print(current_password)
            return render_template('reset_password.html', error="Current password is incorrect.")
        
        # If the current password is correct and new passwords match
        # Update the password in the database
        g.db_ops.update_user_password(session['user_id'], new_password)
        return render_template('reset_password.html', message="Password successfully updated.")

    return render_template('reset_password.html')

def process_time_entries(time_entries):
    # Process time entries to extract date, time-in, time-out, and calculate total_hours
    processed_entries = []
    for entry in time_entries:
        date, clockin_datetime, clockout_datetime, total_hours, status, ot_ut = entry  # Unpack the tuple
        total_hours = calculate_total_hours(clockin_datetime, clockout_datetime)
        # date = format_datetime(date, '%Y-%m-%d')
        time_in = format_datetime(clockin_datetime, '%H:%M:%S')
        time_out = format_datetime(clockout_datetime, '%H:%M:%S')
        processed_entries.append((date, time_in, time_out, total_hours, status, ot_ut))
    return processed_entries

def calculate_total_hours(clockin, clockout):
    # Calculate total_hours only if both clock-in and clock-out are datetime objects
    if isinstance(clockin, datetime) and isinstance(clockout, datetime):
        total_seconds = (clockout - clockin).total_seconds()
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"
    return '--:--'

def format_datetime(dt, format_string):
    # Format datetime object to string if it's not None, otherwise return 'N/A'
    return dt.strftime(format_string) if isinstance(dt, datetime) else '--:--'

def format_date(d):
    """Format date object to string if it's not None, otherwise return 'N/A'."""
    return d.strftime('%Y-%m-%d') if isinstance(d, date) else 'N/A'


if __name__ == '__main__':
    app.run(debug=True)
