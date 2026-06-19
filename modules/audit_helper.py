# modules/audit_helper.py
import json
from datetime import date, datetime
from database import DatabaseManager

def _json_safe(value):
    """Convert common Python objects into JSON-serializable values."""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value

def _sync_audit_sequence(db):
    """Keep audit_log.id aligned with the backing SERIAL sequence."""
    db.execute_query(
        """
        SELECT setval(
            pg_get_serial_sequence('audit_log', 'id'),
            COALESCE((SELECT MAX(id) FROM audit_log), 1),
            (SELECT COUNT(*) > 0 FROM audit_log)
        )
        """
    )

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
    _sync_audit_sequence(db)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_json = json.dumps(_json_safe(old_values)) if old_values else None
    new_json = json.dumps(_json_safe(new_values)) if new_values else None
    db.execute_query(
        "INSERT INTO audit_log (table_name, record_id, action, old_values, new_values, user_id, timestamp) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (table_name, record_id, action, old_json, new_json, user_id, timestamp)
    )
