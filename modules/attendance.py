import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
from database import DatabaseManager
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from datetime import datetime, timedelta

FONT_TEXT = ("Helvetica", 10)

class AttendanceModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")

        # Create a Notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Attendance Entry
        self.entry_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.entry_frame, text="📋 Attendance Entry")

        # Tab 2: Statistics
        self.stats_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        # ---------- Attendance Entry Tab ----------
        self.setup_entry_tab()

        # ---------- Statistics Tab ----------
        self.setup_stats_tab()

        # Load initial data for entry tab
        self.load_filters()
        self.load_members()

    # ================== ENTRY TAB ==================
    def setup_entry_tab(self):
        # Top toolbar
        toolbar = tk.Frame(self.entry_frame, bg="#e8f1ff")
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        # Date selection
        tk.Label(toolbar, text="Select Date:", font=FONT_TEXT, bg="#e8f1ff").pack(side="left", padx=5)
        self.date_entry = DateEntry(
            toolbar, font=FONT_TEXT, width=12,
            background='blue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd'
        )
        self.date_entry.pack(side="left", padx=5)
        self.date_entry.bind("<<DateEntrySelected>>", lambda e: self.load_members())

        # Buttons
        self.load_btn = tk.Button(toolbar, text="📋 Load Members", bg="#1f4fa3", fg="#fff",
                                   font=FONT_TEXT, command=self.load_members)
        self.load_btn.pack(side="left", padx=5)

        self.save_btn = tk.Button(toolbar, text="💾 Save Attendance", bg="#d62828", fg="#fff",
                                   font=FONT_TEXT, command=self.save_attendance)
        self.save_btn.pack(side="left", padx=5)

        self.mark_all_btn = tk.Button(toolbar, text="✅ Mark All Present", bg="#2a9df4", fg="#fff",
                                       font=FONT_TEXT, command=self.mark_all_present)
        self.mark_all_btn.pack(side="left", padx=5)

        self.unmark_all_btn = tk.Button(toolbar, text="⬜ Mark All Absent", bg="#6c757d", fg="#fff",
                                         font=FONT_TEXT, command=self.mark_all_absent)
        self.unmark_all_btn.pack(side="left", padx=5)

        # Present count
        self.count_label = tk.Label(toolbar, text="Present: 0 / 0", font=FONT_TEXT,
                                    bg="#e8f1ff", fg="#1f4fa3")
        self.count_label.pack(side="right", padx=10)

        # ---------- Filter Frame ----------
        filter_frame = tk.Frame(self.entry_frame, bg="#e8f1ff")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Search by name/ID
        tk.Label(filter_frame, text="🔍 Search:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda a,b,c: self.filter_members())
        self.search_entry = tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_TEXT, width=20)
        self.search_entry.pack(side="left", padx=5)

        # Branch filter
        tk.Label(filter_frame, text="Branch:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(filter_frame, textvariable=self.branch_var,
                                         values=["All"], state="readonly", width=15)
        self.branch_combo.pack(side="left", padx=5)
        self.branch_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        # Group filter
        tk.Label(filter_frame, text="Group:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(filter_frame, textvariable=self.group_var,
                                        values=["All"], state="readonly", width=15)
        self.group_combo.pack(side="left", padx=5)
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        # Department filter
        tk.Label(filter_frame, text="Department:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.dept_var = tk.StringVar()
        self.dept_combo = ttk.Combobox(filter_frame, textvariable=self.dept_var,
                                       values=["All"], state="readonly", width=15)
        self.dept_combo.pack(side="left", padx=5)
        self.dept_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        # Status filter
        tk.Label(filter_frame, text="Status:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var,
                                         values=["All", "Present", "Absent"], state="readonly", width=10)
        self.status_combo.pack(side="left", padx=5)
        self.status_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        # Clear filters button
        tk.Button(filter_frame, text="✖ Clear Filters", bg="#e8f1ff", fg="#d62828",
                  font=FONT_TEXT, command=self.clear_filters).pack(side="left", padx=5)

        # ---------- Treeview with Scrollbars ----------
        tree_frame = tk.Frame(self.entry_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("Member ID", "Full Name", "Branch", "Group", "Department", "Present", "DB_ID")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        col_widths = [100, 180, 100, 100, 100, 80, 0]
        for col, w in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=20 if w>0 else 0, stretch=False)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.toggle_present)

        self.all_members = []  # store all items for filtering

    def load_filters(self):
        """Populate branch, group, department comboboxes from database."""
        db = DatabaseManager()
        branches = [r[0] for r in db.fetch_all("SELECT name FROM branches ORDER BY name")]
        groups = [r[0] for r in db.fetch_all("SELECT name FROM groups ORDER BY name")]
        depts = [r[0] for r in db.fetch_all("SELECT name FROM departments ORDER BY name")]

        self.branch_combo['values'] = ["All"] + branches
        self.group_combo['values'] = ["All"] + groups
        self.dept_combo['values'] = ["All"] + depts

        self.branch_var.set("All")
        self.group_var.set("All")
        self.dept_var.set("All")
        self.status_var.set("All")

    def load_members(self):
        """Load members and pre-fill attendance for selected date."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.all_members.clear()

        db = DatabaseManager()
        date_str = self.date_entry.get_date().strftime("%Y-%m-%d")

        # Fetch all members
        query = """
            SELECT m.id, m.member_id, m.full_name, b.name, g.name, d.name
            FROM members m
            LEFT JOIN branches b ON m.branch_id = b.id
            LEFT JOIN groups g ON m.group_id = g.id
            LEFT JOIN departments d ON m.department_id = d.id
            ORDER BY m.full_name
        """
        members = db.fetch_all(query)

        # Fetch existing attendance for this date
        att_map = {}
        att_data = db.fetch_all("SELECT member_id, present FROM attendance WHERE date = ?", (date_str,))
        for mid, pres in att_data:
            att_map[mid] = pres

        for m in members:
            internal_id, member_id, full_name, branch, group, dept = m
            present = att_map.get(internal_id, 0)
            present_display = "✅" if present else "⬜"

            item_id = self.tree.insert("", tk.END, values=(
                member_id or "",
                full_name or "",
                branch or "",
                group or "",
                dept or "",
                present_display,
                internal_id
            ))
            # Store for filtering: (item_id, branch, group, dept, present_display, search_text)
            search_text = f"{member_id} {full_name} {branch} {group} {dept}".lower()
            self.all_members.append((item_id, branch, group, dept, present_display, search_text))

        self.update_present_count()
        self.filter_members()

    def filter_members(self):
        """Apply all filters to the treeview."""
        search_term = self.search_var.get().strip().lower()
        branch_filter = self.branch_var.get()
        group_filter = self.group_var.get()
        dept_filter = self.dept_var.get()
        status_filter = self.status_var.get()

        for item_id, branch, group, dept, present_display, search_text in self.all_members:
            # Check each filter
            if branch_filter != "All" and branch != branch_filter:
                self.tree.detach(item_id)
                continue
            if group_filter != "All" and group != group_filter:
                self.tree.detach(item_id)
                continue
            if dept_filter != "All" and dept != dept_filter:
                self.tree.detach(item_id)
                continue
            if status_filter == "Present" and present_display != "✅":
                self.tree.detach(item_id)
                continue
            if status_filter == "Absent" and present_display != "⬜":
                self.tree.detach(item_id)
                continue
            if search_term and search_term not in search_text:
                self.tree.detach(item_id)
                continue

            # If all filters pass, ensure item is attached
            self.tree.reattach(item_id, "", "end")

    def clear_filters(self):
        self.search_var.set("")
        self.branch_var.set("All")
        self.group_var.set("All")
        self.dept_var.set("All")
        self.status_var.set("All")
        self.filter_members()

    def toggle_present(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        current = self.tree.set(item, "Present")
        new = "⬜" if current == "✅" else "✅"
        self.tree.set(item, "Present", new)
        self.update_present_count()

    def mark_all_present(self):
        for item in self.tree.get_children():
            self.tree.set(item, "Present", "✅")
        self.update_present_count()

    def mark_all_absent(self):
        for item in self.tree.get_children():
            self.tree.set(item, "Present", "⬜")
        self.update_present_count()

    def update_present_count(self):
        total = len(self.tree.get_children())
        present = sum(1 for item in self.tree.get_children() if self.tree.set(item, "Present") == "✅")
        self.count_label.config(text=f"Present: {present} / {total}")

    def save_attendance(self):
        date_str = self.date_entry.get_date().strftime("%Y-%m-%d")
        db = DatabaseManager()

        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            member_db_id = values[6]
            present_val = 1 if values[5] == "✅" else 0

            existing = db.fetch_one("SELECT id FROM attendance WHERE member_id=? AND date=?", (member_db_id, date_str))
            if existing:
                db.execute_query("UPDATE attendance SET present=? WHERE member_id=? AND date=?",
                                 (present_val, member_db_id, date_str))
            else:
                member_info = db.fetch_one("SELECT branch_id, group_id FROM members WHERE id=?", (member_db_id,))
                if member_info:
                    b_id, g_id = member_info
                    db.execute_query("INSERT INTO attendance (member_id, branch_id, group_id, date, present) VALUES (?,?,?,?,?)",
                                     (member_db_id, b_id, g_id, date_str, present_val))

        messagebox.showinfo("Success", f"Attendance for {date_str} saved successfully!")
        self.load_members()  # reload to reflect any changes (optional)

    # ================== STATISTICS TAB ==================
    def setup_stats_tab(self):
        # Control frame
        control_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="Select Date for Pie Chart:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.stats_date_entry = DateEntry(
            control_frame, font=FONT_TEXT, width=12,
            background='blue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd'
        )
        self.stats_date_entry.pack(side="left", padx=5)
        self.stats_date_entry.set_date(datetime.today())

        self.refresh_stats_btn = tk.Button(control_frame, text="🔄 Refresh Stats", bg="#1f4fa3", fg="#fff",
                                           font=FONT_TEXT, command=self.refresh_stats)
        self.refresh_stats_btn.pack(side="left", padx=10)

        # Frame for charts
        self.charts_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        self.charts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.pie_canvas = None
        self.bar_canvas = None

        # Bind tab selection to refresh stats when stats tab is opened
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        if self.notebook.index("current") == 1:  # Statistics tab selected
            self.refresh_stats()

    def refresh_stats(self):
        # Clear previous charts
        for widget in self.charts_frame.winfo_children():
            widget.destroy()

        # Create two subframes for pie and bar
        pie_frame = tk.Frame(self.charts_frame, bg="#e8f1ff")
        pie_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        bar_frame = tk.Frame(self.charts_frame, bg="#e8f1ff")
        bar_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Generate pie chart for selected date
        self.draw_pie_chart(pie_frame)

        # Generate bar chart for last 7 days
        self.draw_trend_chart(bar_frame)

    def draw_pie_chart(self, parent):
        date_str = self.stats_date_entry.get_date().strftime("%Y-%m-%d")
        db = DatabaseManager()

        # Count present and absent for the date
        present_count = db.fetch_one("SELECT COUNT(*) FROM attendance WHERE date=? AND present=1", (date_str,))
        absent_count = db.fetch_one("SELECT COUNT(*) FROM attendance WHERE date=? AND present=0", (date_str,))
        present = present_count[0] if present_count else 0
        absent = absent_count[0] if absent_count else 0

        if present == 0 and absent == 0:
            # No attendance records for this date
            fig = Figure(figsize=(5,4), dpi=100)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No attendance data\nfor selected date", ha='center', va='center', fontsize=12)
            ax.axis('off')
        else:
            fig = Figure(figsize=(5,4), dpi=100)
            ax = fig.add_subplot(111)
            labels = ['Present', 'Absent']
            sizes = [present, absent]
            colors = ['#2a9df4', '#d62828']
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.set_title(f'Attendance on {date_str}')

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def draw_trend_chart(self, parent):
        db = DatabaseManager()
        end_date = datetime.today().date()
        start_date = end_date - timedelta(days=6)

        dates = []
        present_counts = []
        total_members = db.fetch_one("SELECT COUNT(*) FROM members")[0] or 0

        for i in range(7):
            day = start_date + timedelta(days=i)
            date_str = day.strftime("%Y-%m-%d")
            dates.append(day.strftime("%m/%d"))
            # Count present members on that day
            cnt = db.fetch_one("SELECT COUNT(*) FROM attendance WHERE date=? AND present=1", (date_str,))
            present_counts.append(cnt[0] if cnt else 0)

        fig = Figure(figsize=(5,4), dpi=100)
        ax = fig.add_subplot(111)
        ax.bar(dates, present_counts, color="#2a9df4")
        ax.set_title("Attendance Trend (Last 7 Days)")
        ax.set_xlabel("Date")
        ax.set_ylabel("Present Count")
        ax.set_ylim(0, total_members if total_members else 10)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1300x700")
    app = AttendanceModule(root)
    root.mainloop()