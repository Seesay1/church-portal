from werkzeug.utils import secure_filename, send_from_directory
import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import DatabaseManager, hash_password  # your existing DB module
import re
from flask import send_from_directory
from werkzeug.utils import secure_filename
from flask import send_from_directory, abort


app = Flask(__name__)
app.secret_key = os.urandom(24)  # replace with a fixed key in production

# Add near the top after app initialization
app.config['PHOTOS_PATH'] = os.path.join(os.path.dirname(__file__), 'photos')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Add with your other app configurations
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads/resources')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB for resources
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'mp3', 'mp4', 'pptx', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------------------------------------------------------
# Helper: get member details by internal ID
# -------------------------------------------------------------------
def get_member_by_id(member_id):
    db = DatabaseManager()
    # Debug: check if table exists and has data
    try:
        tables = db.fetch_all("SELECT name FROM sqlite_master WHERE type='table'")
        print("DEBUG: Tables in database:", [t[0] for t in tables])
        count = db.fetch_one("SELECT COUNT(*) FROM resources")
        print(f"DEBUG: resources table count = {count[0] if count else 0}")
    except Exception as e:
        print("DEBUG: Error checking resources table:", e)
    row = db.fetch_one("""
        SELECT m.id, m.member_id, m.full_name, m.gender, m.phone, m.email,
               m.address, m.occupation, m.marital_status, m.parent_name,
               m.school_class, m.baptism_date, m.date_joined,
               b.name as branch_name, g.name as group_name, d.name as dept_name,
               m.photo
        FROM members m
        LEFT JOIN branches b ON m.branch_id = b.id
        LEFT JOIN groups g ON m.group_id = g.id
        LEFT JOIN departments d ON m.department_id = d.id
        WHERE m.id = ?
    """, (member_id,))
    if not row:
        return None
    columns = [
        "id", "member_id", "full_name", "gender", "phone", "email",
        "address", "occupation", "marital_status", "parent_name",
        "school_class", "baptism_date", "date_joined", "branch_name",
        "group_name", "dept_name", "photo"
    ]
    return dict(zip(columns, row))

# -------------------------------------------------------------------
# Helper: get total contributions for a member
# -------------------------------------------------------------------
def get_total_contributions(member_id):
    db = DatabaseManager()
    row = db.fetch_one("SELECT SUM(amount) FROM financial_records WHERE member_id = ?", (member_id,))
    return row[0] if row and row[0] else 0

# -------------------------------------------------------------------
# Helper: get attendance count
# -------------------------------------------------------------------
def get_attendance_count(member_id):
    db = DatabaseManager()
    row = db.fetch_one("SELECT COUNT(*) FROM attendance WHERE member_id = ? AND present = 1", (member_id,))
    return row[0] if row else 0


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------
@app.context_processor
def inject_church_name():
    """Make church_name available in all templates."""
    db = DatabaseManager()
    row = db.fetch_one("SELECT value FROM settings WHERE key='church_name'")
    church_name = row[0] if row else "Your Church"
    return dict(church_name=church_name)

@app.route('/')
def home():
    if 'member_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    member_id_input = request.form.get('member_id', '').strip()
    pin_input = request.form.get('pin', '').strip()

    if not member_id_input or not pin_input:
        flash("Please enter both Member ID and PIN.", "danger")
        return redirect(url_for('home'))

    db = DatabaseManager()
    # Look up member by displayed member_id
    member = db.fetch_one("SELECT id FROM members WHERE member_id = ?", (member_id_input,))
    if not member:
        flash("Invalid Member ID or PIN.", "danger")
        return redirect(url_for('home'))

    internal_id = member[0]
    portal = db.fetch_one("SELECT pin FROM member_portal WHERE member_id = ?", (internal_id,))
    if not portal:
        flash("No PIN set for this member. Please contact the church office.", "warning")
        return redirect(url_for('home'))

    # Verify PIN (using your existing hash_password function)
    if portal[0] == hash_password(pin_input):
        session['member_id'] = internal_id
        session['member_name'] = get_member_by_id(internal_id)['full_name']
        # Update last_login
        db.execute_query("UPDATE member_portal SET last_login = ? WHERE member_id = ?",
                         (datetime.now().isoformat(), internal_id))
        flash(f"Welcome back, {session['member_name']}!", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid Member ID or PIN.", "danger")
        return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    member = get_member_by_id(session['member_id'])
    total_contrib = get_total_contributions(session['member_id'])
    attendance_count = get_attendance_count(session['member_id'])

    db = DatabaseManager()
    member_id = session['member_id']

    # Family counts
    family_linked = db.fetch_one("SELECT COUNT(*) FROM family_links WHERE member1_id=? OR member2_id=?", (member_id, member_id))
    family_count = family_linked[0] if family_linked else 0

    pending = db.fetch_one("SELECT COUNT(*) FROM family_link_requests WHERE target_member_id=? AND status='pending'", (member_id,))
    pending_family = pending[0] if pending else 0

    # Profile completion percentage (based on phone, email, address)
    fields = [member.get('phone'), member.get('email'), member.get('address')]
    filled = sum(1 for f in fields if f and f.strip())
    profile_completion = int((filled / 3) * 100)

    # Last attendance date
    last_att = db.fetch_one("SELECT date FROM attendance WHERE member_id=? AND present=1 ORDER BY date DESC LIMIT 1", (member_id,))
    last_attendance_date = last_att[0] if last_att else 'N/A'

    # Recent prayer requests (last 3)
    prayers = db.fetch_all("SELECT request, created_at FROM prayer_requests WHERE member_id=? ORDER BY created_at DESC LIMIT 3", (member_id,))
    recent_prayers = [{'request': r[0], 'created_at': r[1]} for r in prayers]

    # Next event date (nearest upcoming event)
    next_ev = db.fetch_one("SELECT date FROM events WHERE date >= date('now') ORDER BY date ASC LIMIT 1")
    next_event_date = next_ev[0] if next_ev else 'None'

    # Recent contributions (last 5)
    contribs = db.fetch_all("SELECT date, description, amount FROM financial_records WHERE member_id=? ORDER BY date DESC LIMIT 5", (member_id,))
    recent_contributions = [{'date': c[0], 'description': c[1], 'amount': c[2]} for c in contribs]

    # Upcoming events for the dashboard (maybe 3)
    upcoming_events_raw = db.fetch_all("SELECT name as title, date, 'TBA' as time FROM events WHERE date >= date('now') ORDER BY date ASC LIMIT 3")
    upcoming_events = [{'title': e[0], 'date': e[1], 'time': e[2]} for e in upcoming_events_raw]

    return render_template('dashboard.html',
                           member=member,
                           total_contrib=total_contrib,
                           attendance_count=attendance_count,
                           family_count=family_count,
                           pending_family=pending_family,
                           profile_completion=profile_completion,
                           last_attendance_date=last_attendance_date,
                           recent_prayers=recent_prayers,
                           next_event_date=next_event_date,
                           recent_contributions=recent_contributions,
                           upcoming_events=upcoming_events)

@app.route('/profile')
def profile():
    if 'member_id' not in session:
        return redirect(url_for('home'))
    member = get_member_by_id(session['member_id'])
    
    # Get additional stats
    total_contrib = get_total_contributions(session['member_id'])
    attendance_count = get_attendance_count(session['member_id'])
    
    # Get family links count
    db = DatabaseManager()
    family_linked = db.fetch_one("SELECT COUNT(*) FROM family_links WHERE member1_id=? OR member2_id=?", (session['member_id'], session['member_id']))
    family_count = family_linked[0] if family_linked else 0
    
    return render_template('profile.html',
                           member=member,
                           total_contrib=total_contrib,
                           attendance_count=attendance_count,
                           family_count=family_count)

@app.route('/profile/edit', methods=['GET', 'POST'])
def profile_edit():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        occupation = request.form.get('occupation', '').strip()
        marital_status = request.form.get('marital_status', '').strip()
        parent_name = request.form.get('parent_name', '').strip()
        school_class = request.form.get('school_class', '').strip()
        # NEW: opt-in checkbox (returns 'on' if checked, else None)
        directory_opt_in = 1 if request.form.get('directory_opt_in') else 0

        # Basic validation
        if email and '@' not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for('profile_edit'))

        db = DatabaseManager()
        db.execute_query("""
            UPDATE members SET
                phone = ?, email = ?, address = ?, occupation = ?,
                marital_status = ?, parent_name = ?, school_class = ?,
                directory_opt_in = ?
            WHERE id = ?
        """, (phone, email, address, occupation, marital_status,
              parent_name, school_class, directory_opt_in, session['member_id']))

        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for('profile'))

    # GET request
    member = get_member_by_id(session['member_id'])
    return render_template('profile_edit.html', member=member)

@app.route('/contributions')
def contributions():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    rows = db.fetch_all("""
        SELECT date, description, amount
        FROM financial_records
        WHERE member_id = ?
        ORDER BY date DESC
    """, (session['member_id'],))

    contributions = [{"date": r[0], "description": r[1] or "Offering", "amount": r[2]} for r in rows]
    return render_template('contributions.html', contributions=contributions)



@app.route('/attendance')
def attendance():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    rows = db.fetch_all("""
        SELECT date
        FROM attendance
        WHERE member_id = ? AND present = 1
        ORDER BY date DESC
    """, (session['member_id'],))

    attendance_dates = [r[0] for r in rows]

    def calculate_streak(dates):
        if not dates:
            return 0
        date_objs = [datetime.strptime(d, '%Y-%m-%d').date() for d in dates]
        date_objs.sort(reverse=True)
        streak = 1
        current = date_objs[0]
        for next_date in date_objs[1:]:
            if (current - next_date).days == 1:
                streak += 1
                current = next_date
            else:
                break
        return streak

    def count_this_month(dates):
        if not dates:
            return 0
        today = date.today()
        count = 0
        for d in dates:
            dt = datetime.strptime(d, '%Y-%m-%d').date()
            if dt.year == today.year and dt.month == today.month:
                count += 1
        return count

    streak = calculate_streak(attendance_dates)
    this_month = count_this_month(attendance_dates)

    return render_template('attendance.html',
                           attendance_dates=attendance_dates,
                           streak=streak,
                           this_month=this_month)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route('/change-pin', methods=['GET', 'POST'])
def change_pin():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        current_pin = request.form.get('current_pin', '').strip()
        new_pin = request.form.get('new_pin', '').strip()
        confirm_pin = request.form.get('confirm_pin', '').strip()

        # Validate
        if not (current_pin and new_pin and confirm_pin):
            flash("All fields are required.", "danger")
            return redirect(url_for('change_pin'))

        if not re.match(r'^\d{4}$', new_pin):
            flash("New PIN must be exactly 4 digits.", "danger")
            return redirect(url_for('change_pin'))

        if new_pin != confirm_pin:
            flash("New PIN and confirmation do not match.", "danger")
            return redirect(url_for('change_pin'))

        db = DatabaseManager()
        # Fetch current hashed PIN
        row = db.fetch_one("SELECT pin FROM member_portal WHERE member_id = ?", (session['member_id'],))
        if not row:
            flash("PIN record not found. Contact admin.", "danger")
            return redirect(url_for('dashboard'))

        if row[0] != hash_password(current_pin):
            flash("Current PIN is incorrect.", "danger")
            return redirect(url_for('change_pin'))

        # Update to new hashed PIN
        new_hashed = hash_password(new_pin)
        db.execute_query("UPDATE member_portal SET pin = ? WHERE member_id = ?",
                         (new_hashed, session['member_id']))
        flash("PIN changed successfully!", "success")
        return redirect(url_for('dashboard'))

    # GET request – show form
    return render_template('change_pin.html')

@app.route('/upload-photo', methods=['GET', 'POST'])
def upload_photo():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        if 'photo' not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)

        file = request.files['photo']
        if file.filename == '':
            flash("No file selected.", "danger")
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash("File type not allowed. Please upload JPG, PNG, or GIF.", "danger")
            return redirect(request.url)

        # Secure the filename and save
        filename = secure_filename(f"member_{session['member_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg")
        os.makedirs(app.config['PHOTOS_PATH'], exist_ok=True)
        filepath = os.path.join(app.config['PHOTOS_PATH'], filename)
        file.save(filepath)

        # Update database
        db = DatabaseManager()
        db.execute_query("UPDATE members SET photo = ? WHERE id = ?", (filepath, session['member_id']))

        flash("Photo uploaded successfully!", "success")
        return redirect(url_for('profile'))

    # GET request – show upload form
    return render_template('upload_photo.html')

@app.route('/prayer', methods=['GET', 'POST'])
def prayer():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    if request.method == 'POST':
        prayer_text = request.form.get('request', '').strip()
        is_public = 1 if request.form.get('is_public') else 0
        if prayer_text:
            db.execute_query("""
                INSERT INTO prayer_requests (member_id, request, is_public)
                VALUES (?, ?, ?)
            """, (session['member_id'], prayer_text, is_public))
            flash("Your prayer request has been submitted.", "success")
        else:
            flash("Please enter your prayer request.", "danger")
        return redirect(url_for('prayer'))

    # GET: show form and list public requests
    public_requests = db.fetch_all("""
        SELECT p.id, p.request, p.created_at, m.full_name
        FROM prayer_requests p
        LEFT JOIN members m ON p.member_id = m.id
        WHERE p.is_public = 1
        ORDER BY p.created_at DESC
    """)
    requests_list = []
    for r in public_requests:
        # r[2] is 'YYYY-MM-DD HH:MM:SS'
        date_part = r[2][:10]   # YYYY-MM-DD
        time_part = r[2][11:16]  # HH:MM (first 5 chars of time)
        requests_list.append({
            'id': r[0],
            'request': r[1],
            'date': date_part,
            'time': time_part,
            'member': r[3] or 'Anonymous'
        })

    return render_template('prayer.html', requests=requests_list)

@app.template_filter('datetime')
def format_datetime(value, format='%b %d, %Y · %I:%M %p'):
    from datetime import datetime
    if value is None:
        return ""
    dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    return dt.strftime(format)

@app.route('/events')
def events():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    today = datetime.now().strftime('%Y-%m-%d')

    # Fetch upcoming events – now including the time column
    rows = db.fetch_all("""
        SELECT id, name as title, description, date as event_date, time, location, capacity
        FROM events
        WHERE date >= ?
        ORDER BY date ASC
    """, (today,))

    print(f"DEBUG: Found {len(rows)} upcoming events")
    if rows:
        print(f"DEBUG: First event: {rows[0]}")

    registered_ids = set()
    if rows:
        reg_rows = db.fetch_all("""
            SELECT event_id FROM event_registrations WHERE member_id = ?
        """, (session['member_id'],))
        registered_ids = {r[0] for r in reg_rows}

    events_list = []
    for r in rows:
        events_list.append({
            'id': r[0],
            'title': r[1],
            'description': r[2],
            'date': r[3],
            'time': r[4] or 'TBA',          # use actual time, fallback to TBA
            'location': r[5] or 'TBA',
            'capacity': r[6],
            'registered': r[0] in registered_ids
        })

    return render_template('events.html', events=events_list)

@app.route('/events/register/<int:event_id>')
def register_event(event_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    # FIXED: Use 'date' column, alias as 'event_date'
    event = db.fetch_one("""
        SELECT id, name as title, date as event_date, capacity,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = ?) as current_count
        FROM events WHERE id = ?
    """, (event_id, event_id))
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events'))

    # Check capacity
    if event[3] and event[4] >= event[3]:
        flash("Sorry, this event is full.", "warning")
        return redirect(url_for('events'))

    # Check if already registered
    existing = db.fetch_one("SELECT id FROM event_registrations WHERE event_id = ? AND member_id = ?",
                            (event_id, session['member_id']))
    if existing:
        flash("You are already registered for this event.", "info")
    else:
        db.execute_query("INSERT INTO event_registrations (event_id, member_id) VALUES (?, ?)",
                         (event_id, session['member_id']))
        flash(f"Successfully registered for {event[1]}!", "success")

    return redirect(url_for('events'))

@app.route('/events/cancel/<int:event_id>')
def cancel_registration(event_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    db.execute_query("DELETE FROM event_registrations WHERE event_id = ? AND member_id = ?",
                     (event_id, session['member_id']))
    flash("Registration cancelled.", "success")
    return redirect(url_for('events'))

@app.route('/family')
def family():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    # Get linked family members (approved relationships)
    linked = db.fetch_all("""
        SELECT m.id, m.full_name, fl.relationship
        FROM family_links fl
        JOIN members m ON (fl.member2_id = m.id AND fl.member1_id = ?) OR (fl.member1_id = m.id AND fl.member2_id = ?)
        WHERE fl.status = 'approved'
    """, (session['member_id'], session['member_id']))

    # Get pending requests sent to me
    pending_incoming = db.fetch_all("""
        SELECT fr.id, m.full_name, fr.relationship
        FROM family_link_requests fr
        JOIN members m ON fr.requester_id = m.id
        WHERE fr.target_member_id = ? AND fr.status = 'pending'
    """, (session['member_id'],))

    # Get pending requests I sent
    pending_outgoing = db.fetch_all("""
        SELECT fr.id, m.full_name, fr.relationship
        FROM family_link_requests fr
        JOIN members m ON fr.target_member_id = m.id
        WHERE fr.requester_id = ? AND fr.status = 'pending'
    """, (session['member_id'],))

    return render_template('family.html',
                           linked=linked,
                           incoming=pending_incoming,
                           outgoing=pending_outgoing)

@app.route('/family/add', methods=['GET', 'POST'])
def family_add():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        target_member_id = request.form.get('target_member_id', '').strip()
        relationship = request.form.get('relationship', '').strip()

        if not target_member_id or not relationship:
            flash("Please enter a Member ID and relationship.", "danger")
            return redirect(url_for('family_add'))

        # Find member by member_id (displayed ID)
        db = DatabaseManager()
        target = db.fetch_one("SELECT id FROM members WHERE member_id = ?", (target_member_id,))
        if not target:
            flash("No member found with that Member ID.", "danger")
            return redirect(url_for('family_add'))

        if target[0] == session['member_id']:
            flash("You cannot link to yourself.", "danger")
            return redirect(url_for('family_add'))

        # Check if already linked or request pending
        existing = db.fetch_one("""
            SELECT id FROM family_links
            WHERE (member1_id = ? AND member2_id = ?) OR (member1_id = ? AND member2_id = ?)
        """, (session['member_id'], target[0], target[0], session['member_id']))
        if existing:
            flash("You are already linked with this member.", "info")
            return redirect(url_for('family'))

        pending = db.fetch_one("""
            SELECT id FROM family_link_requests
            WHERE (requester_id = ? AND target_member_id = ?) OR (requester_id = ? AND target_member_id = ?)
        """, (session['member_id'], target[0], target[0], session['member_id']))
        if pending:
            flash("A request already exists.", "info")
            return redirect(url_for('family'))

        # Create new request
        db.execute_query("""
            INSERT INTO family_link_requests (requester_id, target_member_id, relationship)
            VALUES (?, ?, ?)
        """, (session['member_id'], target[0], relationship))

        flash("Family link request sent. It will be visible after approval.", "success")
        return redirect(url_for('family'))

    # GET: show form
    return render_template('family_add.html')

@app.route('/family/approve/<int:request_id>')
def family_approve(request_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    # Verify this request is for me
    req = db.fetch_one("""
        SELECT requester_id, target_member_id, relationship
        FROM family_link_requests
        WHERE id = ? AND target_member_id = ? AND status = 'pending'
    """, (request_id, session['member_id']))
    if not req:
        flash("Request not found or already processed.", "danger")
        return redirect(url_for('family'))

    # Insert into family_links (bidirectional)
    db.execute_query("""
        INSERT INTO family_links (member1_id, member2_id, relationship, status)
        VALUES (?, ?, ?, 'approved')
    """, (req[0], req[1], req[2]))
    # Also the reverse? Actually relationship is stored once; we can assume symmetric if needed.
    # For simplicity, we store one direction. When displaying, we treat both directions.

    # Delete the request
    db.execute_query("DELETE FROM family_link_requests WHERE id = ?", (request_id,))

    flash("Family link approved!", "success")
    return redirect(url_for('family'))

@app.route('/family/reject/<int:request_id>')
def family_reject(request_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    db.execute_query("DELETE FROM family_link_requests WHERE id = ? AND target_member_id = ?",
                     (request_id, session['member_id']))
    flash("Request rejected.", "success")
    return redirect(url_for('family'))

@app.route('/member_photos/<filename>')
def member_photo(filename):
    """Serve member photos from the photos directory."""
    return send_from_directory(app.config['PHOTOS_PATH'], filename)


@app.route('/resources')
def resource_library():
    if 'member_id' not in session:
        return redirect(url_for('home'))
    
    db = DatabaseManager()
    
    # Debug: check if table exists and has data
    try:
        # Test query
        test = db.fetch_one("SELECT COUNT(*) FROM resources")
        print(f"DEBUG: resources table count = {test[0] if test else 0}")
    except Exception as e:
        print(f"DEBUG: resources table error: {e}")
    
    # Get filter parameters
    category = request.args.get('category', '')
    search = request.args.get('search', '')
    
    # Build query
    query = "SELECT id, title, description, category, filename, file_size, file_type, download_count, created_at FROM resources"
    params = []
    conditions = []
    
    if category and category != 'All':
        conditions.append("category = ?")
        params.append(category)
    
    if search:
        conditions.append("(title LIKE ? OR description LIKE ?)")
        params.extend([f'%{search}%', f'%{search}%'])
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC"
    
    resources = db.fetch_all(query, params)
    print(f"DEBUG: found {len(resources)} resources")
    
    # Get categories for filter
    categories = db.fetch_all("SELECT DISTINCT category FROM resources WHERE category IS NOT NULL ORDER BY category")
    category_list = [c[0] for c in categories]
    
    # Convert to list of dicts
    resource_list = []
    for r in resources:
        resource_list.append({
            'id': r[0],
            'title': r[1],
            'description': r[2],
            'category': r[3],
            'filename': r[4],
            'file_size': r[5],
            'file_type': r[6],
            'download_count': r[7],
            'created_at': r[8]
        })
    
    return render_template('resources.html',
                          resources=resource_list,
                          categories=['All'] + category_list,
                          current_category=category,
                          search=search)

@app.route('/resources/download/<int:resource_id>')
def download_resource(resource_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    resource = db.fetch_one("SELECT filename, file_path FROM resources WHERE id = ?", (resource_id,))
    if not resource:
        abort(404)

    # Increment download count
    db.execute_query("UPDATE resources SET download_count = download_count + 1 WHERE id = ?", (resource_id,))

    # Send the file from the upload folder
    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        resource[1],               # stored filename (with timestamp)
        as_attachment=True,
        download_name=resource[0]   # original filename
    )

@app.route('/blog')
def blog_list():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    posts = db.fetch_all("""
        SELECT id, title, content, author, category, published_at
        FROM blog_posts
        WHERE is_published = 1
        ORDER BY published_at DESC
    """)

    post_list = []
    for p in posts:
        post_list.append({
            'id': p[0],
            'title': p[1],
            'content': p[2][:200] + "..." if len(p[2]) > 200 else p[2],
            'author': p[3] or 'Admin',
            'category': p[4] or 'Uncategorized',
            'published': p[5]
        })

    return render_template('blog_list.html', posts=post_list)

@app.route('/blog/<int:post_id>')
def blog_detail(post_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    post = db.fetch_one("""
        SELECT title, content, author, category, published_at
        FROM blog_posts
        WHERE id = ? AND is_published = 1
    """, (post_id,))

    if not post:
        abort(404)

    post_dict = {
        'title': post[0],
        'content': post[1],
        'author': post[2] or 'Admin',
        'category': post[3] or 'Uncategorized',
        'published': post[4]
    }
    return render_template('blog_detail.html', post=post_dict)

@app.route('/directory')
def directory():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    rows = db.fetch_all("""
        SELECT full_name, phone, email
        FROM members
        WHERE directory_opt_in = 1
        ORDER BY full_name
    """)

    print("DEBUG: Directory rows =", rows)
    print("DEBUG: Number of rows =", len(rows))

    directory_list = []
    for r in rows:
        directory_list.append({
            'name': r[0],
            'phone': r[1] if r[1] else '—',
            'email': r[2] if r[2] else '—'
        })

    return render_template('directory.html', members=directory_list)

from flask import session, request, flash, redirect, url_for, render_template
from database import hash_password

# ... existing imports ...

@app.route('/forgot_pin', methods=['GET', 'POST'])
def forgot_pin():
    """Step 1: Enter Member ID to initiate PIN reset."""
    if request.method == 'POST':
        member_id_input = request.form.get('member_id', '').strip()
        if not member_id_input:
            flash("Please enter your Member ID.", "danger")
            return redirect(url_for('forgot_pin'))

        db = DatabaseManager()
        # Look up member by displayed member_id
        member = db.fetch_one("SELECT id FROM members WHERE member_id = ?", (member_id_input,))
        if not member:
            flash("Member ID not found.", "danger")
            return redirect(url_for('forgot_pin'))

        internal_id = member[0]
        # Check if security questions are set
        portal = db.fetch_one("SELECT security_question1, security_question2 FROM member_portal WHERE member_id = ?", (internal_id,))
        if not portal or not portal[0] or not portal[1]:
            flash("Security questions not set for this account. Please contact the church office.", "warning")
            return redirect(url_for('forgot_pin'))

        # Store member_id in session for next steps
        session['reset_member_id'] = internal_id
        return redirect(url_for('verify_questions'))

    return render_template('forgot_pin.html')

@app.route('/verify_questions', methods=['GET', 'POST'])
def verify_questions():
    """Step 2: Answer security questions."""
    if 'reset_member_id' not in session:
        flash("Session expired. Please start over.", "danger")
        return redirect(url_for('forgot_pin'))

    db = DatabaseManager()
    internal_id = session['reset_member_id']
    portal = db.fetch_one("SELECT security_question1, security_answer1, security_question2, security_answer2 FROM member_portal WHERE member_id = ?", (internal_id,))
    if not portal:
        flash("Error retrieving security questions.", "danger")
        return redirect(url_for('forgot_pin'))

    q1, ans1_hash, q2, ans2_hash = portal

    if request.method == 'POST':
        answer1 = request.form.get('answer1', '').strip()
        answer2 = request.form.get('answer2', '').strip()
        if not answer1 or not answer2:
            flash("Please answer both questions.", "danger")
            return render_template('verify_questions.html', q1=q1, q2=q2)

        # Verify hashed answers
        if hash_password(answer1) == ans1_hash and hash_password(answer2) == ans2_hash:
            # Correct – allow reset
            session['verified'] = True
            return redirect(url_for('set_new_pin'))
        else:
            flash("Incorrect answers. Please try again.", "danger")
            return render_template('verify_questions.html', q1=q1, q2=q2)

    return render_template('verify_questions.html', q1=q1, q2=q2)

@app.route('/set_new_pin', methods=['GET', 'POST'])
def set_new_pin():
    """Step 3: Set a new 4-digit PIN."""
    if 'reset_member_id' not in session or not session.get('verified'):
        flash("Session expired or not verified. Please start over.", "danger")
        return redirect(url_for('forgot_pin'))

    if request.method == 'POST':
        new_pin = request.form.get('new_pin', '').strip()
        confirm_pin = request.form.get('confirm_pin', '').strip()

        if not new_pin or not confirm_pin:
            flash("Please enter and confirm your new PIN.", "danger")
            return render_template('set_new_pin.html')

        if not re.match(r'^\d{4}$', new_pin):
            flash("PIN must be exactly 4 digits.", "danger")
            return render_template('set_new_pin.html')

        if new_pin != confirm_pin:
            flash("PINs do not match.", "danger")
            return render_template('set_new_pin.html')

        # Update PIN
        db = DatabaseManager()
        new_hashed = hash_password(new_pin)
        db.execute_query("UPDATE member_portal SET pin = ? WHERE member_id = ?",
                         (new_hashed, session['reset_member_id']))

        # Clear session variables
        session.pop('reset_member_id', None)
        session.pop('verified', None)

        flash("Your PIN has been reset successfully. Please log in with your new PIN.", "success")
        return redirect(url_for('home'))

    return render_template('set_new_pin.html')

@app.route('/volunteer')
def volunteer_list():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    try:
        db = DatabaseManager()
        today = datetime.now().strftime('%Y-%m-%d')

        # Fetch active upcoming opportunities
        rows = db.fetch_all("""
            SELECT id, title, role, description, date, start_time, end_time, location, capacity,
                   (SELECT COUNT(*) FROM volunteer_signups WHERE opportunity_id = v.id) as registered
            FROM volunteer_opportunities v
            WHERE date >= ? AND status = 'active'
            ORDER BY date, start_time
        """, (today,))

        # Get signups for the current member
        signed_up_ids = set()
        if rows:
            signup_rows = db.fetch_all("SELECT opportunity_id FROM volunteer_signups WHERE member_id = ?", (session['member_id'],))
            signed_up_ids = {r[0] for r in signup_rows}

        opp_list = []
        for r in rows:
            opp_list.append({
                'id': r[0],
                'title': r[1],
                'role': r[2] or '',
                'description': r[3] or '',
                'date': r[4],
                'start_time': r[5] or '',
                'end_time': r[6] or '',
                'location': r[7] or '',
                'capacity': r[8],
                'registered_count': r[9],
                'signed_up': r[0] in signed_up_ids,
                'spots_left': (r[8] - r[9]) if r[8] else None
            })

        return render_template('volunteer.html', opportunities=opp_list)
    except Exception as e:
        # Handle exceptions
        flash(f"An error occurred while fetching opportunities: {str(e)}", "danger")
        return redirect(url_for('home'))

@app.route('/volunteer/signup/<int:opp_id>')
def volunteer_signup(opp_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    try:
        # Check if already signed up
        existing = db.fetch_one("SELECT id FROM volunteer_signups WHERE opportunity_id=? AND member_id=?", (opp_id, session['member_id']))
        if existing:
            flash("You are already signed up for this opportunity.", "info")
            return redirect(url_for('volunteer_list'))

        # Check capacity
        opp = db.fetch_one("SELECT capacity, (SELECT COUNT(*) FROM volunteer_signups WHERE opportunity_id=?) as registered FROM volunteer_opportunities WHERE id=?", (opp_id, opp_id))
        if not opp:
            flash("Opportunity not found.", "danger")
            return redirect(url_for('volunteer_list'))
        if opp[0] and opp[1] >= opp[0]:
            flash("This opportunity is full.", "warning")
            return redirect(url_for('volunteer_list'))

        # Sign up
        db.execute_query("INSERT INTO volunteer_signups (opportunity_id, member_id) VALUES (?, ?)", (opp_id, session['member_id']))
        flash("You have successfully signed up!", "success")
        return redirect(url_for('volunteer_list'))
    except Exception as e:
        flash(f"An error occurred during signup: {str(e)}", "danger")
        return redirect(url_for('volunteer_list'))

@app.route('/volunteer/cancel/<int:signup_id>')
def volunteer_cancel(signup_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    try:
        # Ensure the signup belongs to this member
        db.execute_query("DELETE FROM volunteer_signups WHERE id=? AND member_id=?", (signup_id, session['member_id']))
        flash("Your signup has been cancelled.", "success")
        return redirect(url_for('volunteer_list'))
    except Exception as e:
        flash(f"An error occurred while cancelling your signup: {str(e)}", "danger")
        return redirect(url_for('volunteer_list'))
    

@app.route('/my_committees')
def my_committees():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    member_id = session['member_id']
    db = DatabaseManager()

    # Get committees this member belongs to, including branch name
    committees = db.fetch_all("""
        SELECT c.id, c.name, c.description, cm.role, cm.joined_date,
               (SELECT COUNT(*) FROM committee_members WHERE committee_id = c.id) as total_members,
               COALESCE(b.name, '') as branch_name
        FROM committee_members cm
        JOIN committees c ON cm.committee_id = c.id
        LEFT JOIN branches b ON c.branch_id = b.id
        WHERE cm.member_id = ?
        ORDER BY c.name
    """, (member_id,))

    committee_list = []
    for c in committees:
        cid, name, description, role, joined, total_members, branch_name = c
        # Get upcoming meetings (next 3)
        meetings = db.fetch_all("""
            SELECT meeting_date, agenda, location
            FROM committee_meetings
            WHERE committee_id = ? AND meeting_date >= date('now')
            ORDER BY meeting_date
            LIMIT 3
        """, (cid,))
        # Get recent activities
        activities = db.fetch_all("""
            SELECT name, start_date, end_date, status
            FROM committee_activities
            WHERE committee_id = ?
            ORDER BY start_date DESC
            LIMIT 3
        """, (cid,))
        committee_list.append({
            'id': cid,
            'name': name,
            'description': description or '',
            'role': role,
            'joined': joined,
            'total_members': total_members,
            'branch': branch_name if branch_name else 'All branches',
            'meetings': [{'date': m[0], 'agenda': m[1], 'location': m[2]} for m in meetings],
            'activities': [{'name': a[0], 'start': a[1], 'end': a[2], 'status': a[3]} for a in activities]
        })

    return render_template('my_committees.html', committees=committee_list)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)