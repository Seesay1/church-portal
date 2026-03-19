import sqlite3
import hashlib
from sqlite3 import Error
import os

DB_FILE = "church_system.db"

# --- Security Helper ---
def hash_password(password):
    """Return a hashed version of the password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

class DatabaseManager:
    def __init__(self):
        self.conn = None

    def connect(self):
        try:
            self.conn = sqlite3.connect(DB_FILE, timeout=10)
            self.conn.execute("PRAGMA foreign_keys = ON")
            return self.conn
        except Error as e:
            print(f"Database connection error: {e}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()

    def execute_query(self, query, params=()):
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)  # wait up to 10 seconds
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Query Error: {e}")
            return False
        finally:
            if conn:
                conn.close()

    def fetch_all(self, query, params=None):
        """Execute a SELECT query and return all rows."""
        if not self.connect():
            return []
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Error as e:
            print(f"Fetch Error: {e}")
            return []
        finally:
            self.close()

    def fetch_one(self, query, params=None):
        """Execute a SELECT query and return one row."""
        if not self.connect():
            return None
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
        except Error as e:
            print(f"Fetch Error: {e}")
            return None
        finally:
            self.close()


def setup_database():
    import os
    print("Database path:", os.path.abspath(DB_FILE))
    """Create all tables with retry on lock."""
    import time
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            with sqlite3.connect(DB_FILE, timeout=20) as conn:
                conn.execute("PRAGMA foreign_keys = ON")
                cursor = conn.cursor()
                # ... all your CREATE TABLE statements ...
                conn.commit()
            print("Database setup complete!")
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e) and attempt < max_attempts - 1:
                print(f"Database locked, retrying ({attempt+1}/{max_attempts})...")
                time.sleep(2)
            else:
                print(f"Fatal database error: {e}")
                raise

    # ---------- Branches ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        address TEXT,
        phone TEXT
    )
    """)

    # ---------- Groups ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    # ---------- Departments ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    # ---------- Members ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT UNIQUE,
        branch_id INTEGER,
        full_name TEXT,
        gender TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        group_id INTEGER,
        department_id INTEGER,
        occupation TEXT,
        marital_status TEXT,
        parent_name TEXT,
        school_class TEXT,
        age INTEGER,
        photo TEXT,
        baptism_date TEXT,
        baptized_by TEXT,
        baptism_place TEXT,
        confirmation_date TEXT,
        confirmed_by TEXT,
        date_joined TEXT,
        FOREIGN KEY(branch_id) REFERENCES branches(id),
        FOREIGN KEY(group_id) REFERENCES groups(id),
        FOREIGN KEY(department_id) REFERENCES departments(id)
    )
    """)

    try:
        cursor.execute("ALTER TABLE members ADD COLUMN confirmation_place TEXT")
    except:
        pass

    # ---------- Families / Household ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS families (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_name TEXT,
        head_of_family TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        member_id INTEGER,
        relation TEXT,
        FOREIGN KEY(family_id) REFERENCES families(id),
        FOREIGN KEY(member_id) REFERENCES members(id)
    )
    """)

    # ---------- Attendance ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        branch_id INTEGER,
        group_id INTEGER,
        date TEXT,
        event_id INTEGER,
        present INTEGER DEFAULT 0,
        FOREIGN KEY(member_id) REFERENCES members(id),
        FOREIGN KEY(branch_id) REFERENCES branches(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    """)
    
    # Add 'present' column if table exists but column is missing (for existing DBs)
    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN present INTEGER DEFAULT 0")
    except:
        pass

    # ---------- Financial Records ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        member_id INTEGER,
        branch_id INTEGER,
        group_id INTEGER,
        amount REAL,
        date TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id),
        FOREIGN KEY(branch_id) REFERENCES branches(id),
        FOREIGN KEY(group_id) REFERENCES groups(id)
    )
    """)
    # Add description column if missing (fix for contributions page)
    try:
        cursor.execute("ALTER TABLE financial_records ADD COLUMN description TEXT")
    except:
        pass

    # ---------- Events ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        branch_id INTEGER,
        date TEXT,
        description TEXT,
        time TEXT,
        location TEXT,
        branch_group TEXT,
        FOREIGN KEY(branch_id) REFERENCES branches(id)
    )
    """)
    
    # Add missing columns for events (capacity, registration_deadline, created_by)
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN capacity INTEGER")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN registration_deadline DATE")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE events ADD COLUMN created_by INTEGER REFERENCES users(id)")
    except:
        pass

    # ---------- Event Registrations ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
        member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        attended INTEGER DEFAULT 0,
        UNIQUE(event_id, member_id)
    )
    """)

    # ---------- SMS Logs ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sms_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT,
        message TEXT,
        status TEXT,
        date_sent TEXT
    )
    """)

    # ---------- Settings ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        value TEXT
    )
    """)
    
    # Insert default settings
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", ('church_name', 'Your Church'))
    
    # ---------- Users ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)
    # Add security question and answer columns if they don't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN security_answer TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN branch_id INTEGER REFERENCES branches(id)")
    except Exception as e:
        print("Note: branch_id column may already exist:", e)

    # ---------- Audit log table ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT,
        record_id INTEGER,
        action TEXT,  -- 'INSERT', 'UPDATE', 'DELETE'
        old_values TEXT,  -- JSON
        new_values TEXT,  -- JSON
        user_id INTEGER,
        timestamp TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    # ---------- Member portal PINs ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS member_portal (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER UNIQUE,
        pin TEXT,  -- hashed PIN
        last_login TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id)
    )
    """)
    try:
        cursor.execute("ALTER TABLE member_portal ADD COLUMN last_login TEXT")
    except:
        pass

    # ---------- User widgets preferences (for dashboard) ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_widgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        widget_name TEXT,
        widget_order INTEGER,
        is_visible INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)    

    # ---------- Certificates ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        certificate_type TEXT,
        verse TEXT,
        generated_date TEXT,
        FOREIGN KEY (member_id) REFERENCES members(id)
    )
    """)
    
    # ---------- ID Cards ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS id_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER,
        generated_date TEXT,
        FOREIGN KEY (member_id) REFERENCES members(id)
    )
    """)
    
    # ---------- Certificate Requests (for member portal) ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificate_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER NOT NULL,
        certificate_type TEXT NOT NULL,
        request_date TEXT NOT NULL,
        status TEXT DEFAULT 'pending',  -- pending, approved, completed, rejected
        admin_notes TEXT,
        FOREIGN KEY(member_id) REFERENCES members(id)
    )
    """)


    # ---------- Prayer Requests ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prayer_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
        request TEXT NOT NULL,
        is_public INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',  -- pending, prayed, answered
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------- Member-to-Member Family Links (direct relationships) ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member1_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        member2_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        relationship TEXT,  -- 'spouse', 'child', 'parent', 'sibling'
        status TEXT DEFAULT 'approved',  -- 'approved', 'pending' (if approval required)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(member1_id, member2_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_link_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        target_member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        relationship TEXT,
        status TEXT DEFAULT 'pending',  -- pending, approved, rejected
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(requester_id, target_member_id)
    )
    """)


    # ---------- Committees ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,                -- e.g. "Administration and Human Resources"
        description TEXT,
        chairperson_id INTEGER,           -- member ID (from members table)
        created_date TEXT,
        FOREIGN KEY (chairperson_id) REFERENCES members(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        committee_id INTEGER,
        member_id INTEGER,
        role TEXT,                        -- e.g. "Member", "Secretary", "Treasurer"
        joined_date TEXT,
        FOREIGN KEY (committee_id) REFERENCES committees(id),
        FOREIGN KEY (member_id) REFERENCES members(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        committee_id INTEGER,
        meeting_date TEXT,
        agenda TEXT,
        minutes TEXT,
        location TEXT,
        FOREIGN KEY (committee_id) REFERENCES committees(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        committee_id INTEGER,
        name TEXT,
        description TEXT,
        start_date TEXT,
        end_date TEXT,
        budget REAL,
        status TEXT DEFAULT 'planned',     -- planned, ongoing, completed, cancelled
        FOREIGN KEY (committee_id) REFERENCES committees(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activity_id INTEGER,
        amount REAL,
        expense_date TEXT,
        description TEXT,
        FOREIGN KEY (activity_id) REFERENCES committee_activities(id)
    )
    """)

    # Committee roles (per committee, with unique names)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        committee_id INTEGER NOT NULL,
        UNIQUE(committee_id, name),
        FOREIGN KEY(committee_id) REFERENCES committees(id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notification_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        title TEXT,
        message TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # In database.py, add to your existing table creation section
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        file_type TEXT,
        download_count INTEGER DEFAULT 0,
        uploaded_by INTEGER,  -- removed REFERENCES members(id) for now
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blog_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT,
        category TEXT,
        published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_published INTEGER DEFAULT 1
    )
    """)
    
    # ---------- Default Admin ----------
    default_pass = hash_password("admin123")
    cursor.execute("""
    INSERT OR IGNORE INTO users(username, password, role)
    VALUES(?,?,?)
    """, ('admin', default_pass, 'Admin'))
    

    # ---------- Commit & Close ----------
    conn.commit()
    conn.close()
    print("Database setup complete!")
    

if __name__ == "__main__":
    setup_database()