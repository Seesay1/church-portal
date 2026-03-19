# modules/member_portal.py
import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager, hash_password
from datetime import datetime

class MemberPortalLogin:
    """Login dialog for members using Member ID and PIN."""
    def __init__(self, parent):
        self.parent = parent  # store reference to parent window
        self.win = tk.Toplevel(parent)
        self.win.title("Member Portal Login")
        self.win.geometry("400x300")
        self.win.configure(bg="#e8f1ff")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        tk.Label(self.win, text="Member Portal", font=("Helvetica", 16, "bold"),
                 bg="#e8f1ff", fg="#1f4fa3").pack(pady=20)

        tk.Label(self.win, text="Member ID:", bg="#e8f1ff", font=("Helvetica", 10)).pack()
        self.member_id_entry = tk.Entry(self.win, font=("Helvetica", 10))
        self.member_id_entry.pack(pady=5)

        tk.Label(self.win, text="PIN:", bg="#e8f1ff", font=("Helvetica", 10)).pack()
        self.pin_entry = tk.Entry(self.win, show="*", font=("Helvetica", 10))
        self.pin_entry.pack(pady=5)

        tk.Button(self.win, text="Login", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 11, "bold"), command=self.login).pack(pady=20)

        self.win.bind("<Return>", lambda e: self.login())

    def login(self):
        member_id = self.member_id_entry.get().strip()
        pin = self.pin_entry.get().strip()
        if not member_id or not pin:
            messagebox.showerror("Error", "Please enter both Member ID and PIN.")
            return

        db = DatabaseManager()
        # Get internal member id
        member = db.fetch_one("SELECT id FROM members WHERE member_id=?", (member_id,))
        if not member:
            messagebox.showerror("Error", "Invalid Member ID.")
            return
        internal_id = member[0]

        # Check portal credentials
        portal = db.fetch_one("SELECT pin FROM member_portal WHERE member_id=?", (internal_id,))
        if not portal:
            messagebox.showerror("Error", "Portal account not set up. Please contact the church office.")
            return

        if hash_password(pin) != portal[0]:
            messagebox.showerror("Error", "Incorrect PIN.")
            return

        # Update last login timestamp
        db.execute_query("UPDATE member_portal SET last_login=? WHERE member_id=?",
                         (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), internal_id))

        self.win.destroy()
        # Open the member dashboard, passing the parent (original root window) and member_id
        MemberPortalDashboard(self.parent, internal_id)


class MemberPortalDashboard:
    """Main dashboard for a logged‑in member."""
    def __init__(self, parent, member_id):
        self.win = tk.Toplevel(parent)
        self.win.title("Member Portal")
        self.win.geometry("800x600")
        self.win.configure(bg="#e8f1ff")
        self.member_id = member_id

        # Create notebook
        notebook = ttk.Notebook(self.win)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        self.profile_frame = tk.Frame(notebook, bg="#e8f1ff")
        notebook.add(self.profile_frame, text="👤 Profile")

        self.attendance_frame = tk.Frame(notebook, bg="#e8f1ff")
        notebook.add(self.attendance_frame, text="📋 Attendance")

        self.contrib_frame = tk.Frame(notebook, bg="#e8f1ff")
        notebook.add(self.contrib_frame, text="💰 Contributions")

        self.cert_frame = tk.Frame(notebook, bg="#e8f1ff")
        notebook.add(self.cert_frame, text="📜 Certificates")

        # Load data
        self.load_profile()
        self.load_attendance()
        self.load_contributions()
        self.load_certificates()

    def load_profile(self):
        db = DatabaseManager()
        member = db.fetch_one("""
            SELECT m.member_id, m.full_name, m.gender, m.phone, m.email,
                   b.name, g.name, d.name
            FROM members m
            LEFT JOIN branches b ON m.branch_id = b.id
            LEFT JOIN groups g ON m.group_id = g.id
            LEFT JOIN departments d ON m.department_id = d.id
            WHERE m.id=?
        """, (self.member_id,))
        if not member:
            return
        mid, name, gender, phone, email, branch, group, dept = member

        info = f"""
        Member ID:    {mid}
        Full Name:    {name}
        Gender:       {gender or 'N/A'}
        Phone:        {phone or 'N/A'}
        Email:        {email or 'N/A'}
        Branch:       {branch or 'N/A'}
        Group:        {group or 'N/A'}
        Department:   {dept or 'N/A'}
        """
        tk.Label(self.profile_frame, text=info, bg="#e8f1ff",
                 font=("Helvetica", 12), justify="left").pack(pady=20)

    def load_attendance(self):
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT date, present FROM attendance
            WHERE member_id=? ORDER BY date DESC LIMIT 50
        """, (self.member_id,))

        tree = ttk.Treeview(self.attendance_frame, columns=("Date", "Present"), show="headings")
        tree.heading("Date", text="Date")
        tree.heading("Present", text="Present")
        tree.column("Date", width=120)
        tree.column("Present", width=80)
        for r in rows:
            status = "Yes" if r[1] else "No"
            tree.insert("", tk.END, values=(r[0], status))
        tree.pack(fill="both", expand=True, padx=10, pady=10)

    def load_contributions(self):
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT type, amount, date FROM financial_records
            WHERE member_id=? ORDER BY date DESC LIMIT 50
        """, (self.member_id,))

        tree = ttk.Treeview(self.contrib_frame, columns=("Type", "Amount", "Date"), show="headings")
        tree.heading("Type", text="Type")
        tree.heading("Amount", text="Amount")
        tree.heading("Date", text="Date")
        tree.column("Type", width=100)
        tree.column("Amount", width=100)
        tree.column("Date", width=120)
        for r in rows:
            tree.insert("", tk.END, values=r)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

    def load_certificates(self):
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT certificate_type, generated_date FROM certificates
            WHERE member_id=? ORDER BY generated_date DESC
        """, (self.member_id,))

        tree = ttk.Treeview(self.cert_frame, columns=("Type", "Date"), show="headings")
        tree.heading("Type", text="Certificate Type")
        tree.heading("Date", text="Generated Date")
        tree.column("Type", width=150)
        tree.column("Date", width=150)
        for r in rows:
            tree.insert("", tk.END, values=r)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Button(self.cert_frame, text="Request New Certificate", bg="#1f4fa3", fg="#fff",
                  command=self.request_certificate).pack(pady=5)

    def request_certificate(self):
    # Open a small dialog to choose certificate type
        win = tk.Toplevel(self.win)
        win.title("Request Certificate")
        win.geometry("300x200")
        win.configure(bg="#e8f1ff")
        win.transient(self.win)
        win.grab_set()

        tk.Label(win, text="Certificate Type:", bg="#e8f1ff", font=("Helvetica", 10)).pack(pady=10)
        cert_type_var = tk.StringVar()
        cert_type_combo = ttk.Combobox(win, textvariable=cert_type_var,
                                        values=["Baptism", "Confirmation", "Membership", "Promotion", "Dedication"],
                                        state="readonly", width=20)
        cert_type_combo.pack(pady=5)
        cert_type_combo.set("Baptism")

        def submit():
            cert_type = cert_type_var.get()
            if not cert_type:
                messagebox.showerror("Error", "Select a certificate type.")
                return
            db = DatabaseManager()
            request_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute_query(
                "INSERT INTO certificate_requests (member_id, certificate_type, request_date) VALUES (?,?,?)",
                (self.member_id, cert_type, request_date)
            )
            messagebox.showinfo("Success", "Your request has been submitted. You will be notified when ready.")
            win.destroy()

        tk.Button(win, text="Submit", bg="#1f4fa3", fg="#fff", command=submit).pack(pady=10)