import psycopg2
from datetime import datetime
import time
from utilities.db_config import POSTGRES_CONFIG

class AuditLogger:
    MAX_RETRIES = 3
    RETRY_DELAY = 0.1  # 100ms delay between retries

    @staticmethod
    def validate_username(username):
        """Validate username exists in PostgreSQL users_list table"""
        if username == "SYSTEM":
            return True
            
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            cursor.execute("SELECT username FROM users_list WHERE username = %s", (username,))
            return cursor.fetchone() is not None
            
        except psycopg2.Error as e:
            print(f"Error validating username in PostgreSQL: {str(e)}")
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass  # Ignore cursor close errors
            if conn:
                try:
                    conn.close()
                except:
                    pass  # Ignore connection close errors

    @staticmethod
    def log_action(connection, username, action, details=None):
        if username is None:  # Handle cases where user isn't logged in
            username = "SYSTEM"
        
        # Validate username exists in database
        if not AuditLogger.validate_username(username):
            error_msg = f"Invalid username '{username}' - not found in database"
            print(error_msg)
            raise ValueError(error_msg)

        # Use PostgreSQL for audit logging
        audit_conn = None
        cursor = None
        retries = 0
        last_error = None

        while retries < AuditLogger.MAX_RETRIES:
            try:
                audit_conn = psycopg2.connect(**POSTGRES_CONFIG)
                cursor = audit_conn.cursor()
                
                cursor.execute('''
                INSERT INTO audit_log (username, action, details)
                VALUES (%s, %s, %s)
                ''', (username, action, str(details) if details else None))
                
                audit_conn.commit()
                return  # Success - exit the retry loop
                
            except psycopg2.Error as e:
                last_error = e
                print(f"Error logging audit trail (attempt {retries + 1}/{AuditLogger.MAX_RETRIES}): {str(e)}")
                if audit_conn:
                    try:
                        audit_conn.rollback()
                    except:
                        pass  # Ignore rollback errors
                retries += 1
                if retries < AuditLogger.MAX_RETRIES:
                    time.sleep(AuditLogger.RETRY_DELAY * retries)  # Exponential backoff
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except:
                        pass  # Ignore cursor close errors
                if audit_conn:
                    try:
                        audit_conn.close()
                    except:
                        pass  # Ignore connection close errors

        # If we get here, all retries failed
        print(f"Failed to log audit trail after {AuditLogger.MAX_RETRIES} attempts")
        if last_error:
            raise last_error  # Re-raise the last error to be handled by the caller
