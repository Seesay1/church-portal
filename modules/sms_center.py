# modules/sms_center.py
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from database import DatabaseManager
import re

try:
    from config import FONT_TEXT, SMS_API_URL
except ImportError:
    FONT_TEXT = ("Segoe UI", 10)
    SMS_API_URL = "https://api.example.com/send_sms"

# Modern color palette
COLORS = {
    "bg": "#f8fafc",
    "card": "#ffffff",
    "accent": "#1f4fa3",
    "accent_light": "#e8f0fe",
    "success": "#10b981",
    "danger": "#ef4444",
    "warning": "#f59e0b",
    "text": "#1e293b",
    "text_light": "#64748b",
    "border": "#e2e8f0"
}

class SMSCenter:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg=COLORS["bg"])
        self.user_id = user_id
        self.branch_id = branch_id

        # Apply custom styling
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background=COLORS["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=COLORS["card"], foreground=COLORS["text"],
                        font=("Segoe UI", 10), padding=[12, 4])
        style.map("TNotebook.Tab", background=[("selected", COLORS["accent_light"])],
                  foreground=[("selected", COLORS["accent"])])
        style.configure("TFrame", background=COLORS["bg"])

        # Main notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=15)

        # Tabs
        self.compose_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.compose_frame, text="✉️ Compose SMS")

        self.history_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.history_frame, text="📋 History")

        self.stats_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        self.birthday_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.birthday_frame, text="🎂 Birthday Reminders")

        self.settings_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.settings_frame, text="⚙️ API Settings")

        # Setup tabs
        self.setup_compose_tab()
        self.setup_history_tab()
        self.setup_stats_tab()
        
        # Load templates before birthday tab (which uses them)
        self.load_templates()
        
        self.setup_birthday_tab()
        self.setup_settings_tab()

        self.load_api_settings()
        self.refresh_stats()

    # ================== HELPER: MODERN CARD ==================
    def create_card(self, parent, title, **kwargs):
        """Create a styled card with title, pack it, and return the inner content frame."""
        card = tk.Frame(parent, bg=COLORS["card"], highlightbackground=COLORS["border"],
                        highlightthickness=1, bd=0, **kwargs)
        card.pack(fill="both", expand=True, pady=5)  # ✅ card is now packed
        title_lbl = tk.Label(card, text=title, bg=COLORS["card"], fg=COLORS["text"],
                             font=("Segoe UI", 12, "bold"), anchor="w")
        title_lbl.pack(fill="x", padx=15, pady=(15, 5))
        content_frame = tk.Frame(card, bg=COLORS["card"])
        content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        return content_frame

    # ================== COMPOSE TAB ==================
    def setup_compose_tab(self):
        main = tk.Frame(self.compose_frame, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Left column – recipient selection and message (expands)
        left = tk.Frame(main, bg=COLORS["bg"])
        left.pack(side="left", fill="both", expand=True, padx=5)

        # Right column – preview and send (fixed width)
        right = tk.Frame(main, bg=COLORS["bg"], width=400)
        right.pack(side="right", fill="y", padx=5)
        right.pack_propagate(False)  # Prevent the frame from shrinking

        # Recipient card
        recipient_content = self.create_card(left, "Recipients", height=200)
        tk.Label(recipient_content, text="Recipient Type:", bg=COLORS["card"],
                font=("Segoe UI", 10), fg=COLORS["text"]).pack(anchor="w", pady=(5,0))
        self.recipient_type = ttk.Combobox(recipient_content,
                                        values=["All Members", "Branch", "Group", "Custom Numbers"],
                                        font=("Segoe UI", 10), state="readonly")
        self.recipient_type.pack(fill="x", pady=5)
        self.recipient_type.set("All Members")
        self.recipient_type.bind("<<ComboboxSelected>>", self.toggle_recipient_fields)

        self.recipient_label = tk.Label(recipient_content, text="Enter Branch/Group Name:",
                                        bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 10))
        self.recipient_label.pack(anchor="w", pady=(10,0))
        self.recipient_entry = tk.Entry(recipient_content, font=("Segoe UI", 10),
                                        bg="#f1f5f9", bd=0, relief="flat")
        self.recipient_entry.pack(fill="x", pady=5, ipady=5)

        # Initially hide
        self.recipient_label.pack_forget()
        self.recipient_entry.pack_forget()

        self.custom_note = tk.Label(recipient_content,
                                    text="Enter phone numbers separated by commas or newlines",
                                    bg=COLORS["card"], fg=COLORS["text_light"], font=("Segoe UI", 9))
        self.custom_note.pack_forget()

        # Template selection
        tk.Label(recipient_content, text="Message Template:", bg=COLORS["card"],
                font=("Segoe UI", 10), fg=COLORS["text"]).pack(anchor="w", pady=(15,0))
        self.template_combo = ttk.Combobox(recipient_content, values=[], font=("Segoe UI", 10))
        self.template_combo.pack(fill="x", pady=5)
        self.template_combo.bind("<<ComboboxSelected>>", self.load_template)

        # Message card
        message_content = self.create_card(left, "Message", height=250)
        self.message_text = tk.Text(message_content, height=6, font=("Segoe UI", 11),
                                    wrap="word", bd=0, bg="#f1f5f9", padx=10, pady=10)
        self.message_text.pack(fill="both", expand=True)
        self.message_text.bind("<KeyRelease>", self.update_char_count)

        self.char_count_label = tk.Label(message_content, text="0 / 160 (1 SMS)",
                                        bg=COLORS["card"], fg=COLORS["text_light"],
                                        font=("Segoe UI", 9))
        self.char_count_label.pack(anchor="e", pady=5)

        # Right column: preview card
        preview_content = self.create_card(right, "Preview")
        self.preview_text = tk.Text(preview_content, height=10, font=("Segoe UI", 11),
                                    wrap="word", bd=0, bg="#f1f5f9", padx=10, pady=10,
                                    state="disabled")
        self.preview_text.pack(fill="both", expand=True)

        # Send button (directly in right frame, below preview card)
        send_btn = tk.Button(right, text="📨 Send SMS", bg=COLORS["accent"], fg="white",
                            font=("Segoe UI", 14, "bold"), bd=0, cursor="hand2",
                            command=self.send_sms, padx=20, pady=10)
        send_btn.pack(pady=20)
        send_btn.bind("<Enter>", lambda e: send_btn.config(bg="#163a7a"))
        send_btn.bind("<Leave>", lambda e: send_btn.config(bg=COLORS["accent"]))

    def toggle_recipient_fields(self, event=None):
        rt = self.recipient_type.get()
        if rt in ["Branch", "Group"]:
            self.recipient_label.config(text=f"Enter {rt} Name:")
            self.recipient_label.pack(anchor="w", pady=(10,0))
            self.recipient_entry.pack(fill="x", pady=5, ipady=5)
            self.custom_note.pack_forget()
        elif rt == "Custom Numbers":
            self.recipient_label.config(text="Phone Numbers:")
            self.recipient_label.pack(anchor="w", pady=(10,0))
            self.recipient_entry.pack(fill="x", pady=5, ipady=5)
            self.custom_note.pack(anchor="w")
        else:
            self.recipient_label.pack_forget()
            self.recipient_entry.pack_forget()
            self.custom_note.pack_forget()
        self.update_preview()

    def load_templates(self):
        """Load predefined message templates."""
        self.templates = {
            "Welcome": "Welcome to PCG Mt. Zion! We're glad to have you.",
            "Event Reminder": "Reminder: {event} is on {date}. Don't miss it!",
            "Attendance": "Your attendance for today has been recorded. Thank you.",
            "Birthday": "Happy Birthday! May God bless you abundantly.",
            "Custom": ""
        }
        self.template_combo['values'] = list(self.templates.keys())
        self.template_combo.set("Custom")

    def load_template(self, event=None):
        name = self.template_combo.get()
        if name in self.templates:
            self.message_text.delete(1.0, tk.END)
            self.message_text.insert(1.0, self.templates[name])
            self.update_char_count()
            self.update_preview()

    def update_char_count(self, event=None):
        text = self.message_text.get(1.0, tk.END).strip()
        length = len(text)
        segments = (length // 153) + 1 if length > 160 else 1
        self.char_count_label.config(text=f"{length} / 160 ({segments} SMS)")
        self.update_preview()

    def update_preview(self):
        text = self.message_text.get(1.0, tk.END).strip()
        self.preview_text.config(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, text if text else "Your message preview will appear here...")
        self.preview_text.config(state="disabled")

    def send_sms(self):
        recipient_type = self.recipient_type.get()
        message = self.message_text.get(1.0, tk.END).strip()
        if not recipient_type:
            messagebox.showerror("Error", "Select recipient type")
            return
        if not message:
            messagebox.showerror("Error", "Enter a message")
            return

        db = DatabaseManager()
        # Get API settings
        api_key = self.api_key_entry.get().strip() if hasattr(self, 'api_key_entry') else ""
        api_url = self.api_url_entry.get().strip() if hasattr(self, 'api_url_entry') else "https://sms.arkesel.com/sms/api"
        sender_id = self.sender_id_entry.get().strip() if hasattr(self, 'sender_id_entry') else "PCG"

        # Fetch phone numbers
        phones = []
        if recipient_type == "All Members":
            query = "SELECT phone FROM members WHERE phone IS NOT NULL AND phone != ''"
            rows = db.fetch_all(query)
            phones = [r[0] for r in rows]
        elif recipient_type == "Branch":
            branch = self.recipient_entry.get().strip()
            if not branch:
                messagebox.showerror("Error", "Enter branch name")
                return
            query = """
                SELECT m.phone FROM members m
                LEFT JOIN branches b ON m.branch_id = b.id
                WHERE b.name = ? AND m.phone IS NOT NULL AND m.phone != ''
            """
            rows = db.fetch_all(query, (branch,))
            phones = [r[0] for r in rows]
        elif recipient_type == "Group":
            group = self.recipient_entry.get().strip()
            if not group:
                messagebox.showerror("Error", "Enter group name")
                return
            query = """
                SELECT m.phone FROM members m
                LEFT JOIN groups g ON m.group_id = g.id
                WHERE g.name = ? AND m.phone IS NOT NULL AND m.phone != ''
            """
            rows = db.fetch_all(query, (group,))
            phones = [r[0] for r in rows]
        elif recipient_type == "Custom Numbers":
            numbers = self.recipient_entry.get().strip()
            if not numbers:
                messagebox.showerror("Error", "Enter phone numbers")
                return
            phones = re.split(r'[,\n\s]+', numbers)
            phones = [p.strip() for p in phones if p.strip()]

        if not phones:
            messagebox.showwarning("No Recipients", "No valid phone numbers found")
            return

        # Check internet
        try:
            requests.get("https://www.google.com", timeout=5)
        except:
            messagebox.showerror("No Internet", "Internet connection required to send SMS")
            return

        # Send
        success_count = 0
        failed_phones = []
        date_sent = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for phone in phones:
            try:
                params = {
                    "action": "send-sms",
                    "api_key": api_key,
                    "to": phone,
                    "from": sender_id,
                    "sms": message
                }
                # First attempt: GET
                response = requests.get(api_url, params=params, timeout=10)
                print(f"GET response: {response.status_code} - {response.text[:200]}")
                
                # If GET returns 405, try POST with form data
                if response.status_code == 405:
                    print("GET not allowed, trying POST...")
                    response = requests.post(api_url, data=params, timeout=10)
                    print(f"POST response: {response.status_code} - {response.text[:200]}")
                
                if response.status_code == 200 and "success" in response.text.lower():
                    status = "Sent"
                    success_count += 1
                else:
                    status = f"Failed: {response.status_code} - {response.text[:50]}"
                    failed_phones.append(phone)
            except Exception as e:
                status = f"Error: {str(e)[:50]}"
                failed_phones.append(phone)

            # Log
            db.execute_query(
                "INSERT INTO sms_logs (phone, message, status, date_sent) VALUES (?,?,?,?)",
                (phone, message[:100], status, date_sent)
            )

        if success_count == len(phones):
            messagebox.showinfo("Success", f"SMS sent successfully to {success_count} recipients!")
        else:
            msg = f"Sent to {success_count} of {len(phones)}.\nFailed: {', '.join(failed_phones[:5])}"
            if len(failed_phones) > 5:
                msg += f" and {len(failed_phones)-5} more"
            messagebox.showwarning("Partial Success", msg)

        self.load_history()
        self.refresh_stats()

    # ================== HISTORY TAB ==================
    def setup_history_tab(self):
        toolbar = tk.Frame(self.history_frame, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=10, pady=10)

        tk.Button(toolbar, text="🔄 Refresh", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 10), command=self.load_history,
                  bd=0, padx=15, pady=5).pack(side="left", padx=5)
        tk.Button(toolbar, text="🗑️ Delete Selected", bg=COLORS["danger"], fg="white",
                  font=("Segoe UI", 10), command=self.delete_history,
                  bd=0, padx=15, pady=5).pack(side="left", padx=5)

        tk.Label(toolbar, text="Status:", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(20,5))
        self.status_filter = ttk.Combobox(toolbar, values=["All", "Sent", "Failed"],
                                          state="readonly", width=10)
        self.status_filter.pack(side="left", padx=5)
        self.status_filter.set("All")
        self.status_filter.bind("<<ComboboxSelected>>", lambda e: self.filter_history())

        tk.Label(toolbar, text="Search Phone:", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(side="left", padx=(20,5))
        self.phone_search = tk.Entry(toolbar, font=("Segoe UI", 10), bg="white", bd=1,
                                     relief="solid", width=15)
        self.phone_search.pack(side="left", padx=5)
        self.phone_search.bind("<KeyRelease>", lambda e: self.filter_history())

        tree_frame = tk.Frame(self.history_frame, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Phone", "Message Preview", "Status", "Date Sent")
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                         yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.history_tree.yview)
        hsb.config(command=self.history_tree.xview)

        col_widths = {"ID": 50, "Phone": 130, "Message Preview": 400, "Status": 150, "Date Sent": 150}
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=col_widths[col], minwidth=50, anchor="w")
            if col == "ID":
                self.history_tree.column(col, anchor="center")

        self.history_tree.pack(fill="both", expand=True)

        self.all_history = []
        self.load_history()

    def load_history(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        self.all_history.clear()

        db = DatabaseManager()
        rows = db.fetch_all("SELECT id, phone, message, status, date_sent FROM sms_logs ORDER BY date_sent DESC")

        for r in rows:
            msg_preview = r[2][:60] + "..." if len(r[2]) > 60 else r[2]
            status = r[3] if r[3] else "Unknown"
            date_sent = r[4] if r[4] else ""

            tag = "sent" if "sent" in status.lower() else "failed"
            item = self.history_tree.insert("", tk.END, values=(r[0], r[1], msg_preview, status, date_sent), tags=(tag,))
            self.all_history.append((item, r[1], status.lower(), date_sent, status))

        self.history_tree.tag_configure("sent", background="#e8f5e9", foreground="#006400")
        self.history_tree.tag_configure("failed", background="#ffebee", foreground="#b71c1c")

        self.filter_history()

    def filter_history(self):
        filter_status = self.status_filter.get()
        search_term = self.phone_search.get().strip().lower()

        for item_id, phone, stat_lower, date_sent, raw_status in self.all_history:
            should_show = True

            if filter_status != "All":
                if "Sent" in filter_status:
                    if "sent" not in stat_lower: should_show = False
                elif "Failed" in filter_status:
                    if "sent" in stat_lower: should_show = False
                else:
                    if filter_status.lower() not in stat_lower: should_show = False

            if search_term and search_term not in phone:
                should_show = False

            if should_show:
                self.history_tree.reattach(item_id, "", "end")
            else:
                self.history_tree.detach(item_id)

    def delete_history(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select entries to delete")
            return
        if not messagebox.askyesno("Confirm", "Delete selected history entries?"):
            return
        db = DatabaseManager()
        for item in selected:
            db_id = self.history_tree.item(item, "values")[0]
            db.execute_query("DELETE FROM sms_logs WHERE id = ?", (db_id,))
        self.load_history()
        self.history_tree.selection_remove(self.history_tree.selection())
        messagebox.showinfo("Success", f"{len(selected)} entries deleted")

    # ================== STATISTICS TAB ==================
    def setup_stats_tab(self):
        control = tk.Frame(self.stats_frame, bg=COLORS["bg"])
        control.pack(fill="x", padx=10, pady=10)

        tk.Label(control, text="SMS Analytics", font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(side="left", padx=10)

        self.refresh_stats_btn = tk.Button(control, text="🔄 Refresh", bg=COLORS["accent"], fg="white",
                                           font=("Segoe UI", 10), command=self.refresh_stats,
                                           bd=0, padx=15, pady=5)
        self.refresh_stats_btn.pack(side="right", padx=5)

        self.stats_charts_frame = tk.Frame(self.stats_frame, bg=COLORS["bg"])
        self.stats_charts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        if self.notebook.index("current") == 2:
            self.refresh_stats()

    def refresh_stats(self):
        for widget in self.stats_charts_frame.winfo_children():
            widget.destroy()

        db = DatabaseManager()

        # Top summary cards
        summary_frame = tk.Frame(self.stats_charts_frame, bg=COLORS["bg"])
        summary_frame.pack(fill="x", pady=10)

        total = db.fetch_one("SELECT COUNT(*) FROM sms_logs")[0] or 0
        sent = db.fetch_one("SELECT COUNT(*) FROM sms_logs WHERE status LIKE '%Sent%'")[0] or 0
        failed = db.fetch_one("SELECT COUNT(*) FROM sms_logs WHERE status NOT LIKE '%Sent%'")[0] or 0

        self._create_stat_card(summary_frame, "Total SMS", total, COLORS["accent"])
        self._create_stat_card(summary_frame, "Successful", sent, COLORS["success"])
        self._create_stat_card(summary_frame, "Failed", failed, COLORS["danger"])

        # Charts
        chart_frame = tk.Frame(self.stats_charts_frame, bg=COLORS["bg"])
        chart_frame.pack(fill="both", expand=True)

        left = tk.Frame(chart_frame, bg=COLORS["bg"])
        left.pack(side="left", fill="both", expand=True, padx=5)
        right = tk.Frame(chart_frame, bg=COLORS["bg"])
        right.pack(side="right", fill="both", expand=True, padx=5)

        self._draw_pie_chart(left)
        self._draw_bar_chart(right)

    def _create_stat_card(self, parent, label, value, color):
        card = tk.Frame(parent, bg="white", highlightbackground=COLORS["border"],
                        highlightthickness=1, bd=0)
        card.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        tk.Label(card, text=label, bg="white", fg=COLORS["text_light"],
                 font=("Segoe UI", 10)).pack(pady=(10,0))
        tk.Label(card, text=str(value), bg="white", fg=color,
                 font=("Segoe UI", 24, "bold")).pack(pady=(0,10))

    def _draw_pie_chart(self, parent):
        db = DatabaseManager()
        stats = db.fetch_all("SELECT status, COUNT(*) FROM sms_logs GROUP BY status")
        fig = Figure(figsize=(5,4), dpi=100, facecolor=COLORS["bg"])
        ax = fig.add_subplot(111)

        if stats:
            labels = [s[0] for s in stats]
            sizes = [s[1] for s in stats]
            colors = [COLORS["success"] if "sent" in l.lower() else COLORS["danger"] for l in labels]
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.set_title("SMS Status Distribution", fontsize=12, color=COLORS["text"])
        else:
            ax.text(0.5, 0.5, "No SMS Data", ha='center', va='center', fontsize=12)
            ax.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_bar_chart(self, parent):
        db = DatabaseManager()
        daily = db.fetch_all("""
            SELECT strftime('%Y-%m-%d', date_sent) as day, COUNT(*)
            FROM sms_logs
            WHERE date_sent IS NOT NULL
            GROUP BY day
            ORDER BY day DESC
            LIMIT 7
        """)
        fig = Figure(figsize=(5,4), dpi=100, facecolor=COLORS["bg"])
        ax = fig.add_subplot(111)

        if daily:
            daily_rev = list(reversed(daily))
            days = [d[0][5:] for d in daily_rev]  # MM-DD
            counts = [d[1] for d in daily_rev]
            ax.bar(days, counts, color=COLORS["accent"])
            ax.set_title("Last 7 Days Volume", fontsize=12, color=COLORS["text"])
            ax.set_xlabel("Date")
            ax.set_ylabel("Count")
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            fig.tight_layout()
        else:
            ax.text(0.5, 0.5, "No Daily Data", ha='center', va='center', fontsize=12)
            ax.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ================== BIRTHDAY REMINDERS TAB ==================
    def setup_birthday_tab(self):
        main = tk.Frame(self.birthday_frame, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # Controls
        ctrl = tk.Frame(main, bg=COLORS["bg"])
        ctrl.pack(fill="x", pady=5)

        tk.Label(ctrl, text="Remind for birthdays in the next:", bg=COLORS["bg"],
                 fg=COLORS["text"], font=("Segoe UI", 10)).pack(side="left", padx=5)
        self.bday_days = ttk.Combobox(ctrl, values=["7 days", "14 days", "30 days"], width=10)
        self.bday_days.pack(side="left", padx=5)
        self.bday_days.set("7 days")
        self.bday_days.bind("<<ComboboxSelected>>", lambda e: self.load_birthdays())

        tk.Button(ctrl, text="🔍 Preview", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 10), command=self.load_birthdays,
                  bd=0, padx=15, pady=5).pack(side="left", padx=20)

        # Treeview to display birthdays
        tree_frame = tk.Frame(main, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, pady=10)

        columns = ("ID", "Name", "Birth Date", "Phone", "Days Until")
        self.bday_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col in columns:
            self.bday_tree.heading(col, text=col)
        self.bday_tree.column("ID", width=50)
        self.bday_tree.column("Name", width=200)
        self.bday_tree.column("Birth Date", width=100)
        self.bday_tree.column("Phone", width=130)
        self.bday_tree.column("Days Until", width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bday_tree.yview)
        self.bday_tree.configure(yscrollcommand=scrollbar.set)
        self.bday_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Template selection for birthday message
        msg_frame = tk.Frame(main, bg=COLORS["bg"])
        msg_frame.pack(fill="x", pady=5)

        tk.Label(msg_frame, text="Message Template:", bg=COLORS["bg"],
                 fg=COLORS["text"], font=("Segoe UI", 10)).pack(side="left", padx=5)
        self.bday_template = ttk.Combobox(msg_frame, values=["Birthday", "Custom"], width=20)
        self.bday_template.pack(side="left", padx=5)
        self.bday_template.set("Birthday")
        self.bday_template.bind("<<ComboboxSelected>>", self.load_bday_template)

        # Preview of message
        self.bday_preview = tk.Text(msg_frame, height=3, font=("Segoe UI", 10),
                                    bg="#f1f5f9", bd=0, padx=10, pady=5, wrap="word")
        self.bday_preview.pack(side="left", fill="x", expand=True, padx=10)
        self.bday_preview.insert(1.0, self.templates.get("Birthday", "Happy Birthday!"))

        # Send button
        btn_frame = tk.Frame(main, bg=COLORS["bg"])
        btn_frame.pack(fill="x", pady=10)
        tk.Button(btn_frame, text="📨 Send Birthday Wishes", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 12, "bold"), command=self.send_birthday_sms,
                  bd=0, padx=20, pady=10).pack()

        self.load_birthdays()

    def load_birthdays(self):
        for row in self.bday_tree.get_children():
            self.bday_tree.delete(row)

        days = int(self.bday_days.get().split()[0])
        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        db = DatabaseManager()
        members = db.fetch_all("SELECT id, full_name, birth_date, phone FROM members WHERE birth_date IS NOT NULL")
        upcoming = []
        for mid, name, bdate, phone in members:
            if not bdate or not phone:
                continue
            try:
                bday = datetime.strptime(bdate, "%Y-%m-%d").date()
                next_bday = bday.replace(year=today.year)
                if next_bday < today:
                    next_bday = next_bday.replace(year=today.year + 1)
                if today <= next_bday <= end_date:
                    days_until = (next_bday - today).days
                    upcoming.append((mid, name, bdate, phone, days_until))
            except:
                continue

        upcoming.sort(key=lambda x: x[4])

        if not upcoming:
            # Insert a placeholder row with a custom tag
            self.bday_tree.insert("", tk.END, values=("", "✨ No upcoming birthdays", "", "", ""),
                                tags=("placeholder",))
            self.bday_tree.tag_configure("placeholder", foreground=COLORS["text_light"],
                                        font=("Segoe UI", 10, "italic"))
            return

        for u in upcoming:
            self.bday_tree.insert("", tk.END, values=u)

    def load_bday_template(self, event=None):
        tmpl = self.bday_template.get()
        if tmpl == "Birthday":
            msg = self.templates.get("Birthday", "Happy Birthday!")
        else:
            msg = ""
        self.bday_preview.delete(1.0, tk.END)
        self.bday_preview.insert(1.0, msg)

    def send_birthday_sms(self):
        selected = self.bday_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select members to send birthday wishes.")
            return

        message = self.bday_preview.get(1.0, tk.END).strip()
        if not message:
            messagebox.showerror("Error", "Message cannot be empty.")
            return

        if not messagebox.askyesno("Confirm", f"Send birthday wishes to {len(selected)} member(s)?"):
            return

        db = DatabaseManager()
        api_key = self.api_key_entry.get().strip() if hasattr(self, 'api_key_entry') else ""
        api_url = self.api_url_entry.get().strip() if hasattr(self, 'api_url_entry') else "https://sms.arkesel.com/sms/api"
        sender_id = self.sender_id_entry.get().strip() if hasattr(self, 'sender_id_entry') else "PCG"
        date_sent = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        success_count = 0
        failed = []

        for item in selected:
            values = self.bday_tree.item(item, "values")
            member_id = values[0]
            phone = values[3]
            name = values[1]

            if not phone:
                failed.append(f"{name} (no phone)")
                continue

            personalized = message.replace("{name}", name)

            try:
                params = {
                    "action": "send-sms",
                    "api_key": api_key,
                    "to": phone,
                    "from": sender_id,
                    "sms": personalized
                }
                # First attempt: GET
                response = requests.get(api_url, params=params, timeout=10)
                print(f"GET response: {response.status_code} - {response.text[:200]}")
                
                if response.status_code == 405:
                    print("GET not allowed, trying POST...")
                    response = requests.post(api_url, data=params, timeout=10)
                    print(f"POST response: {response.status_code} - {response.text[:200]}")
                
                if response.status_code == 200 and "success" in response.text.lower():
                    status = "Sent"
                    success_count += 1
                else:
                    status = f"Failed: {response.status_code} - {response.text[:50]}"
                    failed.append(phone)
            except Exception as e:
                status = f"Error: {str(e)[:50]}"
                failed.append(phone)

            db.execute_query(
                "INSERT INTO sms_logs (phone, message, status, date_sent) VALUES (?,?,?,?)",
                (phone, personalized[:100], status, date_sent)
            )

        if success_count == len(selected):
            messagebox.showinfo("Success", f"Birthday wishes sent to {success_count} members!")
        else:
            msg = f"Sent to {success_count} of {len(selected)}.\nFailed: {', '.join(failed[:5])}"
            if len(failed) > 5:
                msg += f" and {len(failed)-5} more"
            messagebox.showwarning("Partial Success", msg)

        self.load_birthdays()
        self.refresh_stats()

    # ================== SETTINGS TAB ==================
    def setup_settings_tab(self):
        main = tk.Frame(self.settings_frame, bg=COLORS["bg"])
        main.pack(expand=True, fill="both", padx=20, pady=20)

        tk.Label(main, text="SMS API Configuration", font=("Segoe UI", 16, "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(pady=10)

        card = tk.Frame(main, bg=COLORS["card"], highlightbackground=COLORS["border"],
                        highlightthickness=1, bd=0)
        card.pack(fill="x", padx=20, pady=10)

        tk.Label(card, text="API URL:", bg=COLORS["card"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(15,5))
        self.api_url_entry = tk.Entry(card, font=("Segoe UI", 10), width=50,
                                      bg="#f1f5f9", bd=0, relief="flat")
        self.api_url_entry.pack(fill="x", padx=20, pady=5, ipady=5)

        tk.Label(card, text="API Key:", bg=COLORS["card"], fg=COLORS["text"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(10,5))
        self.api_key_entry = tk.Entry(card, font=("Segoe UI", 10), width=50, show="*",
                                      bg="#f1f5f9", bd=0, relief="flat")
        self.api_key_entry.pack(fill="x", padx=20, pady=5, ipady=5)

        tk.Button(main, text="💾 Save Settings", bg=COLORS["accent"], fg="white",
                  font=("Segoe UI", 12, "bold"), command=self.save_api_settings,
                  bd=0, padx=30, pady=10).pack(pady=20)

        self.load_api_settings()


        # Sender ID
        tk.Label(card, text="Sender ID (e.g., PCG):", bg=COLORS["card"], fg=COLORS["text"],
                font=("Segoe UI", 10)).pack(anchor="w", padx=20, pady=(10,5))
        self.sender_id_entry = tk.Entry(card, font=("Segoe UI", 10), width=50,
                                        bg="#f1f5f9", bd=0, relief="flat")
        self.sender_id_entry.pack(fill="x", padx=20, pady=5, ipady=5)
    
    
    def load_api_settings(self):
        db = DatabaseManager()
        url = db.fetch_one("SELECT value FROM settings WHERE key='sms_api_url'")
        key = db.fetch_one("SELECT value FROM settings WHERE key='sms_api_key'")
        sender = db.fetch_one("SELECT value FROM settings WHERE key='sms_sender_id'")
        if hasattr(self, 'api_url_entry'):
            self.api_url_entry.delete(0, tk.END)
            self.api_url_entry.insert(0, url[0] if url else "https://sms.arkesel.com/sms/api")
        if hasattr(self, 'api_key_entry'):
            self.api_key_entry.delete(0, tk.END)
            self.api_key_entry.insert(0, key[0] if key else "")
        if hasattr(self, 'sender_id_entry'):
            self.sender_id_entry.delete(0, tk.END)
            self.sender_id_entry.insert(0, sender[0] if sender else "PCG")

    def save_api_settings(self):
        url = self.api_url_entry.get().strip()
        key = self.api_key_entry.get().strip()
        sender = self.sender_id_entry.get().strip()
        db = DatabaseManager()
        # Save API URL
        if db.fetch_one("SELECT value FROM settings WHERE key='sms_api_url'"):
            db.execute_query("UPDATE settings SET value=? WHERE key='sms_api_url'", (url,))
        else:
            db.execute_query("INSERT INTO settings (key, value) VALUES ('sms_api_url', ?)", (url,))
        # Save API Key
        if db.fetch_one("SELECT value FROM settings WHERE key='sms_api_key'"):
            db.execute_query("UPDATE settings SET value=? WHERE key='sms_api_key'", (key,))
        else:
            db.execute_query("INSERT INTO settings (key, value) VALUES ('sms_api_key', ?)", (key,))
        # Save Sender ID
        if db.fetch_one("SELECT value FROM settings WHERE key='sms_sender_id'"):
            db.execute_query("UPDATE settings SET value=? WHERE key='sms_sender_id'", (sender,))
        else:
            db.execute_query("INSERT INTO settings (key, value) VALUES ('sms_sender_id', ?)", (sender,))
        messagebox.showinfo("Success", "API settings saved")
        self.load_api_settings()

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x700")
    root.title("SMS Center")
    app = SMSCenter(root)
    root.mainloop()