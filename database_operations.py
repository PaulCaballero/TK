from sqlalchemy import create_engine, text 
from sqlalchemy.exc import SQLAlchemyError
import os
import bcrypt
class DatabaseOperations:
    def __init__(self, schema_name=None):
        
        # Configure DB2 Connection
        db_user = 'ab671732' #os.getenv('uid')
        db_password = 'pay73DCQkDz6LJ5i'  #os.getenv('pwd')
        db_host = 'd191fc8e-4bab-4e51-8880-e4720556396b.c8l9ggsd0kmvoig3l8kg.databases.appdomain.cloud' #os.getenv('hostname')
        db_port = '30223' #os.getenv('port', 'default_port')  # Default port if not specified
        db_name =  'bludb' #os.getenv('database')

        conn_str = f"db2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?SECURITY=ssl"
        self.schema_name = schema_name
        self.conn = create_engine(conn_str).connect()

    def verify_current_password(self, username, current_password):
        try:
            stmt_reset_template = """
                SELECT PASSWORD FROM {schema}.USERACCOUNT UA
                WHERE USERNAME = :username
            """
            stmt_reset = text(stmt_reset_template.format(schema=self.schema_name)).bindparams(username=username)
            
            result = self.conn.execute(stmt_reset).fetchone()

            if result is not None:
                stored_password = result[0]  
                return stored_password == current_password
            else:
                return False
        except SQLAlchemyError as e:
            print(f"SQLAlchemy Error: {e}")  # It's good practice to log errors
            raise

    def update_user_password(self, username, new_password):
        try:
            print(f"Updating password for username: {username}")  # Debugging line
            stmt_update_template = """
                UPDATE {schema}.USERACCOUNT
                SET PASSWORD = :new_password
                WHERE USERNAME = :username
            """
            # Explicitly begin a transaction
            transaction = self.conn.begin()
            try:
                # Prepare and execute the update statement
                stmt_update = text(stmt_update_template.format(schema=self.schema_name)).bindparams(new_password=new_password, username=username)
                self.conn.execute(stmt_update)
                
                # Commit the transaction if no errors occurred
                transaction.commit()
                print(f"Password updated for {username}")  # Debugging line
                return True
            except:
                # Rollback the transaction in case of an error
                transaction.rollback()
                raise
        except SQLAlchemyError as e:
            print(f"SQLAlchemy Error during password update: {e}")  # It's good practice to log errors
            return False

    def get_user_credentials(self, username, password, company):
        try:
            
            stmt_select_template = """
                SELECT E.EMPLOYEE_ID, E.SK_EMPLOYEE, E.POSITION FROM {schema}.USERACCOUNT UA
                INNER JOIN {schema}.EMPLOYEE E ON UA.SK_EMPLOYEE = E.SK_EMPLOYEE
                INNER JOIN {schema}.COMPANY C ON E.SK_COMPANY = C.SK_COMPANY
                WHERE USERNAME = :username AND PASSWORD = :password AND COMPANY_ID = :company
            """
            stmt_select = text(stmt_select_template.format(schema=self.schema_name)).bindparams(username=username, password=password, company=company)
            print(stmt_select)
            result = self.conn.execute(stmt_select)
            return result.fetchone()
        except SQLAlchemyError as e:
            raise
    
    def get_time_in(self, user_id):
        try:
            stmt_check_entry_template = """
                SELECT SK_TIME_ENTRY  FROM {schema}.EMPLOYEE e
                INNER JOIN {schema}.TIMEENTRIES t ON e.SK_EMPLOYEE = t.SK_EMPLOYEE 
                WHERE e.EMPLOYEE_ID = :user_id
                AND DATE(CLOCKIN_DATETIME) = DATE((CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS)
            """

            stmt_check_entry = text(stmt_check_entry_template.format(schema=self.schema_name)).bindparams(user_id=user_id)
            result_check_entry = self.conn.execute(stmt_check_entry)
            return result_check_entry.fetchone()
        except SQLAlchemyError as e:
            raise

    def get_time_out(self, user_id):
        try:
            stmt_check_entry_template = """
                SELECT SK_TIME_ENTRY  FROM {schema}.EMPLOYEE e
                INNER JOIN {schema}.TIMEENTRIES t ON e.SK_EMPLOYEE = t.SK_EMPLOYEE 
                WHERE e.EMPLOYEE_ID = :user_id
                AND DATE(CLOCKIN_DATETIME) = DATE((CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS)
                AND CLOCKOUT_DATETIME IS NULL
            """

            stmt_check_entry = text(stmt_check_entry_template.format(schema=self.schema_name)).bindparams(user_id=user_id)
            result_check_entry = self.conn.execute(stmt_check_entry)
            return result_check_entry.fetchone()      
        except SQLAlchemyError as e:
            raise
       
    def insert_time_in(self, sk_emp):
        try:
            stmt_insert_entry_template = """
                INSERT INTO {schema}.TIMEENTRIES (SK_EMPLOYEE, CLOCKIN_DATETIME)
                VALUES (:sk_emp, (CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS)
            """

            stmt_insert_entry = text(stmt_insert_entry_template.format(schema=self.schema_name)).bindparams(sk_emp=sk_emp)  
            self.conn.execute(stmt_insert_entry)
        except SQLAlchemyError as e:
            raise
     
    def insert_time_out(self, sk_time_entry):
        try:
            stmt_update_entry_template = """
                UPDATE {schema}.TimeEntries
                SET CLOCKOUT_DATETIME = (CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS,
                TOTAL_HRS = RIGHT('0' || TRUNC((MIDNIGHT_SECONDS(CLOCKOUT_DATETIME) - MIDNIGHT_SECONDS(CLOCKIN_DATETIME)) / 3600), 2) || ':' ||
                    RIGHT('0' || MOD(TRUNC((MIDNIGHT_SECONDS(CLOCKOUT_DATETIME) - MIDNIGHT_SECONDS(CLOCKIN_DATETIME)) / 60), 60), 2) || ':' ||
                    RIGHT('0' || MOD(MIDNIGHT_SECONDS(CLOCKOUT_DATETIME) - MIDNIGHT_SECONDS(CLOCKIN_DATETIME), 60), 2)
                WHERE SK_TIME_ENTRY = :sk_time_entry
            """
            stmt_update_entry = text(stmt_update_entry_template.format(schema=self.schema_name)).bindparams(sk_time_entry=sk_time_entry)
            self.conn.execute(stmt_update_entry)
        except SQLAlchemyError as e:
            raise
        
    def select_time_entries(self, user_id, page=1, per_page=10):
        offset = (page - 1) * per_page
        try:
            stmt_select_entries_template = """
                SELECT DATE(t.CLOCKIN_DATETIME), t.CLOCKIN_DATETIME, t.CLOCKOUT_DATETIME, t.TOTAL_HRS, 
                    CASE WHEN TO_CHAR(t.CLOCKIN_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEIN THEN 'LATE' END AS STATUS,
                    CASE WHEN TO_CHAR(t.CLOCKOUT_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEOUT THEN 'OT' ELSE 'UT' END AS OT_UT                   
                FROM {schema}.EMPLOYEE e 
                INNER JOIN {schema}.SHIFT s ON e.SK_SHIFT = s.SK_SHIFT 
                INNER JOIN {schema}.TIMEENTRIES t ON e.SK_EMPLOYEE = t.SK_EMPLOYEE 
                WHERE (:user_id IN (SELECT EMPLOYEE_ID FROM {schema}.EMPLOYEE WHERE POSITION = 'Superuser') OR 
                    (e.EMPLOYEE_ID = :user_id))
                ORDER BY t.CLOCKIN_DATETIME DESC
                LIMIT :per_page OFFSET :offset
            """

            stmt_select_entries = text(stmt_select_entries_template.format(schema=self.schema_name)).bindparams(user_id=user_id, per_page=per_page, offset=offset)
            result_entries = self.conn.execute(stmt_select_entries)
            return result_entries.fetchall()

        except SQLAlchemyError as e:
            raise
      
    def count_time_entries(self, user_id):
        try:
            stmt_count_entries_template = """
                SELECT COUNT(*)
                FROM {schema}.TIMEENTRIES t
                INNER JOIN {schema}.EMPLOYEE e ON t.SK_EMPLOYEE = e.SK_EMPLOYEE
                WHERE (:user_id IN (SELECT EMPLOYEE_ID FROM {schema}.EMPLOYEE WHERE POSITION = 'Superuser') OR 
                    (e.EMPLOYEE_ID = :user_id))
            """
            stmt_count_entries = text(stmt_count_entries_template.format(schema=self.schema_name)).bindparams(user_id=user_id)
            result = self.conn.execute(stmt_count_entries)
            return result.scalar()  # Return the count

        except SQLAlchemyError as e:
            raise
        
    def select_time_entries_for_csv(self, user_id, start_date, end_date):
        try:
            stmt_select_entries_template = """
                SELECT e.FIRST_NAME || ' ' || e.LAST_NAME AS FULLNAME, DATE(t.CLOCKIN_DATETIME) AS DATE, t.CLOCKIN_DATETIME, t.CLOCKOUT_DATETIME, t.TOTAL_HRS, 
                    CASE WHEN TO_CHAR(t.CLOCKIN_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEIN THEN 'LATE' END AS STATUS,
                    CASE WHEN TO_CHAR(t.CLOCKOUT_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEOUT THEN 'OT' ELSE 'UT' END AS OT_UT, 
                    TIMESTAMP(DATE(t.CLOCKOUT_DATETIME), s.SHIFT_TIMEOUT) AS SHIFT_TIMEOUT_DATETIME                     
                FROM {schema}.EMPLOYEE e 
                INNER JOIN {schema}.SHIFT s ON e.SK_SHIFT = s.SK_SHIFT 
                INNER JOIN {schema}.TIMEENTRIES t ON e.SK_EMPLOYEE =t.SK_EMPLOYEE 
                WHERE (:user_id IN (SELECT EMPLOYEE_ID FROM {schema}.EMPLOYEE WHERE POSITION = 'Superuser') OR 
                    (e.EMPLOYEE_ID = :user_id)) AND (DATE(t.CLOCKIN_DATETIME)>= :start_date AND DATE(t.CLOCKIN_DATETIME)<= :end_date)
                ORDER BY FULLNAME, t.CLOCKIN_DATETIME DESC
            """

            stmt_select_entries = text(stmt_select_entries_template.format(schema=self.schema_name)).bindparams(user_id=user_id, start_date=start_date, end_date=end_date)  
            result_entries = self.conn.execute(stmt_select_entries)
            return result_entries.fetchall()

        except SQLAlchemyError  as e:
            raise 
        
    def close(self):
        self.conn.close()
