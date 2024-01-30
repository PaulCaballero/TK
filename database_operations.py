from sqlalchemy import create_engine, text 
from sqlalchemy.exc import SQLAlchemyError
import os
class DatabaseOperations:
    def __init__(self):
        # self.conn = connection
        
        # Configure DB2 Connection
        db_user = os.getenv('uid')
        db_password = os.getenv('pwd')
        db_host = os.getenv('hostname')
        db_port = os.getenv('port', 'default_port')  # Default port if not specified
        db_name = os.getenv('database')

        conn_str = f"db2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?SECURITY=ssl"
        self.conn = create_engine(conn_str).connect()

    def get_user_credentials(self, username, password, company):
        try:
            stmt_select = text("""
                SELECT E.EMPLOYEE_ID, E.SK_EMPLOYEE, E.POSITION FROM USERACCOUNT UA 
                INNER JOIN QQW84224.EMPLOYEE E ON UA.SK_EMPLOYEE = E.SK_EMPLOYEE
                INNER JOIN QQW84224.COMPANY C ON E.SK_COMPANY = C.SK_COMPANY
                WHERE USERNAME = :username AND PASSWORD = :password AND COMPANY_ID = :company
            """).bindparams(username=username, password=password, company=company)

            result = self.conn.execute(stmt_select)
            return result.fetchone()
        except SQLAlchemyError as e:
            raise
    
    def get_time_in(self, user_id):
        try:
            stmt_check_entry = text("""
                SELECT SK_TIME_ENTRY  FROM EMPLOYEE e
                INNER JOIN TIMEENTRIES t ON e.SK_EMPLOYEE = t.SK_EMPLOYEE 
                WHERE e.EMPLOYEE_ID = :user_id
                AND DATE(CLOCKIN_DATETIME) = DATE((CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS)
            """).bindparams(user_id=user_id)

            result_check_entry = self.conn.execute(stmt_check_entry)
            return result_check_entry.fetchone()
        except SQLAlchemyError as e:
            raise
    
    def get_time_out(self, user_id):
        try:
            stmt_check_entry = text("""
                SELECT SK_TIME_ENTRY  FROM EMPLOYEE e
                INNER JOIN TIMEENTRIES t ON e.SK_EMPLOYEE = t.SK_EMPLOYEE 
                WHERE e.EMPLOYEE_ID = :user_id
                AND DATE(CLOCKIN_DATETIME) = DATE((CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS)
                AND CLOCKOUT_DATETIME IS NULL
            """).bindparams(user_id=user_id)
            result_check_entry = self.conn.execute(stmt_check_entry)
            return result_check_entry.fetchone()      
        except SQLAlchemyError as e:
            raise

    def insert_time_in(self, sk_emp):
        try:
            stmt_insert_entry = text("""
                INSERT INTO TIMEENTRIES (SK_EMPLOYEE, CLOCKIN_DATETIME)
                VALUES (:sk_emp, (CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS)
            """).bindparams(sk_emp=sk_emp)

            self.conn.execute(stmt_insert_entry)
        except SQLAlchemyError as e:
            raise

    def insert_time_out(self, sk_time_entry):
        try:
            stmt_update_entry = text("""
                UPDATE TimeEntries
                SET CLOCKOUT_DATETIME = (CURRENT TIMESTAMP - CURRENT TIMEZONE) + 8 HOURS,
                TOTAL_HRS = RIGHT('0' || TRUNC((MIDNIGHT_SECONDS(CLOCKOUT_DATETIME) - MIDNIGHT_SECONDS(CLOCKIN_DATETIME)) / 3600), 2) || ':' ||
                    RIGHT('0' || MOD(TRUNC((MIDNIGHT_SECONDS(CLOCKOUT_DATETIME) - MIDNIGHT_SECONDS(CLOCKIN_DATETIME)) / 60), 60), 2) || ':' ||
                    RIGHT('0' || MOD(MIDNIGHT_SECONDS(CLOCKOUT_DATETIME) - MIDNIGHT_SECONDS(CLOCKIN_DATETIME), 60), 2)
                WHERE SK_TIME_ENTRY = :sk_time_entry
            """).bindparams(sk_time_entry=sk_time_entry)

            self.conn.execute(stmt_update_entry)
        except SQLAlchemyError as e:
            raise

    def select_time_entries(self, user_id, page=1, per_page=10):
        offset = (page - 1) * per_page
        try:
            stmt_select_entries = text("""
                SELECT DATE(t.CLOCKIN_DATETIME), t.CLOCKIN_DATETIME, t.CLOCKOUT_DATETIME, t.TOTAL_HRS, 
                    CASE WHEN TO_CHAR(t.CLOCKIN_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEIN THEN 'LATE' END AS STATUS,
                    CASE WHEN TO_CHAR(t.CLOCKOUT_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEOUT THEN 'OT' ELSE 'UT' END AS OT_UT                   
                FROM EMPLOYEE e 
                INNER JOIN SHIFT s ON e.SK_SHIFT = s.SK_SHIFT 
                INNER JOIN TIMEENTRIES t ON e.SK_EMPLOYEE = t.SK_EMPLOYEE 
                WHERE (:user_id IN (SELECT EMPLOYEE_ID FROM EMPLOYEE WHERE POSITION = 'Superuser') OR 
                    (e.EMPLOYEE_ID = :user_id))
                ORDER BY t.CLOCKIN_DATETIME DESC
                LIMIT :per_page OFFSET :offset
            """).bindparams(user_id=user_id, per_page=per_page, offset=offset)

            result_entries = self.conn.execute(stmt_select_entries)
            return result_entries.fetchall()

        except SQLAlchemyError as e:
            raise
        
    def count_time_entries(self, user_id):
        try:
            stmt_count_entries = text("""
                SELECT COUNT(*)
                FROM TIMEENTRIES t
                INNER JOIN EMPLOYEE e ON t.SK_EMPLOYEE = e.SK_EMPLOYEE
                WHERE (:user_id IN (SELECT EMPLOYEE_ID FROM EMPLOYEE WHERE POSITION = 'Superuser') OR 
                    (e.EMPLOYEE_ID = :user_id))
            """).bindparams(user_id=user_id)

            result = self.conn.execute(stmt_count_entries)
            return result.scalar()  # Return the count

        except SQLAlchemyError as e:
            raise

    
    def select_time_entries_for_csv(self, user_id, start_date, end_date):
        try:
            stmt_select_entries = text("""
                SELECT e.FIRST_NAME || ' ' || e.LAST_NAME AS FULLNAME, DATE(t.CLOCKIN_DATETIME) AS DATE, t.CLOCKIN_DATETIME, t.CLOCKOUT_DATETIME, t.TOTAL_HRS, 
                    CASE WHEN TO_CHAR(t.CLOCKIN_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEIN THEN 'LATE' END AS STATUS,
                    CASE WHEN TO_CHAR(t.CLOCKOUT_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEOUT THEN 'OT' ELSE 'UT' END AS OT_UT, 
                    TIMESTAMP(DATE(t.CLOCKOUT_DATETIME), s.SHIFT_TIMEOUT) AS SHIFT_TIMEOUT_DATETIME                     
                FROM EMPLOYEE e 
                INNER JOIN SHIFT s ON e.SK_SHIFT = s.SK_SHIFT 
                INNER JOIN TIMEENTRIES t ON e.SK_EMPLOYEE =t.SK_EMPLOYEE 
                WHERE (:user_id IN (SELECT EMPLOYEE_ID FROM EMPLOYEE WHERE POSITION = 'Superuser') OR 
                    (e.EMPLOYEE_ID = :user_id)) AND (DATE(t.CLOCKIN_DATETIME)>= :start_date AND DATE(t.CLOCKIN_DATETIME)<= :end_date)
                ORDER BY FULLNAME, t.CLOCKIN_DATETIME DESC
            """).bindparams(user_id=user_id, start_date=start_date, end_date=end_date)

            result_entries = self.conn.execute(stmt_select_entries)
            return result_entries.fetchall()

        except SQLAlchemyError  as e:
            raise 
    
    