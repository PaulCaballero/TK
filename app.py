from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine, text 
from datetime import datetime
import ibm_db
app = Flask(__name__)

# Configure DB2 Connection
conn_str = "db2://qqw84224:EbkZsMdg4x5dlfpC@9938aec0-8105-433e-8bf9-0fbb7e483086.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud:32459/bludb?SECURITY=ssl"
conn=create_engine(conn_str).connect()

# SQL statement using SQLAlchemy's text function
stmt = text("""
    CREATE TABLE IF NOT EXISTS time_tracking (
        id INTEGER NOT NULL PRIMARY KEY,
        user_id VARCHAR(50) NOT NULL,
        task_description VARCHAR(255) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT TIMESTAMP
    )
""")

# Execute the SQL statement
conn.execute(stmt)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/time_entry')
def time_entry():
    return render_template('time_entry.html')

@app.route('/track_time', methods=['POST'])
def track_time():
    id = request.form.get('id')
    user_id = request.form.get('user_id')
    task_description = request.form.get('task_description')

    stmt_insert = text("""
        INSERT INTO time_tracking (id, user_id, task_description) VALUES (:id, :user_id, :task_description)
    """).bindparams(id=id, user_id=user_id, task_description=task_description)


    conn.execute(stmt_insert)
    conn.close()

    return redirect(url_for('home'))

@app.route('/add_time_entry', methods=['POST'])
def add_time_entry():
    employee_id = request.form.get('employee_id')
    clockin_datetime_str = request.form.get('clockin_datetime')
    clockout_datetime_str = request.form.get('clockout_datetime')
    total_hrs = request.form.get('total_hrs')

    # Convert string to datetime objects
    clockin_datetime = datetime.strptime(clockin_datetime_str, '%Y-%m-%dT%H:%M')
    clockout_datetime = datetime.strptime(clockout_datetime_str, '%Y-%m-%dT%H:%M')


    stmt_insert = text("""
        INSERT INTO TimeEntries (employee_id, clockin_datetime, clockout_datetime, total_hrs) VALUES (:employee_id, :clockin_datetime, :clockout_datetime, :total_hrs)
    """).bindparams(employee_id=employee_id, clockin_datetime=clockin_datetime, clockout_datetime=clockout_datetime, total_hrs=total_hrs)
    conn=create_engine(conn_str).connect()
    conn.execute(stmt_insert)
    conn.close()

    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
