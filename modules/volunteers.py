# modules/volunteers.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import DatabaseManager
from datetime import datetime
import csv
from tkcalendar import DateEntry

try:
    from config import FONT_TEXT
except ImportError:
    FONT_TEXT = ("Segoe UI", 10)

# Modern color palette
COLOR_BG = "#f4f7fb"
COLOR_SURFACE = "#ffffff"
COLOR_PRIMARY = "#1f4fa3"
COLOR_PRIMARY_DARK = "#163d82"
COLOR_ACCENT = "#3b82f6"
COLOR_SUCCESS = "#10b981"
COLOR_WARNING = "#f59e0b"
COLOR_DANGER = "#ef4444"
COLOR_MUTED = "#6b7280"
COLOR_TEXT = "#111827"
COLOR_BORDER = "#dbe3ef"
COLOR_ROW_ALT = "#f9fbff"

TITLE_FONT = ("Segoe UI", 20, "bold")
SUBTITLE_FONT = ("Segoe UI", 10)
CARD_TITLE_FONT = ("Segoe UI", 10)
CARD_VALUE_FONT = ("Segoe UI", 18, "bold")
BTN_FONT = ("Segoe UI", 10, "bold")
LABEL_FONT = ("Segoe UI", 10, "bold")
ENTRY_FONT = ("Segoe UI", 10)


class VolunteersModule:
    def __init__(self, parent, user_id=None, branch_id=None):
        self.parent = parent
        self.user_id = user_id
        self.branch_id = branch_id

        self.search_var = tk.StringVar()
        self.status_var = tk.StringVar(value="All")
        self.branch_filter_var = tk.StringVar(value="All")   # new

        self.main_frame = tk.Frame(parent, bg=COLOR_BG)
        self.main_frame.pack(fill="both", expand=True)

        self._setup_styles()
        self.setup_ui()
        self.load_opportunities()

    # ---------------- STYLES ----------------
    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(
            "Vol.Treeview",
            background="white",
            foreground=COLOR_TEXT,
            rowheight=34,
            fieldbackground="white",
            borderwidth=0,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Vol.Treeview.Heading",
            background=COLOR_PRIMARY,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            relief="flat"
        )

        style.map(
            "Vol.Treeview",
            background=[("selected", "#dbeafe")],
            foreground=[("selected", COLOR_TEXT)]
        )

        style.configure(
            "Modern.TCombobox",
            padding=6,
            fieldbackground="white"
        )

    # ---------------- UI ----------------
    def setup_ui(self):
        self._build_header()
        self._build_summary_cards()
        self._build_toolbar()
        self._build_table()

    def _build_header(self):
        header = tk.Frame(self.main_frame, bg=COLOR_BG)
        header.pack(fill="x", padx=18, pady=(18, 10))

        left = tk.Frame(header, bg=COLOR_BG)
        left.pack(side="left", fill="x", expand=True)

        tk.Label(
            left,
            text="Volunteer Opportunities",
            font=TITLE_FONT,
            bg=COLOR_BG,
            fg=COLOR_TEXT
        ).pack(anchor="w")

        tk.Label(
            left,
            text="Manage volunteer roles, schedules, capacity, and member signups in one place.",
            font=SUBTITLE_FONT,
            bg=COLOR_BG,
            fg=COLOR_MUTED
        ).pack(anchor="w", pady=(4, 0))

        right = tk.Frame(header, bg=COLOR_BG)
        right.pack(side="right")

        self.refresh_btn = tk.Button(
            right, text="⟳ Refresh", font=BTN_FONT,
            bg=COLOR_PRIMARY, fg="white", bd=0,
            padx=14, pady=8, cursor="hand2",
            activebackground=COLOR_PRIMARY_DARK,
            activeforeground="white",
            command=self.load_opportunities
        )
        self.refresh_btn.pack(side="right")

    def _create_stat_card(self, parent, title, color):
        card = tk.Frame(parent, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        card.pack(side="left", fill="both", expand=True, padx=6)

        top_bar = tk.Frame(card, bg=color, height=4)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        body = tk.Frame(card, bg=COLOR_SURFACE)
        body.pack(fill="both", expand=True, padx=14, pady=12)

        title_lbl = tk.Label(body, text=title, font=CARD_TITLE_FONT, bg=COLOR_SURFACE, fg=COLOR_MUTED)
        title_lbl.pack(anchor="w")

        value_lbl = tk.Label(body, text="0", font=CARD_VALUE_FONT, bg=COLOR_SURFACE, fg=COLOR_TEXT)
        value_lbl.pack(anchor="w", pady=(6, 0))

        return value_lbl

    def _build_summary_cards(self):
        cards_wrap = tk.Frame(self.main_frame, bg=COLOR_BG)
        cards_wrap.pack(fill="x", padx=18, pady=(0, 14))

        self.total_lbl = self._create_stat_card(cards_wrap, "Total Opportunities", COLOR_ACCENT)
        self.active_lbl = self._create_stat_card(cards_wrap, "Active", COLOR_SUCCESS)
        self.completed_lbl = self._create_stat_card(cards_wrap, "Completed", COLOR_WARNING)
        self.cancelled_lbl = self._create_stat_card(cards_wrap, "Cancelled", COLOR_DANGER)

    def _build_toolbar(self):
        toolbar_card = tk.Frame(self.main_frame, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        toolbar_card.pack(fill="x", padx=18, pady=(0, 12))

        toolbar = tk.Frame(toolbar_card, bg=COLOR_SURFACE)
        toolbar.pack(fill="x", padx=12, pady=12)

        # Left actions
        actions = tk.Frame(toolbar, bg=COLOR_SURFACE)
        actions.pack(side="left")

        self._modern_button(actions, "➕ New", COLOR_PRIMARY, self.add_opportunity).pack(side="left", padx=(0, 8))
        self._modern_button(actions, "✏ Edit", COLOR_SUCCESS, self.edit_selected).pack(side="left", padx=8)
        self._modern_button(actions, "🗑 Delete", COLOR_DANGER, self.delete_selected).pack(side="left", padx=8)
        self._modern_button(actions, "👥 Signups", "#7c3aed", self.view_signups).pack(side="left", padx=8)
        self._modern_button(actions, "📤 Export", "#0f766e", self.export_opportunities_csv).pack(side="left", padx=8)

        # Right tools
        tools = tk.Frame(toolbar, bg=COLOR_SURFACE)
        tools.pack(side="right")

        # Search entry
        search_entry = tk.Entry(
            tools, textvariable=self.search_var, font=ENTRY_FONT,
            width=24, relief="solid", bd=1
        )
        search_entry.pack(side="left", padx=(0, 8), ipady=6)
        search_entry.bind("<KeyRelease>", lambda e: self.load_opportunities())

        # Status filter
        status_combo = ttk.Combobox(
            tools, textvariable=self.status_var,
            values=["All", "active", "completed", "cancelled"],
            state="readonly", width=14, style="Modern.TCombobox"
        )
        status_combo.pack(side="left", padx=(0, 8))
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_opportunities())

        # Branch filter
        db = DatabaseManager()
        branches = db.fetch_all("SELECT id, name FROM branches ORDER BY name")
        self.branch_list = [b[1] for b in branches]
        self.branch_id_map = {b[1]: b[0] for b in branches}

        tk.Label(tools, text="Branch:", bg=COLOR_SURFACE, fg=COLOR_TEXT, font=("Segoe UI", 9)).pack(side="left", padx=(8,2))
        self.branch_filter_combo = ttk.Combobox(
            tools, textvariable=self.branch_filter_var,
            values=["All"] + self.branch_list,
            state="readonly", width=14, style="Modern.TCombobox"
        )
        self.branch_filter_combo.pack(side="left", padx=(0,8))
        self.branch_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.load_opportunities())

    def _build_table(self):
        table_card = tk.Frame(self.main_frame, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        table_card.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        title_row = tk.Frame(table_card, bg=COLOR_SURFACE)
        title_row.pack(fill="x", padx=12, pady=(12, 0))

        tk.Label(
            title_row,
            text="Opportunities List",
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        self.count_badge = tk.Label(
            title_row,
            text="0 records",
            bg="#e8f0ff",
            fg=COLOR_PRIMARY,
            font=("Segoe UI", 9, "bold"),
            padx=10, pady=4
        )
        self.count_badge.pack(side="right")

        table_frame = tk.Frame(table_card, bg=COLOR_SURFACE)
        table_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Added "Branch" column
        columns = ("ID", "Title", "Role", "Date", "Start", "End", "Location", "Branch", "Capacity", "Status")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Vol.Treeview"
        )

        for col in columns:
            self.tree.heading(col, text=col)

        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Title", width=220)
        self.tree.column("Role", width=120)
        self.tree.column("Date", width=100, anchor="center")
        self.tree.column("Start", width=70, anchor="center")
        self.tree.column("End", width=70, anchor="center")
        self.tree.column("Location", width=150)
        self.tree.column("Branch", width=120)
        self.tree.column("Capacity", width=80, anchor="center")
        self.tree.column("Status", width=90, anchor="center")

        self.tree.tag_configure("oddrow", background="white")
        self.tree.tag_configure("evenrow", background=COLOR_ROW_ALT)
        self.tree.tag_configure("active", foreground=COLOR_SUCCESS)
        self.tree.tag_configure("completed", foreground=COLOR_WARNING)
        self.tree.tag_configure("cancelled", foreground=COLOR_DANGER)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self.edit_opportunity)

    def _modern_button(self, parent, text, bg, command):
        return tk.Button(
            parent,
            text=text,
            bg=bg,
            fg="white",
            activebackground=bg,
            activeforeground="white",
            font=BTN_FONT,
            bd=0,
            padx=12,
            pady=8,
            cursor="hand2",
            command=command
        )

    # ---------------- DATA ----------------
    def load_opportunities(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        db = DatabaseManager()

        query = """
            SELECT o.id, o.title, o.role, o.date, o.start_time, o.end_time, o.location,
                   COALESCE(b.name, '') as branch_name, o.capacity, o.status
            FROM volunteer_opportunities o
            LEFT JOIN branches b ON o.branch_id = b.id
            WHERE 1=1
        """
        params = []

        if self.search_var.get().strip():
            search = f"%{self.search_var.get().strip()}%"
            query += " AND (o.title LIKE ? OR o.role LIKE ? OR o.location LIKE ?)"
            params.extend([search, search, search])

        if self.status_var.get() != "All":
            query += " AND o.status=?"
            params.append(self.status_var.get())

        if self.branch_filter_var.get() != "All":
            branch_name = self.branch_filter_var.get()
            branch_id = self.branch_id_map.get(branch_name)
            if branch_id:
                query += " AND o.branch_id = ?"
                params.append(branch_id)

        query += " ORDER BY o.date DESC, o.start_time"

        rows = db.fetch_all(query, tuple(params))

        active_count = 0
        completed_count = 0
        cancelled_count = 0

        for i, r in enumerate(rows):
            # values: id, title, role, date, start, end, location, branch_name, capacity, status
            status = str(r[9]).lower() if r[9] else ""
            if status == "active":
                active_count += 1
            elif status == "completed":
                completed_count += 1
            elif status == "cancelled":
                cancelled_count += 1

            row_tag = "evenrow" if i % 2 == 0 else "oddrow"
            self.tree.insert("", tk.END, values=r, tags=(row_tag, status))

        self.total_lbl.config(text=str(len(rows)))
        self.active_lbl.config(text=str(active_count))
        self.completed_lbl.config(text=str(completed_count))
        self.cancelled_lbl.config(text=str(cancelled_count))
        self.count_badge.config(text=f"{len(rows)} record(s)")

    # ---------------- ACTIONS ----------------
    def add_opportunity(self):
        self._edit_opportunity_window()

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an opportunity.")
            return
        opp_id = self.tree.item(selected[0], "values")[0]
        self._edit_opportunity_window(opp_id)

    def edit_opportunity(self, event=None):
        selected = self.tree.selection()
        if selected:
            opp_id = self.tree.item(selected[0], "values")[0]
            self._edit_opportunity_window(opp_id)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select an opportunity to delete.")
            return

        opp_id = self.tree.item(selected[0], "values")[0]
        title = self.tree.item(selected[0], "values")[1]

        if messagebox.askyesno("Confirm Delete", f"Delete opportunity:\n\n{title}\n\nThis action cannot be undone."):
            db = DatabaseManager()
            db.execute_query("DELETE FROM volunteer_opportunities WHERE id=?", (opp_id,))
            self.load_opportunities()

    def view_signups(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select an opportunity to view signups.")
            return
        opp_id = self.tree.item(selected[0], "values")[0]
        opp_title = self.tree.item(selected[0], "values")[1]
        self._show_signups_window(opp_id, opp_title)

    def export_opportunities_csv(self):
        rows = [self.tree.item(item, "values") for item in self.tree.get_children()]
        if not rows:
            messagebox.showinfo("Export", "No data available to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Export Volunteer Opportunities"
        )
        if not filepath:
            return

        columns = ("ID", "Title", "Role", "Date", "Start", "End", "Location", "Branch", "Capacity", "Status")
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        messagebox.showinfo("Export Successful", "Volunteer opportunities exported successfully.")

    # ---------------- FORM WINDOW ----------------
    def _edit_opportunity_window(self, opp_id=None):
        win = tk.Toplevel(self.parent)
        win.title("Edit Opportunity" if opp_id else "New Opportunity")
        win.geometry("680x700")   # a bit taller to accommodate branch combo
        win.configure(bg=COLOR_BG)
        win.grab_set()
        win.resizable(True, True)

        # Main container with grid to separate scrollable area and footer
        win.grid_rowconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=0)
        win.grid_columnconfigure(0, weight=1)

        # Scrollable canvas area
        canvas_frame = tk.Frame(win, bg=COLOR_BG)
        canvas_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        canvas = tk.Canvas(canvas_frame, bg=COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLOR_BG)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Form inside scrollable frame
        container = tk.Frame(scrollable_frame, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        container.pack(fill="both", expand=True, padx=0, pady=0)

        # Header
        header = tk.Frame(container, bg=COLOR_SURFACE)
        header.pack(fill="x", padx=20, pady=(18, 8))

        tk.Label(
            header,
            text="Edit Volunteer Opportunity" if opp_id else "Create Volunteer Opportunity",
            font=("Segoe UI", 16, "bold"),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Provide the opportunity details below.",
            font=("Segoe UI", 10),
            bg=COLOR_SURFACE,
            fg=COLOR_MUTED
        ).pack(anchor="w", pady=(4, 0))

        # Form fields (using grid)
        form = tk.Frame(container, bg=COLOR_SURFACE)
        form.pack(fill="both", expand=True, padx=20, pady=10)

        for i in range(2):
            form.columnconfigure(i, weight=1)

        def add_label(row, col, text):
            tk.Label(form, text=text, bg=COLOR_SURFACE, fg=COLOR_TEXT, font=LABEL_FONT).grid(
                row=row, column=col, sticky="w", padx=8, pady=(8, 4)
            )

        def add_entry(row, col, width=28):
            e = tk.Entry(form, font=ENTRY_FONT, relief="solid", bd=1, width=width)
            e.grid(row=row, column=col, sticky="ew", padx=8, pady=(0, 8), ipady=6)
            return e

        add_label(0, 0, "Title *")
        title_entry = add_entry(1, 0)

        add_label(0, 1, "Role")
        role_entry = add_entry(1, 1)

        # Date field with DatePicker
        add_label(2, 0, "Date *")
        date_picker = DateEntry(form, font=ENTRY_FONT, width=20, background='white', foreground='black',
                                borderwidth=1, date_pattern='yyyy-mm-dd')
        date_picker.grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))
        date_picker.set_date(datetime.now())

        add_label(2, 1, "Capacity")
        cap_entry = add_entry(3, 1)

        add_label(4, 0, "Start Time (HH:MM)")
        start_entry = add_entry(5, 0)

        add_label(4, 1, "End Time (HH:MM)")
        end_entry = add_entry(5, 1)

        add_label(6, 0, "Location")
        loc_entry = add_entry(7, 0, width=28)

        # Branch selection
        db = DatabaseManager()
        branches = db.fetch_all("SELECT id, name FROM branches ORDER BY name")
        branch_names = ["None"] + [b[1] for b in branches]
        branch_id_map = {b[1]: b[0] for b in branches}

        add_label(6, 1, "Branch")
        branch_combo = ttk.Combobox(form, values=branch_names, state="readonly", style="Modern.TCombobox")
        branch_combo.set("None")
        branch_combo.grid(row=7, column=1, sticky="ew", padx=8, pady=(0, 8))

        add_label(8, 0, "Status")
        status_combo = ttk.Combobox(
            form, values=["active", "completed", "cancelled"],
            state="readonly", style="Modern.TCombobox"
        )
        status_combo.set("active")
        status_combo.grid(row=9, column=0, sticky="ew", padx=8, pady=(0, 8))

        tk.Label(form, text="Description", bg=COLOR_SURFACE, fg=COLOR_TEXT, font=LABEL_FONT).grid(
            row=10, column=0, sticky="w", padx=8, pady=(8, 4)
        )
        desc_text = tk.Text(form, height=7, font=ENTRY_FONT, relief="solid", bd=1, wrap="word")
        desc_text.grid(row=11, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0, 10))

        form.rowconfigure(11, weight=1)

        if opp_id:
            opp = db.fetch_one("""
                SELECT title, role, description, date, start_time, end_time, location, branch_id, capacity, status
                FROM volunteer_opportunities WHERE id=?
            """, (opp_id,))
            if opp:
                title_entry.insert(0, opp[0] or "")
                role_entry.insert(0, opp[1] or "")
                desc_text.insert("1.0", opp[2] or "")
                try:
                    date_picker.set_date(datetime.strptime(opp[3], "%Y-%m-%d"))
                except:
                    pass
                start_entry.insert(0, opp[4] or "")
                end_entry.insert(0, opp[5] or "")
                loc_entry.insert(0, opp[6] or "")
                if opp[7]:
                    branch_name = next((b[1] for b in branches if b[0] == opp[7]), "None")
                    branch_combo.set(branch_name)
                cap_entry.insert(0, str(opp[8]) if opp[8] else "")
                status_combo.set(opp[9] or "active")

        # Fixed footer (outside scrollable area)
        footer = tk.Frame(win, bg=COLOR_BG)
        footer.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        footer.columnconfigure(1, weight=1)

        def validate_time(time_text):
            if not time_text:
                return True
            try:
                datetime.strptime(time_text, "%H:%M")
                return True
            except ValueError:
                return False

        def save():
            title = title_entry.get().strip()
            role = role_entry.get().strip()
            description = desc_text.get("1.0", "end-1c").strip()
            date_val = date_picker.get_date().strftime("%Y-%m-%d")
            start_val = start_entry.get().strip()
            end_val = end_entry.get().strip()
            loc = loc_entry.get().strip()
            branch_name = branch_combo.get()
            branch_id = branch_id_map.get(branch_name) if branch_name != "None" else None
            cap = cap_entry.get().strip()
            status = status_combo.get().strip()

            if not title:
                messagebox.showerror("Validation Error", "Title is required.")
                return

            if not validate_time(start_val):
                messagebox.showerror("Validation Error", "Start time must be in HH:MM format.")
                return

            if not validate_time(end_val):
                messagebox.showerror("Validation Error", "End time must be in HH:MM format.")
                return

            if cap and not cap.isdigit():
                messagebox.showerror("Validation Error", "Capacity must be a valid number.")
                return

            db = DatabaseManager()
            data = (title, role, description, date_val, start_val, end_val, loc, cap, status, branch_id)

            if opp_id:
                query = """
                    UPDATE volunteer_opportunities
                    SET title=?, role=?, description=?, date=?, start_time=?, end_time=?,
                        location=?, capacity=?, status=?, branch_id=?
                    WHERE id=?
                """
                db.execute_query(query, (*data, opp_id))
            else:
                query = """
                    INSERT INTO volunteer_opportunities
                    (title, role, description, date, start_time, end_time, location, capacity, status, created_by, branch_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                db.execute_query(query, (*data, self.user_id, branch_id))

            win.destroy()
            self.load_opportunities()
            messagebox.showinfo("Success", "Opportunity saved successfully.")

        # Cancel and Save buttons in footer
        tk.Button(
            footer, text="Cancel", font=BTN_FONT,
            bg="#e5e7eb", fg=COLOR_TEXT, bd=0,
            padx=14, pady=8, cursor="hand2",
            command=win.destroy
        ).grid(row=0, column=0, padx=(0, 8))

        tk.Button(
            footer,
            text="Save Opportunity",
            font=BTN_FONT,
            bg=COLOR_PRIMARY,
            fg="white",
            bd=0,
            padx=16,
            pady=8,
            cursor="hand2",
            command=save
        ).grid(row=0, column=1, sticky="e")

    # ---------------- SIGNUPS WINDOW ----------------
    def _show_signups_window(self, opp_id, opp_title):
        win = tk.Toplevel(self.parent)
        win.title(f"Volunteer Signups - {opp_title}")
        win.geometry("1020x500")   # wider to include branch
        win.configure(bg=COLOR_BG)
        win.grab_set()

        container = tk.Frame(win, bg=COLOR_SURFACE, highlightthickness=1, highlightbackground=COLOR_BORDER)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        header = tk.Frame(container, bg=COLOR_SURFACE)
        header.pack(fill="x", padx=16, pady=(16, 8))

        tk.Label(
            header,
            text="Volunteer Signups",
            font=("Segoe UI", 16, "bold"),
            bg=COLOR_SURFACE,
            fg=COLOR_TEXT
        ).pack(anchor="w")

        tk.Label(
            header,
            text=opp_title,
            font=("Segoe UI", 10),
            bg=COLOR_SURFACE,
            fg=COLOR_MUTED
        ).pack(anchor="w", pady=(4, 0))

        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT m.member_id, m.full_name, m.phone, m.email, b.name as branch_name, vs.signed_up_at, vs.status
            FROM volunteer_signups vs
            JOIN members m ON vs.member_id = m.id
            LEFT JOIN branches b ON m.branch_id = b.id
            WHERE vs.opportunity_id = ?
            ORDER BY vs.signed_up_at
        """, (opp_id,))

        top_actions = tk.Frame(container, bg=COLOR_SURFACE)
        top_actions.pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(
            top_actions,
            text=f"{len(rows)} signup(s)",
            bg="#eef6ff",
            fg=COLOR_PRIMARY,
            font=("Segoe UI", 9, "bold"),
            padx=10, pady=4
        ).pack(side="left")

        columns = ("Member ID", "Name", "Phone", "Email", "Branch", "Signed Up", "Status")
        tree_frame = tk.Frame(container, bg=COLOR_SURFACE)
        tree_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", style="Vol.Treeview")
        for col in columns:
            tree.heading(col, text=col)

        tree.column("Member ID", width=100, anchor="center")
        tree.column("Name", width=160)
        tree.column("Phone", width=120)
        tree.column("Email", width=170)
        tree.column("Branch", width=120)
        tree.column("Signed Up", width=150, anchor="center")
        tree.column("Status", width=100, anchor="center")

        tree.tag_configure("oddrow", background="white")
        tree.tag_configure("evenrow", background=COLOR_ROW_ALT)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        for i, r in enumerate(rows):
            # r = (member_id, full_name, phone, email, branch_name, signed_up_at, status)
            tree.insert("", tk.END, values=r, tags=("evenrow" if i % 2 == 0 else "oddrow",))

        def export_csv():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV", "*.csv")],
                title="Export Volunteer Signups"
            )
            if filepath:
                with open(filepath, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    for row in rows:
                        writer.writerow(row)
                messagebox.showinfo("Export", "Exported successfully.")

        footer = tk.Frame(container, bg=COLOR_SURFACE)
        footer.pack(fill="x", padx=16, pady=(0, 14))

        tk.Button(
            footer,
            text="Export CSV",
            bg="#0f766e",
            fg="white",
            font=BTN_FONT,
            bd=0,
            padx=14,
            pady=8,
            cursor="hand2",
            command=export_csv
        ).pack(side="right")