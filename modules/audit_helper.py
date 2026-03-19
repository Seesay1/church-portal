# modules/audit_helper.py
import json
from datetime import datetime
from database import DatabaseManager

def log_action(table_name, record_id, action, old_values=None, new_values=None, user_id=None):
    """
    Insert a record into audit_log.
    - table_name: e.g., 'members'
    - record_id: the primary key of the affected row
    - action: 'INSERT', 'UPDATE', 'DELETE'
    - old_values: dict of old values (for UPDATE/DELETE) or None
    - new_values: dict of new values (for INSERT/UPDATE) or None
    - user_id: current user's database ID
    """
    db = DatabaseManager()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_json = json.dumps(old_values) if old_values else None
    new_json = json.dumps(new_values) if new_values else None
    db.execute_query(
        "INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, user_id, timestamp) VALUES (?,?,?,?,?,?,?)",
        (table_name, record_id, action, old_json, new_json, user_id, timestamp)
    )