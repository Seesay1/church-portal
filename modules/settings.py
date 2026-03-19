import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from database import DatabaseManager, hash_password
import tkinter.simpledialog as simpledialog
import json
import os
import shutil
from datetime import datetime

try:
    from config import FONT_TEXT
except ImportError:
    FONT_TEXT = ("Helvetica", 10)

class SettingsModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.user_id = user_id
        self.branch_id = branch_id
        self.root.configure(bg="#e8f1ff")

        # Create Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tabs
        self.general_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.general_frame, text="⚙️ General")

        self.sms_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.sms_frame, text="📱 SMS")

        self.users_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.users_frame, text="👥 Users")

        self.backup_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.backup_frame, text="💾 Backup")

        self.appearance_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.appearance_frame, text="🎨 Appearance")

        # Tab 6: Dashboard Widgets
        self.widgets_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.widgets_frame, text="📊 Dashboard Widgets")

        self.setup_general_tab()
        self.setup_sms_tab()
        self.setup_users_tab()
        self.setup_backup_tab()
        self.setup_appearance_tab()
        self.setup_widgets_tab()   # new

        self.load_settings()

    # ---------- Database helpers ----------
    def get_setting(self, key, default=""):
        db = DatabaseManager()
        res = db.fetch_one("SELECT value FROM settings WHERE key=?", (key,))
        return res[0] if res else default

    def save_setting(self, key, value):
        db = DatabaseManager()
        existing = db.fetch_one("SELECT id FROM settings WHERE key=?", (key,))
        if existing:
            db.execute_query("UPDATE settings SET value=? WHERE key=?", (value, key))
        else:
            db.execute_query("INSERT INTO settings (key, value) VALUES (?,?)", (key, value))

    # ================== GENERAL TAB ==================
    def setup_general_tab(self):
        main = tk.Frame(self.general_frame, bg="#e8f1ff")
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Church Name
        tk.Label(main, text="Church Name:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.church_name_entry = tk.Entry(main, font=FONT_TEXT, width=40)
        self.church_name_entry.grid(row=0, column=1, pady=5, padx=5, sticky="w")

        # Church Address
        tk.Label(main, text="Church Address:", bg="#e8f1ff", font=FONT_TEXT).grid(row=1, column=0, sticky="w", pady=5)
        self.church_address_entry = tk.Entry(main, font=FONT_TEXT, width=40)
        self.church_address_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")

        # Church Phone
        tk.Label(main, text="Church Phone:", bg="#e8f1ff", font=FONT_TEXT).grid(row=2, column=0, sticky="w", pady=5)
        self.church_phone_entry = tk.Entry(main, font=FONT_TEXT, width=40)
        self.church_phone_entry.grid(row=2, column=1, pady=5, padx=5, sticky="w")

        # Church Email
        tk.Label(main, text="Church Email:", bg="#e8f1ff", font=FONT_TEXT).grid(row=3, column=0, sticky="w", pady=5)
        self.church_email_entry = tk.Entry(main, font=FONT_TEXT, width=40)
        self.church_email_entry.grid(row=3, column=1, pady=5, padx=5, sticky="w")

        # Default Bible Verse
        tk.Label(main, text="Default Bible Verse:", bg="#e8f1ff", font=FONT_TEXT).grid(row=4, column=0, sticky="w", pady=5)
        self.bible_verse_entry = tk.Entry(main, font=FONT_TEXT, width=40)
        self.bible_verse_entry.grid(row=4, column=1, pady=5, padx=5, sticky="w")

        # Branch Code Mapping (simple textarea for JSON)
        # ---- Branch Codes (with editor) ----
        tk.Label(main, text="Branch Codes:", bg="#e8f1ff", font=FONT_TEXT).grid(row=5, column=0, sticky="nw", pady=5)
        self.branch_codes_text = tk.Text(main, height=5, width=40, font=FONT_TEXT)
        self.branch_codes_text.grid(row=5, column=1, pady=5, padx=5, sticky="w")
        # Add a button to open the editor
        tk.Button(main, text="✏️ Edit Branch Codes", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.edit_branch_codes).grid(row=5, column=2, padx=5)

        # Save button
        tk.Button(main, text="💾 Save General Settings", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 11, "bold"), command=self.save_general_settings).grid(row=6, column=1, pady=20, sticky="w")

    def edit_branch_codes(self):
        """Open a dialog to edit branch codes as key-value pairs."""
        # Parse current JSON from the text field
        current_text = self.branch_codes_text.get("1.0", tk.END).strip()
        try:
            codes = json.loads(current_text) if current_text else {}
        except json.JSONDecodeError:
            codes = {}
            messagebox.showerror("Error", "Invalid JSON in branch codes. Starting with empty list.")

        win = tk.Toplevel(self.root)
        win.title("Edit Branch Codes")
        win.geometry("500x400")
        win.configure(bg="#e8f1ff")
        win.transient(self.root)
        win.grab_set()

        # Treeview to show branch-code pairs
        columns = ("Branch Name", "Code Prefix")
        tree = ttk.Treeview(win, columns=columns, show="headings")
        tree.heading("Branch Name", text="Branch Name")
        tree.heading("Code Prefix", text="Code Prefix")
        tree.column("Branch Name", width=200)
        tree.column("Code Prefix", width=150)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Populate tree
        for branch, code in codes.items():
            tree.insert("", tk.END, values=(branch, code))

        # Buttons frame
        btn_frame = tk.Frame(win, bg="#e8f1ff")
        btn_frame.pack(fill="x", pady=5)

        def add_code():
            # Simple input dialogs
            branch = simpledialog.askstring("Add Branch", "Enter branch name:", parent=win)
            if not branch:
                return
            code = simpledialog.askstring("Add Code", "Enter code prefix (e.g., PCG-MZ):", parent=win)
            if not code:
                return
            # Check for duplicate
            for item in tree.get_children():
                if tree.item(item, "values")[0].lower() == branch.lower():
                    messagebox.showerror("Error", "Branch already exists!")
                    return
            tree.insert("", tk.END, values=(branch, code))

        def edit_code():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("No selection", "Select a branch to edit.")
                return
            item = selected[0]
            old_branch, old_code = tree.item(item, "values")
            new_branch = simpledialog.askstring("Edit Branch", "Edit branch name:", initialvalue=old_branch, parent=win)
            if not new_branch:
                return
            new_code = simpledialog.askstring("Edit Code", "Edit code prefix:", initialvalue=old_code, parent=win)
            if not new_code:
                return
            tree.item(item, values=(new_branch, new_code))

        def delete_code():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("No selection", "Select a branch to delete.")
                return
            if messagebox.askyesno("Confirm Delete", "Delete selected branch code?"):
                for item in selected:
                    tree.delete(item)

        def save_codes():
            # Collect all items
            new_codes = {}
            for item in tree.get_children():
                branch, code = tree.item(item, "values")
                new_codes[branch] = code
            # Update the text widget with pretty JSON
            self.branch_codes_text.delete("1.0", tk.END)
            self.branch_codes_text.insert("1.0", json.dumps(new_codes, indent=2))
            win.destroy()

        tk.Button(btn_frame, text="➕ Add", bg="#1f4fa3", fg="#fff", command=add_code).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✏️ Edit", bg="#1f4fa3", fg="#fff", command=edit_code).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete", bg="#333", fg="#fff", command=delete_code).pack(side="left", padx=5)
        tk.Button(btn_frame, text="💾 Save", bg="#d62828", fg="#fff", command=save_codes).pack(side="right", padx=5)
        tk.Button(btn_frame, text="Cancel", bg="#888888", fg="#fff", command=win.destroy).pack(side="right", padx=5)    

    def save_general_settings(self):
        self.save_setting("church_name", self.church_name_entry.get())
        self.save_setting("church_address", self.church_address_entry.get())
        self.save_setting("church_phone", self.church_phone_entry.get())
        self.save_setting("church_email", self.church_email_entry.get())
        self.save_setting("default_bible_verse", self.bible_verse_entry.get())
        codes = self.branch_codes_text.get("1.0", tk.END).strip()
        # Validate JSON
        try:
            json.loads(codes) if codes else None
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Invalid JSON format for branch codes.")
            return
        self.save_setting("branch_codes", codes)
        messagebox.showinfo("Success", "General settings saved.")

    # ================== SMS TAB ==================
    def setup_sms_tab(self):
        main = tk.Frame(self.sms_frame, bg="#e8f1ff")
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # API Provider
        tk.Label(main, text="SMS Provider:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.sms_provider = ttk.Combobox(main, values=["Twilio", "Hubtel", "Other"], font=FONT_TEXT, width=20)
        self.sms_provider.grid(row=0, column=1, pady=5, padx=5, sticky="w")

        # API URL
        tk.Label(main, text="API URL:", bg="#e8f1ff", font=FONT_TEXT).grid(row=1, column=0, sticky="w", pady=5)
        self.sms_api_url = tk.Entry(main, font=FONT_TEXT, width=50)
        self.sms_api_url.grid(row=1, column=1, pady=5, padx=5, sticky="w")

        # API Key
        tk.Label(main, text="API Key:", bg="#e8f1ff", font=FONT_TEXT).grid(row=2, column=0, sticky="w", pady=5)
        self.sms_api_key = tk.Entry(main, font=FONT_TEXT, width=50, show="*")
        self.sms_api_key.grid(row=2, column=1, pady=5, padx=5, sticky="w")

        # Sender ID
        tk.Label(main, text="Sender ID:", bg="#e8f1ff", font=FONT_TEXT).grid(row=3, column=0, sticky="w", pady=5)
        self.sms_sender_id = tk.Entry(main, font=FONT_TEXT, width=50)
        self.sms_sender_id.grid(row=3, column=1, pady=5, padx=5, sticky="w")

        # Test button
        tk.Button(main, text="📨 Test Connection", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.test_sms_connection).grid(row=4, column=1, pady=10, sticky="w")

        # Save button
        tk.Button(main, text="💾 Save SMS Settings", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 11, "bold"), command=self.save_sms_settings).grid(row=5, column=1, pady=10, sticky="w")

    def save_sms_settings(self):
        self.save_setting("sms_provider", self.sms_provider.get())
        self.save_setting("sms_api_url", self.sms_api_url.get())
        self.save_setting("sms_api_key", self.sms_api_key.get())
        self.save_setting("sms_sender_id", self.sms_sender_id.get())
        messagebox.showinfo("Success", "SMS settings saved.")

    def test_sms_connection(self):
        # Placeholder test – you can integrate actual API test later
        messagebox.showinfo("Test", "Connection test would be performed here. (Not implemented)")

    # ================== USERS TAB ==================
    def setup_users_tab(self):
        # Treeview for users
        tree_frame = tk.Frame(self.users_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("ID", "Username", "Role", "Security Question", "DB_ID")
        self.users_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=120)
        self.users_tree.column("DB_ID", width=0, stretch=False)  # hidden
        self.users_tree.pack(fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(self.users_frame, bg="#e8f1ff")
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="➕ Add User", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.add_user).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✏️ Edit Selected", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.edit_user).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete Selected", bg="#333", fg="#fff",
                  font=FONT_TEXT, command=self.delete_user).pack(side="left", padx=5)

        self.load_users()

    def load_users(self):
        for row in self.users_tree.get_children():
            self.users_tree.delete(row)
        db = DatabaseManager()
        users = db.fetch_all("SELECT id, username, role, security_question FROM users ORDER BY username")
        for u in users:
            self.users_tree.insert("", tk.END, values=(u[0], u[1], u[2], u[3], u[0]))

    def add_user(self):
        self.user_form("Add User")

    def edit_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a user to edit.")
            return
        user_id = self.users_tree.item(selected[0])['values'][4]
        self.user_form("Edit User", user_id)

    def delete_user(self):
        selected = self.users_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a user to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected user?"):
            return
        db = DatabaseManager()
        for item in selected:
            user_id = self.users_tree.item(item)['values'][4]
            db.execute_query("DELETE FROM users WHERE id=?", (user_id,))
        self.load_users()
        messagebox.showinfo("Success", "User(s) deleted.")

    def user_form(self, title, user_id=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("400x450")
        win.configure(bg="#e8f1ff")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Username:", bg="#e8f1ff", font=FONT_TEXT).pack(pady=5)
        username_entry = tk.Entry(win, font=FONT_TEXT, width=30)
        username_entry.pack(pady=5)

        tk.Label(win, text="Password (leave blank to keep unchanged):", bg="#e8f1ff", font=FONT_TEXT).pack(pady=5)
        password_entry = tk.Entry(win, font=FONT_TEXT, width=30, show="*")
        password_entry.pack(pady=5)

        tk.Label(win, text="Role:", bg="#e8f1ff", font=FONT_TEXT).pack(pady=5)
        role_combo = ttk.Combobox(win, values=["Admin", "User"], state="readonly", font=FONT_TEXT)
        role_combo.pack(pady=5)

        tk.Label(win, text="Security Question:", bg="#e8f1ff", font=FONT_TEXT).pack(pady=5)
        question_combo = ttk.Combobox(win, values=[
            "What is your mother's maiden name?",
            "What was your first pet's name?",
            "What is your favorite book?",
            "What city were you born in?",
            "What is your favorite food?"
        ], font=FONT_TEXT, width=38)
        question_combo.pack(pady=5)

        tk.Label(win, text="Security Answer:", bg="#e8f1ff", font=FONT_TEXT).pack(pady=5)
        answer_entry = tk.Entry(win, font=FONT_TEXT, width=30)
        answer_entry.pack(pady=5)

        if user_id:
            db = DatabaseManager()
            user = db.fetch_one("SELECT username, role, security_question, security_answer FROM users WHERE id=?", (user_id,))
            if user:
                username_entry.insert(0, user[0])
                role_combo.set(user[1])
                question_combo.set(user[2] or "")
                # answer not filled for security

        def save():
            uname = username_entry.get().strip()
            pwd = password_entry.get().strip()
            role = role_combo.get().strip()
            question = question_combo.get().strip()
            answer = answer_entry.get().strip().lower()

            if not uname or not role:
                messagebox.showerror("Error", "Username and role required.")
                return
            db = DatabaseManager()
            if user_id:
                # Update
                if pwd:
                    hashed = hash_password(pwd)
                    db.execute_query("UPDATE users SET password=? WHERE id=?", (hashed, user_id))
                db.execute_query("UPDATE users SET username=?, role=?, security_question=? WHERE id=?",
                                 (uname, role, question, user_id))
                if answer:
                    hashed_ans = hash_password(answer)
                    db.execute_query("UPDATE users SET security_answer=? WHERE id=?", (hashed_ans, user_id))
                messagebox.showinfo("Success", "User updated.")
            else:
                if not pwd:
                    messagebox.showerror("Error", "Password required for new users.")
                    return
                hashed = hash_password(pwd)
                hashed_ans = hash_password(answer) if answer else None
                db.execute_query(
                    "INSERT INTO users (username, password, role, security_question, security_answer) VALUES (?,?,?,?,?)",
                    (uname, hashed, role, question, hashed_ans)
                )
                messagebox.showinfo("Success", "User added.")
            win.destroy()
            self.load_users()

        tk.Button(win, text="Save", bg="#d62828", fg="#fff", font=FONT_TEXT, command=save).pack(pady=20)

    # ================== BACKUP TAB ==================
    def setup_backup_tab(self):
        main = tk.Frame(self.backup_frame, bg="#e8f1ff")
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Backup database
        tk.Button(main, text="💾 Backup Database", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 12), command=self.backup_database).pack(pady=10, fill="x")

        # Restore database
        tk.Button(main, text="📂 Restore Database", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 12), command=self.restore_database).pack(pady=10, fill="x")

        # Export settings
        tk.Button(main, text="📤 Export Settings (JSON)", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 12), command=self.export_settings).pack(pady=10, fill="x")

        # Import settings
        tk.Button(main, text="📥 Import Settings (JSON)", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 12), command=self.import_settings).pack(pady=10, fill="x")

    def backup_database(self):
        db_file = "church_system.db"
        if not os.path.exists(db_file):
            messagebox.showerror("Error", "Database file not found.")
            return
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"church_system_backup_{timestamp}.db")
        try:
            shutil.copy2(db_file, backup_file)
            messagebox.showinfo("Success", f"Database backed up to:\n{backup_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed: {e}")

    def restore_database(self):
        file_path = filedialog.askopenfilename(
            title="Select Backup File",
            filetypes=[("Database files", "*.db"), ("All files", "*.*")]
        )
        if not file_path:
            return
        if not messagebox.askyesno("Confirm Restore", "This will overwrite the current database. Continue?"):
            return
        try:
            shutil.copy2(file_path, "church_system.db")
            messagebox.showinfo("Success", "Database restored. Please restart the application.")
        except Exception as e:
            messagebox.showerror("Error", f"Restore failed: {e}")

    def export_settings(self):
        db = DatabaseManager()
        rows = db.fetch_all("SELECT key, value FROM settings")
        settings_dict = {k: v for k, v in rows}
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            title="Export Settings",
            initialfile="settings_export.json"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=4)
            messagebox.showinfo("Success", f"Settings exported to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {e}")

    def import_settings(self):
        file_path = filedialog.askopenfilename(
            title="Select Settings File",
            filetypes=[("JSON files", "*.json")]
        )
        if not file_path:
            return
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            db = DatabaseManager()
            for key, value in settings.items():
                existing = db.fetch_one("SELECT id FROM settings WHERE key=?", (key,))
                if existing:
                    db.execute_query("UPDATE settings SET value=? WHERE key=?", (value, key))
                else:
                    db.execute_query("INSERT INTO settings (key, value) VALUES (?,?)", (key, value))
            messagebox.showinfo("Success", "Settings imported successfully.")
            self.load_settings()  # refresh all tabs
        except Exception as e:
            messagebox.showerror("Error", f"Import failed: {e}")

    # ================== APPEARANCE TAB ==================
    def setup_appearance_tab(self):
        main = tk.Frame(self.appearance_frame, bg="#e8f1ff")
        main.pack(fill="both", expand=True, padx=20, pady=20)

        # Theme selection
        tk.Label(main, text="Theme:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.theme_var = tk.StringVar()
        theme_combo = ttk.Combobox(main, textvariable=self.theme_var,
                                    values=["Light", "Dark"], state="readonly", font=FONT_TEXT)
        theme_combo.grid(row=0, column=1, pady=5, padx=5, sticky="w")

        # Primary color (accent)
        tk.Label(main, text="Primary Color:", bg="#e8f1ff", font=FONT_TEXT).grid(row=1, column=0, sticky="w", pady=5)
        self.primary_color_entry = tk.Entry(main, font=FONT_TEXT, width=20)
        self.primary_color_entry.grid(row=1, column=1, pady=5, padx=5, sticky="w")
        tk.Button(main, text="Choose", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.choose_primary_color).grid(row=1, column=2, padx=5)

        # Secondary color
        tk.Label(main, text="Secondary Color:", bg="#e8f1ff", font=FONT_TEXT).grid(row=2, column=0, sticky="w", pady=5)
        self.secondary_color_entry = tk.Entry(main, font=FONT_TEXT, width=20)
        self.secondary_color_entry.grid(row=2, column=1, pady=5, padx=5, sticky="w")
        tk.Button(main, text="Choose", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.choose_secondary_color).grid(row=2, column=2, padx=5)

        # Save button
        tk.Button(main, text="💾 Save Appearance", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 11, "bold"), command=self.save_appearance).grid(row=3, column=1, pady=20, sticky="w")

    def choose_primary_color(self):
        color = colorchooser.askcolor(title="Choose Primary Color")[1]
        if color:
            self.primary_color_entry.delete(0, tk.END)
            self.primary_color_entry.insert(0, color)

    def choose_secondary_color(self):
        color = colorchooser.askcolor(title="Choose Secondary Color")[1]
        if color:
            self.secondary_color_entry.delete(0, tk.END)
            self.secondary_color_entry.insert(0, color)

    def save_appearance(self):
        self.save_setting("theme", self.theme_var.get())
        self.save_setting("primary_color", self.primary_color_entry.get())
        self.save_setting("secondary_color", self.secondary_color_entry.get())
        messagebox.showinfo("Success", "Appearance settings saved. Restart to see changes?")
        # Optionally, we could emit a signal to refresh dashboard theme

    # ================== LOAD SETTINGS ==================
    def load_settings(self):
        # General
        self.church_name_entry.insert(0, self.get_setting("church_name", ""))
        self.church_address_entry.insert(0, self.get_setting("church_address", ""))
        self.church_phone_entry.insert(0, self.get_setting("church_phone", ""))
        self.church_email_entry.insert(0, self.get_setting("church_email", ""))
        self.bible_verse_entry.insert(0, self.get_setting("default_bible_verse", ""))
        branch_codes = self.get_setting("branch_codes", "{}")
        self.branch_codes_text.insert("1.0", branch_codes)

        # SMS
        self.sms_provider.set(self.get_setting("sms_provider", ""))
        self.sms_api_url.insert(0, self.get_setting("sms_api_url", ""))
        self.sms_api_key.insert(0, self.get_setting("sms_api_key", ""))
        self.sms_sender_id.insert(0, self.get_setting("sms_sender_id", ""))

        # Appearance
        self.theme_var.set(self.get_setting("theme", "Light"))
        self.primary_color_entry.insert(0, self.get_setting("primary_color", "#1f4fa3"))
        self.secondary_color_entry.insert(0, self.get_setting("secondary_color", "#d62828"))

    # ================== WIDGETS TAB (UPDATED) ==================
    def setup_widgets_tab(self):
        """Tab for dashboard widget configuration."""
        main = tk.Frame(self.widgets_frame, bg="#e8f1ff")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(main, text="Select which widgets to show on your dashboard and arrange them.",
                bg="#e8f1ff", font=FONT_TEXT, wraplength=400, justify="left").pack(anchor="w", pady=5)

        # Columns: Display Name, Visible, Internal Name (hidden)
        columns = ("Widget", "Visible", "Internal")
        self.widgets_tree = ttk.Treeview(main, columns=columns, show="headings", height=8)
        self.widgets_tree.heading("Widget", text="Widget")
        self.widgets_tree.heading("Visible", text="Visible")
        self.widgets_tree.heading("Internal", text="Internal")
        self.widgets_tree.column("Widget", width=250)
        self.widgets_tree.column("Visible", width=60)
        self.widgets_tree.column("Internal", width=0, stretch=False)  # hidden
        self.widgets_tree.pack(fill="both", expand=True, pady=10)

        # Buttons to reorder
        btn_frame = tk.Frame(main, bg="#e8f1ff")
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="↑ Move Up", bg="#1f4fa3", fg="#fff",
                font=FONT_TEXT, command=self.move_widget_up).pack(side="left", padx=5)
        tk.Button(btn_frame, text="↓ Move Down", bg="#1f4fa3", fg="#fff",
                font=FONT_TEXT, command=self.move_widget_down).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Toggle Visibility", bg="#1f4fa3", fg="#fff",
                font=FONT_TEXT, command=self.toggle_widget_visibility).pack(side="left", padx=5)

        # Save button
        tk.Button(main, text="💾 Save Widget Settings", bg="#d62828", fg="#fff",
                font=("Helvetica", 11, "bold"), command=self.save_widget_settings).pack(pady=10)

        self.load_widget_settings()

    def load_widget_settings(self):
        """Load user's widget preferences from database."""
        db = DatabaseManager()
        # Predefined list of available widgets: (internal_id, display_name)
        all_widgets = [
            ("summary", "Summary Cards"),
            ("contrib_chart", "Contribution Chart"),
            ("attendance_trend", "Attendance Trend"),
            ("member_growth", "Member Growth"),
            ("upcoming_events", "Upcoming Events"),
            ("recent_contributions", "Recent Contributions"),
        ]
        # Get user's settings
        rows = db.fetch_all(
            "SELECT widget_name, is_visible, widget_order FROM user_widgets WHERE user_id=? ORDER BY widget_order",
            (self.user_id,)
        )
        # Build a dict for quick lookup
        user_widgets = {r[0]: (r[1], r[2]) for r in rows}
        # Clear tree
        for item in self.widgets_tree.get_children():
            self.widgets_tree.delete(item)

        # Insert widgets in order (if user has settings, use that order; else default)
        if rows:
            # Use saved order
            for row in rows:
                internal = row[0]
                visible = row[1]
                display = next((d for i, d in all_widgets if i == internal), internal)
                self.widgets_tree.insert("", "end", values=(display, "✓" if visible else "", internal))
        else:
            # Default order as defined in all_widgets
            for internal, display in all_widgets:
                self.widgets_tree.insert("", "end", values=(display, "✓", internal))

    def move_widget_up(self):
        selected = self.widgets_tree.selection()
        if not selected:
            return
        idx = self.widgets_tree.index(selected[0])
        if idx == 0:
            return
        self.widgets_tree.move(selected[0], self.widgets_tree.parent(selected[0]), idx-1)

    def move_widget_down(self):
        selected = self.widgets_tree.selection()
        if not selected:
            return
        idx = self.widgets_tree.index(selected[0])
        if idx == len(self.widgets_tree.get_children())-1:
            return
        self.widgets_tree.move(selected[0], self.widgets_tree.parent(selected[0]), idx+1)

    def toggle_widget_visibility(self):
        selected = self.widgets_tree.selection()
        if not selected:
            return
        for item in selected:
            current = self.widgets_tree.item(item, "values")[1]
            new = "" if current == "✓" else "✓"
            # Update the row, preserving internal value (index 2)
            internal = self.widgets_tree.item(item, "values")[2]
            self.widgets_tree.item(item, values=(self.widgets_tree.item(item, "values")[0], new, internal))

    def save_widget_settings(self):
        """Save widget order and visibility to database."""
        db = DatabaseManager()
        # First delete existing entries for this user
        db.execute_query("DELETE FROM user_widgets WHERE user_id=?", (self.user_id,))
        # Insert new settings
        for idx, item in enumerate(self.widgets_tree.get_children()):
            values = self.widgets_tree.item(item, "values")
            internal_name = values[2]  # hidden internal name
            visible = 1 if values[1] == "✓" else 0
            db.execute_query(
                "INSERT INTO user_widgets (user_id, widget_name, widget_order, is_visible) VALUES (?,?,?,?)",
                (self.user_id, internal_name, idx, visible)
            )
        messagebox.showinfo("Success", "Dashboard layout saved.")

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("800x600")
    app = SettingsModule(root)
    root.mainloop()