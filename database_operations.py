from sqlalchemy import create_engine, text 
from sqlalchemy.exc import SQLAlchemyError

class DatabaseOperations:
    def __init__(self):
        # self.conn = connection
        
        # Configure DB2 Connection
        conn_str = "db2://qqw84224:EbkZsMdg4x5dlfpC@9938aec0-8105-433e-8bf9-0fbb7e483086.c1ogj3sd0tgtu0lqde00.databases.appdomain.cloud:32459/bludb?SECURITY=ssl"
        self.conn=create_engine(conn_str).connect()

    def get_user_credentials(self, username, password, company):
        try:
            stmt_select = text("""
                SELECT E.EMPLOYEE_ID, E.SK_EMPLOYEE FROM USERACCOUNT UA 
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

    def select_time_entries(self, user_id):
        try:
            stmt_select_entries = text("""
                SELECT DATE(t.CLOCKIN_DATETIME), t.CLOCKIN_DATETIME, t.CLOCKOUT_DATETIME, t.TOTAL_HRS, 
                    CASE WHEN TO_CHAR(t.CLOCKIN_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEIN THEN 'LATE' END AS STATUS,
                    CASE WHEN TO_CHAR(t.CLOCKOUT_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEOUT THEN 'OT' ELSE 'UT' END AS OT_UT                   
                FROM EMPLOYEE e 
                INNER JOIN SHIFT s ON e.SK_SHIFT = s.SK_SHIFT 
                INNER JOIN TIMEENTRIES t ON e.SK_EMPLOYEE =t.SK_EMPLOYEE 
                WHERE EMPLOYEE_ID = :user_id
                ORDER BY t.CLOCKIN_DATETIME DESC
            """).bindparams(user_id=user_id)

            result_entries = self.conn.execute(stmt_select_entries)
            return result_entries.fetchall()

        except SQLAlchemyError  as e:
            raise 
    
    def select_time_entries_for_csv(self, user_id, start_date, end_date):
        try:
            stmt_select_entries = text("""
                SELECT DATE(t.CLOCKIN_DATETIME), t.CLOCKIN_DATETIME, t.CLOCKOUT_DATETIME, t.TOTAL_HRS, 
                    CASE WHEN TO_CHAR(t.CLOCKIN_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEIN THEN 'LATE' END AS STATUS,
                    CASE WHEN TO_CHAR(t.CLOCKOUT_DATETIME, 'HH24:MI:SS') > s.SHIFT_TIMEOUT THEN 'OT' ELSE 'UT' END AS OT_UT                   
                FROM EMPLOYEE e 
                INNER JOIN SHIFT s ON e.SK_SHIFT = s.SK_SHIFT 
                INNER JOIN TIMEENTRIES t ON e.SK_EMPLOYEE =t.SK_EMPLOYEE 
                WHERE EMPLOYEE_ID = :user_id AND (DATE(t.CLOCKIN_DATETIME)>= :start_date AND DATE(t.CLOCKIN_DATETIME)<= :end_date)
                ORDER BY t.CLOCKIN_DATETIME DESC
            """).bindparams(user_id=user_id, start_date=start_date, end_date=end_date)

            result_entries = self.conn.execute(stmt_select_entries)
            return result_entries.fetchall()

        except SQLAlchemyError  as e:
            raise 
    
    