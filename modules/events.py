# modules/events.py
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from database import DatabaseManager
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import csv
from tkinter import ttk, messagebox, filedialog

FONT_TEXT = ("Helvetica", 10)

class EventsModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")
        self.editing_event_id = None

        # Create Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Events List
        self.list_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.list_frame, text="📋 Events List")

        # Tab 2: Statistics
        self.stats_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        self.setup_list_tab()
        self.setup_stats_tab()

        # Load initial data
        self.load_filters()
        self.load_events()

    # ================== EVENTS LIST TAB ==================
    def setup_list_tab(self):
        # ---------- Top Toolbar ----------
        toolbar = tk.Frame(self.list_frame, bg="#e8f1ff")
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        # Buttons on left
        btn_frame = tk.Frame(toolbar, bg="#e8f1ff")
        btn_frame.pack(side="left", fill="x", expand=True)

        tk.Button(btn_frame, text="➕ Add Event", width=15, bg="#d62828", fg="#fff",
                  font=FONT_TEXT, command=self.add_event).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✏️ Edit Selected", width=15, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete Selected", width=15, bg="#333", fg="#fff",
                  font=FONT_TEXT, command=self.delete_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📄 Export", width=10, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.export_events).pack(side="left", padx=5)

        # NEW: View Registrations button
        btn_reg = tk.Button(btn_frame, text="👥 View Registrations", width=18, bg="#1f4fa3", fg="#fff",
                            font=FONT_TEXT, command=self.view_selected_registrations)
        btn_reg.pack(side="left", padx=5)

        # ---------- Filter Bar ----------
        filter_frame = tk.Frame(self.list_frame, bg="#e8f1ff")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Search
        tk.Label(filter_frame, text="🔍 Search:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda a,b,c: self.filter_events())
        tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_TEXT, width=20).pack(side="left", padx=5)

        # Date Range
        tk.Label(filter_frame, text="From:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.date_from = DateEntry(filter_frame, width=10, background='blue', foreground='white',
                                   borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.date_from.pack(side="left", padx=2)
        self.date_from.set_date(datetime.now() - timedelta(days=30))

        tk.Label(filter_frame, text="To:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.date_to = DateEntry(filter_frame, width=10, background='blue', foreground='white',
                                 borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.date_to.pack(side="left", padx=2)
        self.date_to.set_date(datetime.now() + timedelta(days=90))

        # Branch/Group filter
        tk.Label(filter_frame, text="Branch/Group:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.bg_var = tk.StringVar()
        self.bg_combo = ttk.Combobox(filter_frame, textvariable=self.bg_var,
                                      values=["All"], state="readonly", width=15)
        self.bg_combo.pack(side="left", padx=5)
        self.bg_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_events())

        # Apply Filters button
        tk.Button(filter_frame, text="Apply", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.filter_events).pack(side="left", padx=5)

        # Clear filters
        tk.Button(filter_frame, text="✖ Clear", bg="#e8f1ff", fg="#d62828",
                  font=FONT_TEXT, command=self.clear_filters).pack(side="left", padx=5)

        # ---------- Treeview ----------
        tree_frame = tk.Frame(self.list_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        # Columns: ID (hidden), Name, Date, Time, Location, Branch/Group, Capacity, Registrations
        columns = ("id", "name", "date", "time", "location", "branch_group", "capacity", "registrations")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Headings
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Event Name")
        self.tree.heading("date", text="Date")
        self.tree.heading("time", text="Time")
        self.tree.heading("location", text="Location")
        self.tree.heading("branch_group", text="Branch/Group")
        self.tree.heading("capacity", text="Capacity")
        self.tree.heading("registrations", text="Registered")

        # Column widths
        self.tree.column("id", width=0, stretch=False)          # hidden
        self.tree.column("name", width=200, minwidth=150)
        self.tree.column("date", width=100)
        self.tree.column("time", width=80)
        self.tree.column("location", width=150)
        self.tree.column("branch_group", width=120)
        self.tree.column("capacity", width=80)
        self.tree.column("registrations", width=100)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_event)  # double-click to edit

        # Store all events for filtering
        self.all_events = []

    def load_filters(self):
        """Populate branch/group combobox from database."""
        db = DatabaseManager()
        rows = db.fetch_all("SELECT DISTINCT branch_group FROM events WHERE branch_group IS NOT NULL AND branch_group != '' ORDER BY branch_group")
        values = [r[0] for r in rows]
        self.bg_combo['values'] = ["All"] + values
        self.bg_combo.set("All")

    def load_events(self):
        """Load all events from database, including registration count."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.all_events.clear()

        db = DatabaseManager()
        query = """
            SELECT e.id, e.name, e.date, e.time, e.location, e.branch_group, e.capacity,
                   (SELECT COUNT(*) FROM event_registrations WHERE event_id = e.id) as reg_count
            FROM events e
            ORDER BY e.date, e.time
        """
        rows = db.fetch_all(query)

        for r in rows:
            values = [
                r[0],               # id (hidden)
                r[1] or "",
                r[2] or "",
                r[3] or "",
                r[4] or "",
                r[5] or "",
                r[6] or "",
                r[7]                 # registrations count
            ]
            item_id = self.tree.insert("", tk.END, values=values)
            # Store for filtering: search_text (name + location + branch_group)
            search_text = f"{r[1] or ''} {r[4] or ''} {r[5] or ''}".lower()
            self.all_events.append((item_id, r[2] or "", r[5] or "", search_text))

        self.filter_events()

    def filter_events(self):
        """Apply filters to the treeview."""
        search_term = self.search_var.get().strip().lower()
        date_from = self.date_from.get_date()
        date_to = self.date_to.get_date()
        branch_group_filter = self.bg_var.get()

        for item_id, date_str, branch_group, search_text in self.all_events:
            show = True

            # Date filter
            if date_str:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if event_date < date_from or event_date > date_to:
                    show = False

            # Branch/Group filter
            if show and branch_group_filter != "All" and branch_group != branch_group_filter:
                show = False

            # Search filter
            if show and search_term and search_term not in search_text:
                show = False

            if show:
                self.tree.reattach(item_id, "", "end")
            else:
                self.tree.detach(item_id)

    def clear_filters(self):
        self.search_var.set("")
        self.date_from.set_date(datetime.now() - timedelta(days=30))
        self.date_to.set_date(datetime.now() + timedelta(days=90))
        self.bg_var.set("All")
        self.filter_events()

    def export_events(self):
        """Export current filtered events to CSV."""
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                  filetypes=[("CSV files", "*.csv")])
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Event Name", "Date", "Time", "Location", "Branch/Group", "Capacity", "Registrations"])
                for item in self.tree.get_children():
                    values = self.tree.item(item)['values']
                    writer.writerow(values)
            messagebox.showinfo("Export", "Events exported successfully.")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ---------- CRUD Operations ----------
    def add_event(self):
        self._event_form("Add Event")

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an event to edit.")
            return
        event_id = self.tree.item(selected[0])['values'][0]
        self._event_form("Edit Event", event_id)

    def edit_event(self, event):
        selected = self.tree.selection()
        if selected:
            event_id = self.tree.item(selected[0])['values'][0]
            self._event_form("Edit Event", event_id)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an event to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected event(s)?"):
            return
        db = DatabaseManager()
        for item in selected:
            event_id = self.tree.item(item)['values'][0]
            db.execute_query("DELETE FROM events WHERE id = ?", (event_id,))
        self.load_events()
        self.tree.selection_remove(self.tree.selection())
        messagebox.showinfo("Success", f"{len(selected)} event(s) deleted.")
        self._update_dashboard_badge()

    # ---------- Event Form (Add/Edit) ----------
    def _event_form(self, title, event_id=None):
        self.editing_event_id = event_id
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("450x550")
        win.configure(bg="#e8f1ff")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        win.lift()
        win.focus_force()

        # Event Name
        tk.Label(win, text="Event Name *", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.event_name_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.event_name_entry.pack(pady=5)

        # Date
        tk.Label(win, text="Date *", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.date_entry = DateEntry(
            win, font=FONT_TEXT, width=16, background='blue',
            foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd'
        )
        self.date_entry.pack(pady=5)

        # Time
        tk.Label(win, text="Time * (HH:MM)", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.time_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.time_entry.pack(pady=5)

        # Location
        tk.Label(win, text="Location", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.location_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.location_entry.pack(pady=5)

        # Branch/Group
        tk.Label(win, text="Branch/Group", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.bg_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.bg_entry.pack(pady=5)

        # Capacity
        tk.Label(win, text="Capacity (optional)", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.capacity_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.capacity_entry.pack(pady=5)

        # Load data if editing
        if event_id:
            self._load_event_data(event_id)

        # Buttons
        btn_frame = tk.Frame(win, bg="#e8f1ff")
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Cancel", bg="#888888", fg="#fff",
                  font=FONT_TEXT, width=10, command=win.destroy).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save", bg="#d62828", fg="#fff",
                  font=FONT_TEXT, width=10, command=self.save_event).pack(side="left", padx=5)

        win.bind("<Return>", lambda e: self.save_event())

    def _load_event_data(self, event_id):
        db = DatabaseManager()
        event = db.fetch_one("SELECT name, date, time, location, branch_group, capacity FROM events WHERE id=?", (event_id,))
        if event:
            self.event_name_entry.insert(0, event[0] or "")
            self.date_entry.set_date(event[1] if event[1] else datetime.now())
            self.time_entry.insert(0, event[2] or "")
            self.location_entry.insert(0, event[3] or "")
            self.bg_entry.insert(0, event[4] or "")
            self.capacity_entry.insert(0, event[5] if event[5] else "")

    def save_event(self):
        name = self.event_name_entry.get().strip()
        date_str = self.date_entry.get_date().strftime("%Y-%m-%d")
        time_str = self.time_entry.get().strip()
        location = self.location_entry.get().strip()
        branch_group = self.bg_entry.get().strip()
        capacity = self.capacity_entry.get().strip()
        capacity = int(capacity) if capacity.isdigit() else None

        if not name or not date_str or not time_str:
            messagebox.showerror("Error", "Event name, date, and time are required!")
            return

        db = DatabaseManager()

        if self.editing_event_id:
            # Update
            query = """
                UPDATE events SET name=?, date=?, time=?, location=?, branch_group=?, capacity=?
                WHERE id=?
            """
            success = db.execute_query(query, (name, date_str, time_str, location, branch_group, capacity, self.editing_event_id))
            if success:
                messagebox.showinfo("Success", f"Event '{name}' updated.")
                self._close_form_and_refresh()
            else:
                messagebox.showerror("Error", "Failed to update event.")
        else:
            # Check duplicate
            existing = db.fetch_one(
                "SELECT id FROM events WHERE name=? AND date=? AND time=?",
                (name, date_str, time_str)
            )
            if existing:
                messagebox.showerror("Error", "An event with the same name, date, and time already exists.")
                return
            # Insert
            query = "INSERT INTO events (name, date, time, location, branch_group, capacity) VALUES (?,?,?,?,?,?)"
            success = db.execute_query(query, (name, date_str, time_str, location, branch_group, capacity))
            if success:
                messagebox.showinfo("Success", f"Event '{name}' added.")
                self._close_form_and_refresh()
            else:
                messagebox.showerror("Error", "Failed to save event.")

    def _close_form_and_refresh(self):
        if hasattr(self, 'add_win') and self.add_win:
            self.add_win.destroy()
        self.load_events()
        self.load_filters()
        self.notebook.select(0)  # switch to list tab
        self._update_dashboard_badge()

    def _update_dashboard_badge(self):
        """Notify the dashboard to refresh its notification badge."""
        dashboard = self.root.winfo_toplevel()
        if hasattr(dashboard, 'force_notification_update'):
            dashboard.force_notification_update()

    # ================== EVENT REGISTRATIONS ==================
    def get_event_registrations(self, event_id):
        """Fetch all members registered for a given event."""
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT m.member_id, m.full_name, m.phone, m.email, er.registered_at, er.attended
            FROM event_registrations er
            JOIN members m ON er.member_id = m.id
            WHERE er.event_id = ?
            ORDER BY er.registered_at DESC
        """, (event_id,))
        return rows

    def show_registrations(self, event_id):
        """Open a new window with the list of registrations."""
        reg_window = tk.Toplevel(self.root)
        reg_window.title("Event Registrations")
        reg_window.geometry("800x400")

        # Fetch data
        registrations = self.get_event_registrations(event_id)

        # Treeview to display
        columns = ("Member ID", "Full Name", "Phone", "Email", "Registered On", "Attended")
        tree = ttk.Treeview(reg_window, columns=columns, show="headings")
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        tree.column("Registered On", width=150)
        tree.column("Attended", width=80)

        for reg in registrations:
            attended_str = "Yes" if reg[5] == 1 else "No"
            tree.insert("", "end", values=(reg[0], reg[1], reg[2], reg[3], reg[4], attended_str))

        tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Export button
        def export_csv():
            file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                      filetypes=[("CSV files", "*.csv")])
            if file_path:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    for reg in registrations:
                        attended_str = "Yes" if reg[5] == 1 else "No"
                        writer.writerow((reg[0], reg[1], reg[2], reg[3], reg[4], attended_str))
                messagebox.showinfo("Export", "Registrations exported successfully.")

        btn_export = tk.Button(reg_window, text="Export to CSV", command=export_csv)
        btn_export.pack(pady=5)

    def view_selected_registrations(self):
        """Called when 'View Registrations' button is clicked."""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an event.")
            return
        # Get the event ID from the hidden first column
        event_id = self.tree.item(selected[0])['values'][0]
        self.show_registrations(event_id)

    # ================== STATISTICS TAB ==================
    def setup_stats_tab(self):
        control_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="Event Statistics", font=("Helvetica", 14, "bold"),
                 bg="#e8f1ff", fg="#1f4fa3").pack(side="left", padx=10)

        self.refresh_stats_btn = tk.Button(control_frame, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                                           font=FONT_TEXT, command=self.refresh_stats)
        self.refresh_stats_btn.pack(side="right", padx=5)

        # Frame for charts
        self.stats_charts_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        self.stats_charts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        if self.notebook.index("current") == 1:  # Statistics tab
            self.refresh_stats()

    def refresh_stats(self):
        for widget in self.stats_charts_frame.winfo_children():
            widget.destroy()

        # Create left and right frames
        left_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        left_frame.pack(side="left", fill="both", expand=True, padx=5)
        right_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        right_frame.pack(side="right", fill="both", expand=True, padx=5)

        self.draw_upcoming_count(left_frame)
        self.draw_monthly_chart(right_frame)
        self.draw_branch_pie(left_frame)  # will place under the count

    def draw_upcoming_count(self, parent):
        db = DatabaseManager()
        today = datetime.now().strftime("%Y-%m-%d")
        thirty_days = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        count = db.fetch_one("SELECT COUNT(*) FROM events WHERE date BETWEEN ? AND ?", (today, thirty_days))
        count = count[0] if count else 0

        # Card
        card = tk.Frame(parent, bg="white", bd=1, relief="solid")
        card.pack(fill="x", pady=5, padx=5, ipadx=10, ipady=10)
        tk.Label(card, text="📅 Upcoming Events (Next 30 Days)", font=("Helvetica", 12, "bold"),
                 bg="white", fg="#1f4fa3").pack()
        tk.Label(card, text=str(count), font=("Helvetica", 24, "bold"),
                 bg="white", fg="#d62828").pack()

    def draw_monthly_chart(self, parent):
        db = DatabaseManager()
        year = datetime.now().year
        data = db.fetch_all("""
            SELECT strftime('%m', date), COUNT(*) 
            FROM events 
            WHERE date LIKE ?
            GROUP BY strftime('%m', date)
            ORDER BY 1
        """, (f"{year}%",))

        months = [str(m).zfill(2) for m in range(1,13)]
        counts = [0]*12
        for row in data:
            month_idx = int(row[0]) - 1
            if 0 <= month_idx < 12:
                counts[month_idx] = row[1]

        fig = Figure(figsize=(5,3), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(months, counts, color="#2a9df4")
        ax.set_title(f"Events by Month ({year})")
        ax.set_xlabel("Month")
        ax.set_ylabel("Count")
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def draw_branch_pie(self, parent):
        db = DatabaseManager()
        data = db.fetch_all("""
            SELECT branch_group, COUNT(*) 
            FROM events 
            WHERE branch_group IS NOT NULL AND branch_group != ''
            GROUP BY branch_group
            ORDER BY COUNT(*) DESC
        """)
        if not data:
            card = tk.Frame(parent, bg="white", bd=1, relief="solid")
            card.pack(fill="x", pady=5, padx=5, ipadx=10, ipady=10)
            tk.Label(card, text="No branch/group data", bg="white").pack()
            return

        labels = [r[0] for r in data]
        sizes = [r[1] for r in data]
        fig = Figure(figsize=(5,3), dpi=100)
        ax = fig.add_subplot(111)
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        ax.set_title("Events by Branch/Group")
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x700")
    app = EventsModule(root)
    root.mainloop()