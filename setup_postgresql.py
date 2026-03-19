# setup_postgresql.py (corrected order)
import psycopg2
from psycopg2 import sql
import hashlib

# ================== CONFIGURATION ==================
DATABASE_URL = "postgresql://church_user:2311@localhost:5432/church_db"

def hash_password(password):
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("Connected to PostgreSQL")

    # ---------- Branches ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS branches (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        address TEXT,
        phone TEXT
    )
    """)

    # ---------- Groups ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    )
    """)

    # ---------- Departments ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE
    )
    """)

    # ---------- Members ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS members (
        id SERIAL PRIMARY KEY,
        member_id TEXT UNIQUE,
        branch_id INTEGER REFERENCES branches(id),
        full_name TEXT,
        gender TEXT,
        phone TEXT,
        email TEXT,
        address TEXT,
        group_id INTEGER REFERENCES groups(id),
        department_id INTEGER REFERENCES departments(id),
        occupation TEXT,
        marital_status TEXT,
        parent_name TEXT,
        school_class TEXT,
        age INTEGER,
        photo TEXT,
        baptism_date DATE,
        baptized_by TEXT,
        baptism_place TEXT,
        confirmation_date DATE,
        confirmed_by TEXT,
        confirmation_place TEXT,
        date_joined DATE,
        birth_date DATE,
        place_of_birth TEXT,
        directory_opt_in INTEGER DEFAULT 0
    )
    """)

    # ---------- Families ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS families (
        id SERIAL PRIMARY KEY,
        family_name TEXT,
        head_of_family TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_members (
        id SERIAL PRIMARY KEY,
        family_id INTEGER REFERENCES families(id),
        member_id INTEGER REFERENCES members(id),
        relation TEXT
    )
    """)

    # ---------- Attendance ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY,
        member_id INTEGER REFERENCES members(id),
        branch_id INTEGER REFERENCES branches(id),
        group_id INTEGER REFERENCES groups(id),
        date DATE,
        event_id INTEGER,
        present INTEGER DEFAULT 0
    )
    """)

    # ---------- Financial Records ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS financial_records (
        id SERIAL PRIMARY KEY,
        type TEXT,
        member_id INTEGER REFERENCES members(id),
        branch_id INTEGER REFERENCES branches(id),
        group_id INTEGER REFERENCES groups(id),
        amount REAL,
        date DATE,
        description TEXT
    )
    """)

    # ---------- Settings ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id SERIAL PRIMARY KEY,
        key TEXT UNIQUE,
        value TEXT
    )
    """)
    # Insert default church name
    cursor.execute("INSERT INTO settings (key, value) VALUES ('church_name', 'Your Church') ON CONFLICT (key) DO NOTHING")

    # ---------- Users ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        security_question TEXT,
        security_answer TEXT,
        branch_id INTEGER REFERENCES branches(id)
    )
    """)

    # ---------- Events ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id SERIAL PRIMARY KEY,
        name TEXT,
        branch_id INTEGER REFERENCES branches(id),
        date DATE,
        description TEXT,
        time TEXT,
        location TEXT,
        branch_group TEXT,
        capacity INTEGER,
        registration_deadline DATE,
        created_by INTEGER REFERENCES users(id)
    )
    """)

    # ---------- Event Registrations ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS event_registrations (
        id SERIAL PRIMARY KEY,
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
        id SERIAL PRIMARY KEY,
        phone TEXT,
        message TEXT,
        status TEXT,
        date_sent TIMESTAMP
    )
    """)

    # ---------- Audit Log ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id SERIAL PRIMARY KEY,
        table_name TEXT,
        record_id INTEGER,
        action TEXT,
        old_values TEXT,
        new_values TEXT,
        user_id INTEGER REFERENCES users(id),
        timestamp TIMESTAMP
    )
    """)

    # ---------- Member Portal ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS member_portal (
        id SERIAL PRIMARY KEY,
        member_id INTEGER UNIQUE REFERENCES members(id),
        pin TEXT,
        last_login TEXT,
        security_question1 TEXT,
        security_answer1 TEXT,
        security_question2 TEXT,
        security_answer2 TEXT
    )
    """)

    # ---------- User Widgets ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_widgets (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        widget_name TEXT,
        widget_order INTEGER,
        is_visible INTEGER DEFAULT 1
    )
    """)

    # ---------- Certificates ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificates (
        id SERIAL PRIMARY KEY,
        member_id INTEGER REFERENCES members(id),
        certificate_type TEXT,
        verse TEXT,
        generated_date DATE
    )
    """)

    # ---------- ID Cards ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS id_cards (
        id SERIAL PRIMARY KEY,
        member_id INTEGER REFERENCES members(id),
        generated_date DATE
    )
    """)

    # ---------- Certificate Requests ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS certificate_requests (
        id SERIAL PRIMARY KEY,
        member_id INTEGER NOT NULL REFERENCES members(id),
        certificate_type TEXT NOT NULL,
        request_date TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        admin_notes TEXT
    )
    """)

    # ---------- Prayer Requests ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prayer_requests (
        id SERIAL PRIMARY KEY,
        member_id INTEGER REFERENCES members(id) ON DELETE SET NULL,
        request TEXT NOT NULL,
        is_public INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------- Family Links ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_links (
        id SERIAL PRIMARY KEY,
        member1_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        member2_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        relationship TEXT,
        status TEXT DEFAULT 'approved',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(member1_id, member2_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_link_requests (
        id SERIAL PRIMARY KEY,
        requester_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        target_member_id INTEGER REFERENCES members(id) ON DELETE CASCADE,
        relationship TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(requester_id, target_member_id)
    )
    """)

    # ---------- Committees ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committees (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        description TEXT,
        chairperson_id INTEGER REFERENCES members(id),
        branch_id INTEGER REFERENCES branches(id),
        created_date DATE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_members (
        id SERIAL PRIMARY KEY,
        committee_id INTEGER REFERENCES committees(id),
        member_id INTEGER REFERENCES members(id),
        role TEXT,
        joined_date DATE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_meetings (
        id SERIAL PRIMARY KEY,
        committee_id INTEGER REFERENCES committees(id),
        meeting_date DATE,
        agenda TEXT,
        minutes TEXT,
        location TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_activities (
        id SERIAL PRIMARY KEY,
        committee_id INTEGER REFERENCES committees(id),
        name TEXT,
        description TEXT,
        start_date DATE,
        end_date DATE,
        budget REAL,
        status TEXT DEFAULT 'planned'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_expenses (
        id SERIAL PRIMARY KEY,
        activity_id INTEGER REFERENCES committee_activities(id),
        amount REAL,
        expense_date DATE,
        description TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS committee_roles (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        committee_id INTEGER NOT NULL REFERENCES committees(id) ON DELETE CASCADE,
        UNIQUE(committee_id, name)
    )
    """)

    # ---------- Notification History ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notification_history (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,
        type TEXT,
        title TEXT,
        message TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------- Resources ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resources (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        file_type TEXT,
        download_count INTEGER DEFAULT 0,
        uploaded_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ---------- Blog Posts ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blog_posts (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        author TEXT,
        category TEXT,
        published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_published INTEGER DEFAULT 1
    )
    """)

    # ---------- Volunteer Opportunities ----------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS volunteer_opportunities (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        role TEXT,
        date DATE NOT NULL,
        start_time TEXT,
        end_time TEXT,
        location TEXT,
        capacity INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER REFERENCES users(id),
        status TEXT DEFAULT 'active',
        branch_id INTEGER REFERENCES branches(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS volunteer_signups (
        id SERIAL PRIMARY KEY,
        opportunity_id INTEGER NOT NULL REFERENCES volunteer_opportunities(id) ON DELETE CASCADE,
        member_id INTEGER NOT NULL REFERENCES members(id) ON DELETE CASCADE,
        signed_up_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'registered',
        notes TEXT,
        UNIQUE(opportunity_id, member_id)
    )
    """)

    # ---------- Default Admin ----------
    default_pass = hash_password("admin123")
    cursor.execute("""
        INSERT INTO users (username, password, role)
        VALUES ('admin', %s, 'Admin')
        ON CONFLICT (username) DO NOTHING
    """, (default_pass,))

    conn.commit()
    print("All tables created and default admin inserted.")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()