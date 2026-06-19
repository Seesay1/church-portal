import os
import re
import secrets
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

# Load environment variables before importing modules that read them at import time.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, abort
from werkzeug.utils import secure_filename
from database import DatabaseManager, hash_password, password_needs_upgrade, verify_password, setup_database
import config


# Configure logging (suppress werkzeug verbose logs)
import sys
import logging
logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

app = Flask(__name__)
if not config.SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set before starting the Flask app.")
app.secret_key = config.SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = config.SESSION_COOKIE_HTTPONLY
app.config["SESSION_COOKIE_SECURE"] = config.SESSION_COOKIE_SECURE
app.config["SESSION_COOKIE_SAMESITE"] = config.SESSION_COOKIE_SAMESITE
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=config.SESSION_LIFETIME_MINUTES)
logger = logging.getLogger(__name__)

# Ensure PostgreSQL schema exists before requests hit the app in WSGI/production.
setup_database()

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
# Photo uploads
app.config['PHOTOS_PATH'] = os.path.join(os.path.dirname(__file__), 'photos')
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Resource uploads
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads/resources')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB for resources
ALLOWED_RESOURCE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'docx', 'mp3', 'mp4', 'pptx', 'xlsx'}

# Ensure upload directories exist
os.makedirs(app.config['PHOTOS_PATH'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# -------------------------------------------------------------------
# Helper functions
# -------------------------------------------------------------------
def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def get_csrf_token():
    token = session.get('_csrf_token')
    if not token:
        token = secrets.token_urlsafe(32)
        session['_csrf_token'] = token
    return token

@app.before_request
def protect_against_csrf():
    # Logout is intentionally exempt so legacy links and buttons can still sign out cleanly.
    if request.path == '/logout' or request.endpoint == 'logout':
        return
    if request.method == 'POST':
        sent_token = request.form.get('csrf_token', '') or request.headers.get('X-CSRFToken', '') or request.headers.get('X-CSRF-Token', '')
        session_token = session.get('_csrf_token', '')
        if not sent_token or not session_token or not secrets.compare_digest(sent_token, session_token):
            abort(400, description="Invalid or missing CSRF token.")

@app.template_filter('date_format')
def format_datetime(value, format='%Y-%m-%d'):
    return '' if value is None else value.strftime(format)

def get_member_by_id(member_id):
    """Fetch member details by internal ID."""
    db = DatabaseManager()
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
        WHERE m.id = %s
    """, (member_id,))

    if not row:
        return None

    baptism_date = row[11]
    date_joined = row[12]
    baptism_date_str = baptism_date.strftime("%Y-%m-%d") if baptism_date else None
    date_joined_str = date_joined.strftime("%Y-%m-%d") if date_joined else None

    return {
        "id": row[0],
        "member_id": row[1],
        "full_name": row[2],
        "gender": row[3],
        "phone": row[4],
        "email": row[5],
        "address": row[6],
        "occupation": row[7],
        "marital_status": row[8],
        "parent_name": row[9],
        "school_class": row[10],
        "baptism_date": baptism_date_str,
        "date_joined": date_joined_str,
        "branch_name": row[13],
        "group_name": row[14],
        "dept_name": row[15],
        "photo": row[16]
    }

def get_total_contributions(member_id):
    db = DatabaseManager()
    row = db.fetch_one("SELECT SUM(amount) FROM financial_records WHERE member_id = %s", (member_id,))
    return row[0] if row and row[0] else 0

def get_attendance_count(member_id):
    db = DatabaseManager()
    row = db.fetch_one("SELECT COUNT(*) FROM attendance WHERE member_id = %s AND present = 1", (member_id,))
    return row[0] if row else 0

# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

# -------------------------------------------------------------------
# Authentication Routes
# -------------------------------------------------------------------
@app.context_processor
def inject_church_name():
    from flask import session
    db = DatabaseManager()
    try:
        row = db.fetch_one("SELECT value FROM settings WHERE key='church_name'")
        church_name = row[0] if row else "Your Church"
    except Exception as e:
        logger.warning(f"Could not fetch church name: {e}")
        church_name = "Your Church"
    
    # Get current member info if logged in
    member_info = None
    member_photo = None
    if 'member_id' in session:
        try:
            member_info = get_member_by_id(session['member_id'])
            if member_info and member_info.get('photo'):
                member_photo = member_info['photo']
        except Exception as e:
            logger.warning(f"Could not fetch member info: {e}")
    
    return dict(
        church_name=church_name,
        member_info=member_info,
        member_photo=member_photo,
        csrf_token=get_csrf_token
    )

@app.route('/')
def home():
    try:
        if 'member_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('login.html')
    except Exception as e:
        logging.exception("Error in home route")
        return "Internal Server Error", 500

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact form page - sends email to church office."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        message = request.form.get('message', '').strip()
        
        if not name or not email or not message:
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for('contact'))
        
        # Check if contact form is enabled
        if not getattr(config, 'CONTACT_FORM_ENABLED', False):
            flash("Contact form is currently disabled.", "danger")
            return redirect(url_for('contact'))
        if not all([config.SMTP_HOST, config.SMTP_USERNAME, config.SMTP_PASSWORD, config.CONTACT_FORM_RECIPIENT]):
            flash("Contact form email is not configured.", "danger")
            return redirect(url_for('contact'))
        
        try:
            # Build email content
            subject = f"{config.CONTACT_FORM_SUBJECT} - From: {name}"
            
            body_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2 style="color: #667eea;">New Contact Form Submission</h2>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Phone:</strong> {phone if phone else 'Not provided'}</p>
                <hr>
                <h3>Message:</h3>
                <p style="background: #f8f9fa; padding: 15px; border-radius: 8px;">{message}</p>
                <hr>
                <p style="color: #666; font-size: 12px;">This email was sent from the PCG Mt. Zion Congregation website contact form.</p>
            </body>
            </html>
            """
            
            body_text = f"""
            New Contact Form Submission
            
            Name: {name}
            Email: {email}
            Phone: {phone if phone else 'Not provided'}
            
            Message:
            {message}
            
            ---
            This email was sent from the PCG Mt. Zion Congregation website contact form.
            """
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['From'] = config.SMTP_USERNAME
            msg['To'] = config.CONTACT_FORM_RECIPIENT
            msg['Subject'] = subject
            
            # Attach both plain text and HTML versions
            part1 = MIMEText(body_text, 'plain')
            part2 = MIMEText(body_html, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Create secure SSL context
            context = ssl.create_default_context()
            
            # Connect to SMTP server and send
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
                if config.SMTP_USE_TLS:
                    server.starttls(context=context)
                server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                server.sendmail(config.SMTP_USERNAME, config.CONTACT_FORM_RECIPIENT, msg.as_string())
            
            flash("Your message has been sent! We'll get back to you soon.", "success")
            return redirect(url_for('contact'))
            
        except Exception as e:
            logging.exception("Error sending contact form email")
            flash(f"Failed to send message. Please try again later or contact us directly at {config.CONTACT_FORM_RECIPIENT}", "danger")
            return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/login', methods=['POST'])
def login():
    member_id_input = request.form.get('member_id', '').strip()
    pin_input = request.form.get('pin', '').strip()

    if not member_id_input or not pin_input:
        flash("Please enter both Member ID and PIN.", "danger")
        return redirect(url_for('home'))

    db = DatabaseManager()
    member = db.fetch_one("SELECT id FROM members WHERE member_id = %s", (member_id_input,))
    if not member:
        flash("Invalid Member ID or PIN.", "danger")
        return redirect(url_for('home'))

    internal_id = member[0]
    portal = db.fetch_one("SELECT pin FROM member_portal WHERE member_id = %s", (internal_id,))
    if not portal:
        flash("No PIN set for this member. Please contact the church office.", "warning")
        return redirect(url_for('home'))

    if verify_password(pin_input, portal[0]):
        if password_needs_upgrade(portal[0]):
            db.execute_query("UPDATE member_portal SET pin = %s WHERE member_id = %s",
                             (hash_password(pin_input), internal_id))
        session['member_id'] = internal_id
        session.permanent = True
        session['member_name'] = get_member_by_id(internal_id)['full_name']
        db.execute_query("UPDATE member_portal SET last_login = %s WHERE member_id = %s",
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

    family_linked = db.fetch_one("SELECT COUNT(*) FROM family_links WHERE member1_id=%s OR member2_id=%s", (member_id, member_id))
    family_count = family_linked[0] if family_linked else 0

    pending = db.fetch_one("SELECT COUNT(*) FROM family_link_requests WHERE target_member_id=%s AND status='pending'", (member_id,))
    pending_family = pending[0] if pending else 0

    fields = [member.get('phone'), member.get('email'), member.get('address')]
    filled = sum(bool(f and f.strip()) for f in fields)
    profile_completion = int((filled / 3) * 100)

    last_att = db.fetch_one("SELECT date FROM attendance WHERE member_id=%s AND present=1 ORDER BY date DESC LIMIT 1", (member_id,))
    last_attendance_date = last_att[0].strftime('%Y-%m-%d') if last_att else 'N/A'

    prayers = db.fetch_all("SELECT request, created_at FROM prayer_requests WHERE member_id=%s ORDER BY created_at DESC LIMIT 3", (member_id,))
    recent_prayers = [{'request': r[0], 'created_at': r[1].strftime('%Y-%m-%d') if r[1] else ''} for r in prayers]

    next_ev = db.fetch_one("SELECT date FROM events WHERE date >= CURRENT_DATE ORDER BY date ASC LIMIT 1")
    next_event_date = next_ev[0].strftime('%Y-%m-%d') if next_ev else 'None'

    contribs = db.fetch_all("SELECT date, description, amount FROM financial_records WHERE member_id=%s ORDER BY date DESC LIMIT 5", (member_id,))
    recent_contributions = [{'date': c[0].strftime('%Y-%m-%d') if c[0] else '', 'description': c[1], 'amount': c[2]} for c in contribs]

    upcoming_events_raw = db.fetch_all("SELECT id, name as title, date, 'TBA' as time FROM events WHERE date >= CURRENT_DATE ORDER BY date ASC LIMIT 3")
    
    # Get registered events for current member
    registered_event_ids = set()
    reg_rows = db.fetch_all("SELECT event_id FROM event_registrations WHERE member_id = %s", (member_id,))
    registered_event_ids = {r[0] for r in reg_rows}
    
    upcoming_events = [{'id': e[0], 'title': e[1], 'date': e[2].strftime('%Y-%m-%d') if e[2] else '', 'time': e[3], 'registered': e[0] in registered_event_ids} for e in upcoming_events_raw]

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
    total_contrib = get_total_contributions(session['member_id'])
    attendance_count = get_attendance_count(session['member_id'])

    db = DatabaseManager()
    family_linked = db.fetch_one("SELECT COUNT(*) FROM family_links WHERE member1_id=%s OR member2_id=%s", (session['member_id'], session['member_id']))
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
        directory_opt_in = 1 if request.form.get('directory_opt_in') else 0

        if email and '@' not in email:
            flash("Please enter a valid email address.", "danger")
            return redirect(url_for('profile_edit'))

        db = DatabaseManager()
        db.execute_query("""
            UPDATE members SET
                phone = %s, email = %s, address = %s, occupation = %s,
                marital_status = %s, parent_name = %s, school_class = %s,
                directory_opt_in = %s
            WHERE id = %s
        """, (phone, email, address, occupation, marital_status,
              parent_name, school_class, directory_opt_in, session['member_id']))

        flash("Your profile has been updated successfully.", "success")
        return redirect(url_for('profile'))

    member = get_member_by_id(session['member_id'])
    return render_template('profile_edit.html', member=member)

# -------------------------------------------------------------------
# Member Activity Routes
# -------------------------------------------------------------------

@app.route('/contributions')
def contributions():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    rows = db.fetch_all("""
        SELECT date, description, amount
        FROM financial_records
        WHERE member_id = %s
        ORDER BY date DESC
    """, (session['member_id'],))

    contributions = [{"date": r[0].strftime('%Y-%m-%d') if r[0] else '', "description": r[1] or "Offering", "amount": r[2]} for r in rows]
    return render_template('contributions.html', contributions=contributions)

@app.route('/attendance')
def attendance():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    rows = db.fetch_all("""
        SELECT date
        FROM attendance
        WHERE member_id = %s AND present = 1
        ORDER BY date DESC
    """, (session['member_id'],))

    attendance_date_objs = [r[0] for r in rows if r[0]]
    attendance_dates = [d.strftime('%Y-%m-%d') for d in attendance_date_objs]

    def calculate_streak(dates):
        if not dates:
            return 0
        sorted_dates = sorted(dates, reverse=True)
        streak = 1
        current = sorted_dates[0]
        for next_date in sorted_dates[1:]:
            if (current - next_date).days == 1:
                streak += 1
                current = next_date
            else:
                break
        return streak

    def count_this_month(dates):
        today = date.today()
        return sum(1 for d in dates if d.year == today.year and d.month == today.month)

    streak = calculate_streak(attendance_date_objs)
    this_month = count_this_month(attendance_date_objs)

    return render_template(
        'attendance.html',
        attendance_dates=attendance_dates,
        streak=streak,
        this_month=this_month
    )

# -------------------------------------------------------------------
# Profile Management Routes
# -------------------------------------------------------------------

@app.route('/logout', methods=['GET', 'POST'])
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
        row = db.fetch_one("SELECT pin FROM member_portal WHERE member_id = %s", (session['member_id'],))
        if not row:
            flash("PIN record not found. Contact admin.", "danger")
            return redirect(url_for('dashboard'))

        if not verify_password(current_pin, row[0]):
            flash("Current PIN is incorrect.", "danger")
            return redirect(url_for('change_pin'))

        new_hashed = hash_password(new_pin)
        db.execute_query("UPDATE member_portal SET pin = %s WHERE member_id = %s",
                         (new_hashed, session['member_id']))
        flash("PIN changed successfully!", "success")
        return redirect(url_for('dashboard'))

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

        if not allowed_file(file.filename, ALLOWED_PHOTO_EXTENSIONS):
            flash("File type not allowed. Please upload JPG, PNG, or GIF.", "danger")
            return redirect(request.url)

        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)
        if file_size > 2 * 1024 * 1024:
            flash("Photo is too large. Maximum size is 2 MB.", "danger")
            return redirect(request.url)

        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"member_{session['member_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}")
        filepath = os.path.join(app.config['PHOTOS_PATH'], filename)
        file.save(filepath)

        db = DatabaseManager()
        db.execute_query("UPDATE members SET photo = %s WHERE id = %s", (filepath, session['member_id']))

        flash("Photo uploaded successfully!", "success")
        return redirect(url_for('profile'))

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
                VALUES (%s, %s, %s)
            """, (session['member_id'], prayer_text, is_public))
            flash("Your prayer request has been submitted.", "success")
        else:
            flash("Please enter your prayer request.", "danger")
        return redirect(url_for('prayer'))

    public_requests = db.fetch_all("""
        SELECT p.id, p.request, p.created_at, m.full_name
        FROM prayer_requests p
        LEFT JOIN members m ON p.member_id = m.id
        WHERE p.is_public = 1
        ORDER BY p.created_at DESC
    """)
    requests_list = []
    for r in public_requests:
        created = r[2]
        date_part = created.strftime('%Y-%m-%d') if created else ''
        time_part = created.strftime('%H:%M') if created else ''
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
    return "" if value is None else value.strftime(format)

@app.route('/events')
def events():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    today = datetime.now().strftime('%Y-%m-%d')
    rows = db.fetch_all("""
        SELECT id, name as title, description, date as event_date, time, location, capacity
        FROM events
        WHERE date >= %s
        ORDER BY date ASC
    """, (today,))

    registered_ids = set()
    if rows:
        reg_rows = db.fetch_all("""
            SELECT event_id FROM event_registrations WHERE member_id = %s
        """, (session['member_id'],))
        registered_ids = {r[0] for r in reg_rows}

    events_list = [{
        'id': r[0],
        'title': r[1],
        'description': r[2],
        'date': r[3].strftime('%Y-%m-%d') if r[3] else '',
        'time': r[4] or 'TBA',
        'location': r[5] or 'TBA',
        'capacity': r[6],
        'registered': r[0] in registered_ids
    } for r in rows]

    return render_template('events.html', events=events_list)

@app.route('/events/register/<int:event_id>', methods=['POST'])
def register_event(event_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    event = db.fetch_one("""
        SELECT id, name as title, date as event_date, capacity,
               (SELECT COUNT(*) FROM event_registrations WHERE event_id = %s) as current_count
        FROM events WHERE id = %s
    """, (event_id, event_id))
    if not event:
        flash("Event not found.", "danger")
        return redirect(url_for('events'))

    if event[3] and event[4] >= event[3]:
        flash("Sorry, this event is full.", "warning")
        return redirect(url_for('events'))

    if existing := db.fetch_one("SELECT id FROM event_registrations WHERE event_id = %s AND member_id = %s",
                            (event_id, session['member_id'])):
        flash("You are already registered for this event.", "info")
    else:
        db.execute_query("INSERT INTO event_registrations (event_id, member_id) VALUES (%s, %s)",
                         (event_id, session['member_id']))
        flash(f"Successfully registered for {event[1]}!", "success")

    return redirect(url_for('events'))

@app.route('/events/cancel/<int:event_id>', methods=['POST'])
def cancel_registration(event_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    db.execute_query("DELETE FROM event_registrations WHERE event_id = %s AND member_id = %s",
                     (event_id, session['member_id']))
    flash("Registration cancelled.", "success")
    return redirect(url_for('events'))

# -------------------------------------------------------------------
# Family Management Routes
# -------------------------------------------------------------------

@app.route('/family')
def family():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    linked = db.fetch_all("""
        SELECT m.id, m.full_name, fl.relationship
        FROM family_links fl
        JOIN members m ON (fl.member2_id = m.id AND fl.member1_id = %s) OR (fl.member1_id = m.id AND fl.member2_id = %s)
        WHERE fl.status = 'approved'
    """, (session['member_id'], session['member_id']))

    pending_incoming = db.fetch_all("""
        SELECT fr.id, m.full_name, fr.relationship
        FROM family_link_requests fr
        JOIN members m ON fr.requester_id = m.id
        WHERE fr.target_member_id = %s AND fr.status = 'pending'
    """, (session['member_id'],))

    pending_outgoing = db.fetch_all("""
        SELECT fr.id, m.full_name, fr.relationship
        FROM family_link_requests fr
        JOIN members m ON fr.target_member_id = m.id
        WHERE fr.requester_id = %s AND fr.status = 'pending'
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

        db = DatabaseManager()
        target = db.fetch_one("SELECT id FROM members WHERE member_id = %s", (target_member_id,))
        if not target:
            flash("No member found with that Member ID.", "danger")
            return redirect(url_for('family_add'))

        if target[0] == session['member_id']:
            flash("You cannot link to yourself.", "danger")
            return redirect(url_for('family_add'))

        if existing := db.fetch_one("""
            SELECT id FROM family_links
            WHERE (member1_id = %s AND member2_id = %s) OR (member1_id = %s AND member2_id = %s)
        """, (session['member_id'], target[0], target[0], session['member_id'])):
            flash("You are already linked with this member.", "info")
            return redirect(url_for('family'))

        if pending := db.fetch_one("""
            SELECT id FROM family_link_requests
            WHERE (requester_id = %s AND target_member_id = %s) OR (requester_id = %s AND target_member_id = %s)
        """, (session['member_id'], target[0], target[0], session['member_id'])):
            flash("A request already exists.", "info")
            return redirect(url_for('family'))

        db.execute_query("""
            INSERT INTO family_link_requests (requester_id, target_member_id, relationship)
            VALUES (%s, %s, %s)
        """, (session['member_id'], target[0], relationship))

        flash("Family link request sent. It will be visible after approval.", "success")
        return redirect(url_for('family'))

    return render_template('family_add.html')

@app.route('/family/approve/<int:request_id>', methods=['POST'])
def family_approve(request_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    req = db.fetch_one("""
        SELECT requester_id, target_member_id, relationship
        FROM family_link_requests
        WHERE id = %s AND target_member_id = %s AND status = 'pending'
    """, (request_id, session['member_id']))
    if not req:
        flash("Request not found or already processed.", "danger")
        return redirect(url_for('family'))

    db.execute_query("""
        INSERT INTO family_links (member1_id, member2_id, relationship, status)
        VALUES (%s, %s, %s, 'approved')
    """, (req[0], req[1], req[2]))
    db.execute_query("DELETE FROM family_link_requests WHERE id = %s", (request_id,))

    flash("Family link approved!", "success")
    return redirect(url_for('family'))

@app.route('/family/reject/<int:request_id>', methods=['POST'])
def family_reject(request_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    db.execute_query("DELETE FROM family_link_requests WHERE id = %s AND target_member_id = %s",
                     (request_id, session['member_id']))
    flash("Request rejected.", "success")
    return redirect(url_for('family'))

@app.route('/member_photos/<filename>')
def member_photo(filename):
    return send_from_directory(app.config['PHOTOS_PATH'], filename)

# -------------------------------------------------------------------
# Resource & Content Routes
# -------------------------------------------------------------------

@app.route('/resources')
def resource_library():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    try:
        test = db.fetch_one("SELECT COUNT(*) FROM resources")
        logger.debug("resources table count = %s", test[0] if test else 0)
    except Exception as e:
        logger.exception("resources table check failed")

    category = request.args.get('category', '')
    search = request.args.get('search', '')

    query = "SELECT id, title, description, category, filename, file_size, file_type, download_count, created_at FROM resources"
    params = []
    conditions = []

    if category and category != 'All':
        conditions.append("category = %s")
        params.append(category)

    if search:
        conditions.append("(title ILIKE %s OR description ILIKE %s)")
        params.extend([f'%{search}%', f'%{search}%'])

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC"

    resources = db.fetch_all(query, params)
    categories = db.fetch_all("SELECT DISTINCT category FROM resources WHERE category IS NOT NULL ORDER BY category")
    category_list = [c[0] for c in categories]

    resource_list = [{
        'id': r[0],
        'title': r[1],
        'description': r[2],
        'category': r[3],
        'filename': r[4],
        'file_size': r[5],
        'file_type': r[6],
        'download_count': r[7],
        'created_at': r[8].strftime('%Y-%m-%d') if r[8] else ''
    } for r in resources]

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
    resource = db.fetch_one("SELECT filename, file_path FROM resources WHERE id = %s", (resource_id,))
    if not resource:
        abort(404)

    db.execute_query("UPDATE resources SET download_count = download_count + 1 WHERE id = %s", (resource_id,))

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        resource[1],
        as_attachment=True,
        download_name=resource[0]
    )

# -------------------------------------------------------------------
# Blog & News Routes
# -------------------------------------------------------------------

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

    post_list = [{
        'id': p[0],
        'title': p[1],
        'content': (p[2][:200] + "...") if len(p[2]) > 200 else p[2],
        'author': p[3] or 'Admin',
        'category': p[4] or 'Uncategorized',
        'published': p[5].strftime('%Y-%m-%d') if p[5] else ''
    } for p in posts]

    return render_template('blog_list.html', posts=post_list)

@app.route('/blog/<int:post_id>')
def blog_detail(post_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    post = db.fetch_one("""
        SELECT title, content, author, category, published_at
        FROM blog_posts
        WHERE id = %s AND is_published = 1
    """, (post_id,))

    if not post:
        abort(404)

    post_dict = {
        'title': post[0],
        'content': post[1],
        'author': post[2] or 'Admin',
        'category': post[3] or 'Uncategorized',
        'published': post[4].strftime('%Y-%m-%d') if post[4] else ''
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

    directory_list = [{
        'name': r[0],
        'phone': r[1] or '—',
        'email': r[2] or '—'
    } for r in rows]

    return render_template('directory.html', members=directory_list)

# -------------------------------------------------------------------
# Account Recovery Routes
# -------------------------------------------------------------------

@app.route('/forgot_pin', methods=['GET', 'POST'])
def forgot_pin():
    if request.method == 'POST':
        member_id_input = request.form.get('member_id', '').strip()
        if not member_id_input:
            flash("Please enter your Member ID.", "danger")
            return redirect(url_for('forgot_pin'))

        db = DatabaseManager()
        member = db.fetch_one("SELECT id FROM members WHERE member_id = %s", (member_id_input,))
        if not member:
            flash("Member ID not found.", "danger")
            return redirect(url_for('forgot_pin'))

        internal_id = member[0]
        portal = db.fetch_one("SELECT security_question1, security_question2 FROM member_portal WHERE member_id = %s", (internal_id,))
        if not portal or not portal[0] or not portal[1]:
            flash("Security questions not set for this account. Please contact the church office.", "warning")
            return redirect(url_for('forgot_pin'))

        session['reset_member_id'] = internal_id
        return redirect(url_for('verify_questions'))

    return render_template('forgot_pin.html')

@app.route('/verify_questions', methods=['GET', 'POST'])
def verify_questions():
    if 'reset_member_id' not in session:
        flash("Session expired. Please start over.", "danger")
        return redirect(url_for('forgot_pin'))

    db = DatabaseManager()
    internal_id = session['reset_member_id']
    portal = db.fetch_one("SELECT security_question1, security_answer1, security_question2, security_answer2 FROM member_portal WHERE member_id = %s", (internal_id,))
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

        if verify_password(answer1, ans1_hash) and verify_password(answer2, ans2_hash):
            if password_needs_upgrade(ans1_hash) or password_needs_upgrade(ans2_hash):
                db.execute_query("""
                    UPDATE member_portal
                    SET security_answer1 = %s, security_answer2 = %s
                    WHERE member_id = %s
                """, (hash_password(answer1), hash_password(answer2), internal_id))
            session['verified'] = True
            return redirect(url_for('set_new_pin'))
        else:
            flash("Incorrect answers. Please try again.", "danger")
            return render_template('verify_questions.html', q1=q1, q2=q2)

    return render_template('verify_questions.html', q1=q1, q2=q2)

@app.route('/set_new_pin', methods=['GET', 'POST'])
def set_new_pin():
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

        db = DatabaseManager()
        new_hashed = hash_password(new_pin)
        db.execute_query("UPDATE member_portal SET pin = %s WHERE member_id = %s",
                         (new_hashed, session['reset_member_id']))

        session.pop('reset_member_id', None)
        session.pop('verified', None)

        flash("Your PIN has been reset successfully. Please log in with your new PIN.", "success")
        return redirect(url_for('home'))

    return render_template('set_new_pin.html')

# -------------------------------------------------------------------
# Volunteer Management Routes
# -------------------------------------------------------------------

@app.route('/volunteer')
def volunteer_list():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    try:
        db = DatabaseManager()
        today = datetime.now().strftime('%Y-%m-%d')
        member_id = session['member_id']

        rows = db.fetch_all("""
            SELECT 
                v.id, v.title, v.role, v.description, v.date, 
                v.start_time, v.end_time, v.location, v.capacity,
                (SELECT COUNT(*) FROM volunteer_signups 
                 WHERE opportunity_id = v.id AND status = 'approved') as approved_count
            FROM volunteer_opportunities v
            WHERE v.date >= %s AND v.status = 'active'
            ORDER BY v.date, v.start_time
        """, (today,))

        opp_ids = [r[0] for r in rows]
        signups = {}
        if opp_ids:
            placeholders = ','.join(['%s'] * len(opp_ids))
            signup_rows = db.fetch_all(f"""
                SELECT opportunity_id, id, status 
                FROM volunteer_signups 
                WHERE member_id = %s AND opportunity_id IN ({placeholders})
            """, (member_id, *opp_ids))
            for sr in signup_rows:
                signups[sr[0]] = {'id': sr[1], 'status': sr[2]}

        opp_list = []
        for r in rows:
            opp_id = r[0]
            capacity = r[8]
            approved_count = r[9]
            user_signup = signups.get(opp_id)

            opp_list.append({
                'id': opp_id,
                'title': r[1],
                'role': r[2] or '',
                'description': r[3] or '',
                'date': r[4].strftime('%Y-%m-%d') if r[4] else '',
                'start_time': r[5] or '',
                'end_time': r[6] or '',
                'location': r[7] or '',
                'capacity': capacity,
                'registered_count': approved_count,
                'user_signup': user_signup,
                'spots_left': (capacity - approved_count) if capacity else None
            })

        return render_template('volunteer.html', opportunities=opp_list)
    except Exception as e:
        flash(f"An error occurred while fetching opportunities: {str(e)}", "danger")
        return redirect(url_for('home'))

@app.route('/volunteer/signup/<int:opp_id>', methods=['POST'])
def volunteer_signup(opp_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    member_id = session['member_id']
    try:
        if existing := db.fetch_one("""
            SELECT id, status FROM volunteer_signups 
            WHERE opportunity_id=%s AND member_id=%s
        """, (opp_id, member_id)):
            if existing[1] in ('pending', 'approved'):
                flash("You already have an active signup for this opportunity.", "info")
                return redirect(url_for('volunteer_list'))
            else:
                db.execute_query("UPDATE volunteer_signups SET status='pending' WHERE id=%s", (existing[0],))
                flash("Your signup request has been submitted for approval.", "success")
                return redirect(url_for('volunteer_list'))

        opp = db.fetch_one("""
            SELECT capacity, 
                   (SELECT COUNT(*) FROM volunteer_signups WHERE opportunity_id=%s AND status='approved') as approved 
            FROM volunteer_opportunities WHERE id=%s
        """, (opp_id, opp_id))
        if not opp:
            flash("Opportunity not found.", "danger")
            return redirect(url_for('volunteer_list'))
        capacity, approved = opp[0], opp[1]
        if capacity and approved >= capacity:
            flash("This opportunity is full.", "warning")
            return redirect(url_for('volunteer_list'))

        db.execute_query("""
            INSERT INTO volunteer_signups (opportunity_id, member_id, status, signed_up_at)
            VALUES (%s, %s, 'pending', NOW())
        """, (opp_id, member_id))
        flash("Your signup request has been submitted for approval.", "success")
        return redirect(url_for('volunteer_list'))
    except Exception as e:
        flash(f"An error occurred during signup: {str(e)}", "danger")
        return redirect(url_for('volunteer_list'))

@app.route('/volunteer/cancel/<int:signup_id>', methods=['POST'])
def volunteer_cancel(signup_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    member_id = session['member_id']
    try:
        db.execute_query("""
            UPDATE volunteer_signups 
            SET status='cancelled' 
            WHERE id=%s AND member_id=%s
        """, (signup_id, member_id))
        flash("Your signup has been cancelled.", "success")
        return redirect(url_for('volunteer_list'))
    except Exception as e:
        flash(f"An error occurred while cancelling your signup: {str(e)}", "danger")
        return redirect(url_for('volunteer_list'))

# -------------------------------------------------------------------
# Committee Management Routes
# -------------------------------------------------------------------

@app.route('/my_committees')
def my_committees():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    member_id = session['member_id']
    db = DatabaseManager()

    committees = db.fetch_all("""
        SELECT c.id, c.name, c.description, cm.role, cm.joined_date,
               (SELECT COUNT(*) FROM committee_members WHERE committee_id = c.id) as total_members,
               COALESCE(b.name, '') as branch_name
        FROM committee_members cm
        JOIN committees c ON cm.committee_id = c.id
        LEFT JOIN branches b ON c.branch_id = b.id
        WHERE cm.member_id = %s
        ORDER BY c.name
    """, (member_id,))

    committee_list = []
    for c in committees:
        cid, name, description, role, joined, total_members, branch_name = c
        meetings = db.fetch_all("""
            SELECT meeting_date, agenda, location
            FROM committee_meetings
            WHERE committee_id = %s AND meeting_date >= CURRENT_DATE
            ORDER BY meeting_date
            LIMIT 3
        """, (cid,))
        activities = db.fetch_all("""
            SELECT name, start_date, end_date, status
            FROM committee_activities
            WHERE committee_id = %s
            ORDER BY start_date DESC
            LIMIT 3
        """, (cid,))

        committee_list.append({
            'id': cid,
            'name': name,
            'description': description or '',
            'role': role,
            'joined': joined.strftime('%Y-%m-%d') if joined else '',
            'total_members': total_members,
            'branch': branch_name or 'All branches',
            'meetings': [{'date': m[0].strftime('%Y-%m-%d') if m[0] else '', 'agenda': m[1], 'location': m[2]} for m in meetings],
            'activities': [{'name': a[0], 'start': a[1].strftime('%Y-%m-%d') if a[1] else '', 'end': a[2].strftime('%Y-%m-%d') if a[2] else '', 'status': a[3]} for a in activities]
        })

    return render_template('my_committees.html', committees=committee_list)

# -------------------------------------------------------------------
# Asset Management Routes
# -------------------------------------------------------------------

@app.route('/assets')
def assets_list():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    category = request.args.get('category', '')
    search = request.args.get('search', '')

    query = """SELECT a.id, a.name, a.description, a.asset_id, a.purchase_date, 
                      a.purchase_price, a.condition, a.status, a.location, a.photo_path,
                      c.name as category_name
               FROM assets a
               LEFT JOIN asset_categories c ON a.category_id = c.id
               WHERE 1=1"""
    params = []
    conditions = []

    if category and category != 'All':
        conditions.append("c.name = %s")
        params.append(category)

    if search:
        conditions.append("(a.name ILIKE %s OR a.description ILIKE %s OR a.asset_id ILIKE %s)")
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY a.name"

    assets = db.fetch_all(query, params)
    categories = db.fetch_all("SELECT DISTINCT name FROM asset_categories ORDER BY name")

    asset_list = [{
        'id': a[0],
        'name': a[1],
        'description': a[2] or '',
        'serial_number': a[3] or '',
        'purchase_date': a[4].strftime('%Y-%m-%d') if a[4] else '',
        'purchase_price': float(a[5]) if a[5] else 0,
        'condition': a[6] or '',
        'status': a[7] or '',
        'location': a[8] or '',
        'photo_path': a[9] or '',
        'category': a[10] or ''
    } for a in assets]

    return render_template('assets.html', assets=asset_list, categories=[c[0] for c in categories], selected_category=category, search=search)

@app.route('/assets/<int:asset_id>')
def asset_detail(asset_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    asset = db.fetch_one("""
        SELECT a.id, a.name, a.description, a.asset_id, a.purchase_date, 
               a.purchase_price, a.condition, a.status, a.location, a.photo_path,
               c.name as category_name
        FROM assets a
        LEFT JOIN asset_categories c ON a.category_id = c.id
        WHERE a.id = %s
    """, (asset_id,))

    if not asset:
        abort(404)

    maintenance = db.fetch_all("""
        SELECT id, maintenance_date, description, cost, performed_by
        FROM asset_maintenance
        WHERE asset_id = %s
        ORDER BY maintenance_date DESC
    """, (asset_id,))

    assignments = db.fetch_all("""
        SELECT aa.id,
               COALESCE(m.full_name, aa.assigned_to::text),
               aa.assigned_date,
               COALESCE(aa.actual_return_date, aa.expected_return_date),
               aa.notes
        FROM asset_assignments aa
        LEFT JOIN members m ON aa.assigned_to = m.id
        WHERE asset_id = %s
        ORDER BY aa.assigned_date DESC
    """, (asset_id,))

    asset_data = {
        'id': asset[0],
        'name': asset[1],
        'description': asset[2] or '',
        'serial_number': asset[3] or '',
        'purchase_date': asset[4].strftime('%Y-%m-%d') if asset[4] else '',
        'purchase_price': float(asset[5]) if asset[5] else 0,
        'condition': asset[6] or '',
        'status': asset[7] or '',
        'location': asset[8] or '',
        'photo_path': asset[9] or '',
        'category': asset[10] or '',
        'maintenance': [{'id': m[0], 'date': m[1].strftime('%Y-%m-%d') if m[1] else '', 'description': m[2], 'cost': float(m[3]) if m[3] else 0, 'performed_by': m[4]} for m in maintenance],
        'assignments': [{'id': a[0], 'assigned_to': a[1], 'date': a[2].strftime('%Y-%m-%d') if a[2] else '', 'return_date': a[3].strftime('%Y-%m-%d') if a[3] else '', 'notes': a[4]} for a in assignments]
    }

    return render_template('asset_detail.html', asset=asset_data)

# -------------------------------------------------------------------
# Service Planning Routes
# -------------------------------------------------------------------

@app.route('/service_schedule')
def service_schedule():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    date_filter = request.args.get('date', '')

    query = """SELECT s.id, s.service_date, s.service_type_id, s.theme, s.notes,
                      s.title, st.name as type_name
               FROM service_schedule s
               LEFT JOIN service_types st ON s.service_type_id = st.id
               WHERE 1=1"""
    params = []

    if date_filter:
        query += " AND s.service_date = %s"
        params.append(date_filter)
    else:
        query += " AND s.service_date >= CURRENT_DATE"

    query += " ORDER BY s.service_date"

    services = db.fetch_all(query, params)

    service_list = [{
        'id': s[0],
        'date': s[1].strftime('%Y-%m-%d') if s[1] else '',
        'service_type_id': s[2] or '',
        'theme': s[3] or '',
        'notes': s[4] or '',
        'title': s[5] or '',
        'leader': '',
        'type_name': s[6] or ''
    } for s in services]

    return render_template('service_schedule.html', services=service_list, date_filter=date_filter)

@app.route('/service/<int:service_id>')
def service_detail(service_id):
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    service = db.fetch_one("""
        SELECT s.id, s.service_date, s.service_type_id, s.theme, s.notes,
               s.title, st.name as type_name
        FROM service_schedule s
        LEFT JOIN service_types st ON s.service_type_id = st.id
        WHERE s.id = %s
    """, (service_id,))

    if not service:
        abort(404)

    items = db.fetch_all("""
        SELECT id, item_type, title, description, duration_minutes, item_order
        FROM service_items
        WHERE service_id = %s
        ORDER BY item_order
    """, (service_id,))

    songs = []

    service_data = {
        'id': service[0],
        'date': service[1].strftime('%Y-%m-%d') if service[1] else '',
        'service_type_id': service[2] or '',
        'theme': service[3] or '',
        'notes': service[4] or '',
        'title': service[5] or '',
        'leader': '',
        'type_name': service[6] or '',
        'items': [{'id': i[0], 'type': i[1], 'title': i[2], 'description': i[3], 'duration': i[4], 'order': i[5]} for i in items],
        'songs': [{'id': s[0], 'title': s[1], 'key': s[2], 'duration': s[3], 'notes': s[4]} for s in songs]
    }

    return render_template('service_detail.html', service=service_data)

@app.route('/sermons')
def sermons_list():
    if 'member_id' not in session:
        return redirect(url_for('home'))

    db = DatabaseManager()
    search = request.args.get('search', '')

    query = """SELECT id, title, preacher, service_date, duration_minutes, summary, scripture_reference
               FROM sermons WHERE 1=1"""
    params = []

    if search:
        query += " AND (title ILIKE %s OR preacher ILIKE %s OR summary ILIKE %s OR scripture_reference ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])

    query += " ORDER BY service_date DESC"

    sermons = db.fetch_all(query, params)

    sermon_list = [{
        'id': s[0],
        'title': s[1],
        'preacher': s[2] or '',
        'date': s[3].strftime('%Y-%m-%d') if s[3] else '',
        'duration': s[4] or '',
        'description': s[5] or '',
        'notes': s[6] or ''
    } for s in sermons]

    return render_template('sermons.html', sermons=sermon_list, search=search)

# -------------------------------------------------------------------
# Application Entry Point
# -------------------------------------------------------------------

if __name__ == '__main__':
    try:
        print(" * Initializing app...", flush=True)
        port = int(os.environ.get('PORT', 5000))
        host = os.environ.get('HOST', 'localhost')
        print(f" * Starting on http://{host}:{port}", flush=True)
        print(" * Running Flask server...", flush=True)
        print(" * Press Ctrl+C to stop", flush=True)
        app.run(host=host, port=port, debug=False)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f" * ERROR: Port {port} is already in use!", flush=True)
            print(f" * Try: set PORT=5001 && python app.py", flush=True)
        else:
            print(f" * ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f" * ERROR: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
