# modules/service_planning.py
from modules.audit_helper import log_action
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from database import DatabaseManager
from theme import (
    COLORS, FONTS, PAD, SMALL_PAD,
    ToolTip, styled_button, show_toast, get_color
)


# ===================== THEME =====================
COLOR_BLUE = get_color("primary")
COLOR_LIGHT_BLUE = get_color("highlight")
COLOR_RED = get_color("danger")
COLOR_GREEN = get_color("success")
COLOR_PURPLE = "#8e44ad"
COLOR_WHITE = "#ffffff"
COLOR_BG = get_color("bg")
COLOR_TEXT = get_color("text")
COLOR_MUTED = get_color("text_muted")
COLOR_BORDER = get_color("border")


# ===================== MAIN MODULE =====================
class ServicePlanningModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.user_id = user_id
        self.branch_id = branch_id

        self.root.configure(bg=COLOR_BG)

        self.editing_service_id = None
        self.add_win = None
        self.service_type_win = None
        self.entries = {}
        self.all_services = []
        self.service_type_combo = None
        self.service_type_records = []
        self.editing_service_type_id = None

        self._setup_styles()
        self._build_main_layout()
        self.load_filters()
        self.load_services()

    # ===================== STYLES =====================
    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview",
            background=COLOR_WHITE,
            fieldbackground=COLOR_WHITE,
            foreground=COLOR_TEXT,
            rowheight=25,
            bordercolor=COLOR_BORDER,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=COLOR_BLUE,
            foreground="white",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Treeview.Heading", background=[("active", "#285fc0")])

        style.configure("TNotebook", background=COLOR_BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(10, 6), font=("Segoe UI", 9, "bold"))
        style.map("TNotebook.Tab", background=[("selected", COLOR_WHITE)])

    # ===================== MAIN LAYOUT =====================
    def _build_main_layout(self):
        # Create Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Service Schedule
        self.schedule_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.schedule_frame, text="📅 Service Schedule")

        # Tab 2: Order of Service
        self.order_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.order_frame, text="📋 Order of Service")

        # Tab 3: Song Library
        self.songs_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.songs_frame, text="🎵 Song Library")

        # Tab 4: Sermons
        self.sermons_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.sermons_frame, text="📖 Sermons")

        # Tab 5: Service Teams
        self.teams_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.teams_frame, text="👥 Service Teams")

        self.setup_schedule_tab()
        self.setup_order_tab()
        self.setup_songs_tab()
        self.setup_sermons_tab()
        self.setup_teams_tab()

    # ===================== SCHEDULE TAB =====================
    def setup_schedule_tab(self):
        # ---------- Top Toolbar ----------
        toolbar = tk.Frame(self.schedule_frame, bg=COLOR_BG)
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        btn_frame = tk.Frame(toolbar, bg=COLOR_BG)
        btn_frame.pack(side="left", fill="x", expand=True)

        tk.Button(btn_frame, text="Add", width=10, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.add_service).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Edit", width=10, bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=self.edit_service).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete", width=12, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.delete_service).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Manage Order", width=13, bg=COLOR_PURPLE, fg="#fff",
                  font=FONTS["text"], command=self.manage_order).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Service Types", width=13, bg="#0f766e", fg="#fff",
                  font=FONTS["text"], command=self.open_service_type_manager).pack(side="left", padx=5)

        # ---------- Filter Bar ----------
        filter_frame = tk.Frame(self.schedule_frame, bg=COLOR_BG)
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Date Range
        tk.Label(filter_frame, text="From:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=5)
        self.date_from = DateEntry(filter_frame, width=10, background='blue', foreground='white',
                                   borderwidth=2, date_pattern='yyyy-mm-dd', font=FONTS["text"])
        self.date_from.pack(side="left", padx=2)
        self.date_from.set_date(datetime.now() - timedelta(days=30))

        tk.Label(filter_frame, text="To:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=5)
        self.date_to = DateEntry(filter_frame, width=10, background='blue', foreground='white',
                                 borderwidth=2, date_pattern='yyyy-mm-dd', font=FONTS["text"])
        self.date_to.pack(side="left", padx=2)
        self.date_to.set_date(datetime.now() + timedelta(days=60))

        tk.Button(filter_frame, text="🔍 Filter", bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=self.load_services).pack(side="left", padx=10)

        # Status Filter
        tk.Label(filter_frame, text="Status:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=15)
        self.status_var = tk.StringVar()
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, width=12, 
                                     values=["All", "Scheduled", "In Progress", "Completed", "Cancelled"],
                                     state="readonly")
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.load_services())
        status_combo.set("All")

        # ---------- Services Treeview ----------
        tree_frame = tk.Frame(self.schedule_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "date", "type", "title", "theme", "start_time", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.tree.heading("id", text="ID")
        self.tree.heading("date", text="Date")
        self.tree.heading("type", text="Type")
        self.tree.heading("title", text="Title")
        self.tree.heading("theme", text="Theme")
        self.tree.heading("start_time", text="Start Time")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=40)
        self.tree.column("date", width=90)
        self.tree.column("type", width=100)
        self.tree.column("title", width=180)
        self.tree.column("theme", width=150)
        self.tree.column("start_time", width=80)
        self.tree.column("status", width=90)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.edit_service())

    # ===================== ORDER OF SERVICE TAB =====================
    def setup_order_tab(self):
        # Service selector
        selector_frame = tk.Frame(self.order_frame, bg=COLOR_BG)
        selector_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(selector_frame, text="Select Service:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=5)
        self.order_service_var = tk.StringVar()
        self.order_service_combo = ttk.Combobox(selector_frame, textvariable=self.order_service_var, width=30, state="readonly")
        self.order_service_combo.pack(side="left", padx=5)
        self.order_service_combo.bind("<<ComboboxSelected>>", lambda e: self.load_order_items())

        tk.Button(selector_frame, text="Add Item", width=12, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.add_order_item).pack(side="left", padx=10)
        tk.Button(selector_frame, text="Move Up", width=10, bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=lambda: self.move_item(-1)).pack(side="left", padx=2)
        tk.Button(selector_frame, text="Move Down", width=10, bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=lambda: self.move_item(1)).pack(side="left", padx=2)
        tk.Button(selector_frame, text="Delete", width=10, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.delete_order_item).pack(side="left", padx=2)

        # Order items tree
        tree_frame = tk.Frame(self.order_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("order", "type", "title", "duration", "assigned_to", "notes")
        self.order_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.order_tree.heading("order", text="#")
        self.order_tree.heading("type", text="Type")
        self.order_tree.heading("title", text="Title")
        self.order_tree.heading("duration", text="Duration (min)")
        self.order_tree.heading("assigned_to", text="Assigned To")
        self.order_tree.heading("notes", text="Notes")

        self.order_tree.column("order", width=40)
        self.order_tree.column("type", width=120)
        self.order_tree.column("title", width=180)
        self.order_tree.column("duration", width=80)
        self.order_tree.column("assigned_to", width=150)
        self.order_tree.column("notes", width=200)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.order_tree.yview)
        self.order_tree.configure(yscrollcommand=scrollbar.set)

        self.order_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Load services for selector
        self.load_service_selector()

    # ===================== SONGS TAB =====================
    def setup_songs_tab(self):
        toolbar = tk.Frame(self.songs_frame, bg=COLOR_BG)
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        tk.Button(toolbar, text="Add Song", width=12, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.add_song).pack(side="left", padx=5)
        tk.Button(toolbar, text="Edit", width=10, bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=self.edit_song).pack(side="left", padx=5)
        tk.Button(toolbar, text="Delete", width=12, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.delete_song).pack(side="left", padx=5)

        # Search
        tk.Label(toolbar, text="🔍 Search:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=20)
        self.song_search = tk.Entry(toolbar, width=20, font=FONTS["text"])
        self.song_search.pack(side="left", padx=5)
        self.song_search.bind("<KeyRelease>", lambda e: self.load_songs())

        tree_frame = tk.Frame(self.songs_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "title", "artist", "key", "tempo", "category")
        self.songs_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.songs_tree.heading("id", text="ID")
        self.songs_tree.heading("title", text="Title")
        self.songs_tree.heading("artist", text="Artist")
        self.songs_tree.heading("key", text="Key")
        self.songs_tree.heading("tempo", text="Tempo")
        self.songs_tree.heading("category", text="Category")

        self.songs_tree.column("id", width=40)
        self.songs_tree.column("title", width=200)
        self.songs_tree.column("artist", width=150)
        self.songs_tree.column("key", width=60)
        self.songs_tree.column("tempo", width=80)
        self.songs_tree.column("category", width=120)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.songs_tree.yview)
        self.songs_tree.configure(yscrollcommand=scrollbar.set)

        self.songs_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_songs()

    # ===================== SERMONS TAB =====================
    def setup_sermons_tab(self):
        toolbar = tk.Frame(self.sermons_frame, bg=COLOR_BG)
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        tk.Button(toolbar, text="Add Sermon", width=14, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.add_sermon).pack(side="left", padx=5)
        tk.Button(toolbar, text="Edit", width=10, bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=self.edit_sermon).pack(side="left", padx=5)
        tk.Button(toolbar, text="Delete", width=12, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.delete_sermon).pack(side="left", padx=5)

        tree_frame = tk.Frame(self.sermons_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "title", "scripture", "preacher", "date", "duration")
        self.sermons_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.sermons_tree.heading("id", text="ID")
        self.sermons_tree.heading("title", text="Title")
        self.sermons_tree.heading("scripture", text="Scripture")
        self.sermons_tree.heading("preacher", text="Preacher")
        self.sermons_tree.heading("date", text="Date")
        self.sermons_tree.heading("duration", text="Duration (min)")

        self.sermons_tree.column("id", width=40)
        self.sermons_tree.column("title", width=250)
        self.sermons_tree.column("scripture", width=150)
        self.sermons_tree.column("preacher", width=150)
        self.sermons_tree.column("date", width=90)
        self.sermons_tree.column("duration", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.sermons_tree.yview)
        self.sermons_tree.configure(yscrollcommand=scrollbar.set)

        self.sermons_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_sermons()

    # ===================== TEAMS TAB =====================
    def setup_teams_tab(self):
        # Service selector
        selector_frame = tk.Frame(self.teams_frame, bg=COLOR_BG)
        selector_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(selector_frame, text="Select Service:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=5)
        self.team_service_var = tk.StringVar()
        self.team_service_combo = ttk.Combobox(selector_frame, textvariable=self.team_service_var, width=30, state="readonly")
        self.team_service_combo.pack(side="left", padx=5)
        self.team_service_combo.bind("<<ComboboxSelected>>", lambda e: self.load_service_teams())

        tk.Button(selector_frame, text="Add Member", width=14, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.add_team_member).pack(side="left", padx=10)
        tk.Button(selector_frame, text="Remove", width=10, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.remove_team_member).pack(side="left", padx=2)

        # Teams tree
        tree_frame = tk.Frame(self.teams_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "role", "member", "status", "notes")
        self.teams_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.teams_tree.heading("id", text="ID")
        self.teams_tree.heading("role", text="Role")
        self.teams_tree.heading("member", text="Member")
        self.teams_tree.heading("status", text="Status")
        self.teams_tree.heading("notes", text="Notes")

        self.teams_tree.column("id", width=40)
        self.teams_tree.column("role", width=150)
        self.teams_tree.column("member", width=200)
        self.teams_tree.column("status", width=100)
        self.teams_tree.column("notes", width=200)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.teams_tree.yview)
        self.teams_tree.configure(yscrollcommand=scrollbar.set)

        self.teams_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_team_service_selector()

    # ===================== DATA LOADING =====================
    def load_filters(self):
        pass  # Service types loaded in form

    def fetch_service_types(self):
        db = DatabaseManager()
        return db.fetch_all("""
            SELECT id, name, COALESCE(description, ''), COALESCE(default_duration_minutes, 90)
            FROM service_types
            ORDER BY name
        """)

    def _format_service_type_option(self, service_type_row):
        return f"{service_type_row[0]} - {service_type_row[1]}"

    def refresh_service_type_combo(self, selected_id=None):
        self.service_type_records = self.fetch_service_types()
        if not self.service_type_combo:
            return

        options = [self._format_service_type_option(row) for row in self.service_type_records]
        self.service_type_combo["values"] = options

        if selected_id:
            for row in self.service_type_records:
                if row[0] == selected_id:
                    self.service_type_combo.set(self._format_service_type_option(row))
                    return

        current_value = self.service_type_combo.get().strip()
        if current_value in options:
            self.service_type_combo.set(current_value)
        elif options:
            self.service_type_combo.set(options[0])
        else:
            self.service_type_combo.set("")

    def _reset_sequence_if_empty(self, db, table_name, sequence_name):
        remaining = db.fetch_one(f"SELECT COUNT(*) FROM {table_name}")
        if remaining and remaining[0] == 0:
            db.execute_query(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")

    def load_services(self):
        db = DatabaseManager()
        try:
            date_from = self.date_from.get_date()
            date_to = self.date_to.get_date()
            status = self.status_var.get()

            query = """
                SELECT s.id, s.service_date, COALESCE(t.name, 'Custom'), s.title, 
                       s.theme, s.start_time, s.status
                FROM service_schedule s
                LEFT JOIN service_types t ON s.service_type_id = t.id
                WHERE s.service_date BETWEEN %s AND %s
            """
            params = [date_from, date_to]

            if status != "All":
                query += " AND s.status = %s"
                params.append(status)

            query += " ORDER BY s.service_date DESC"

            self.all_services = db.fetch_all(query, tuple(params))
            self.refresh_tree()
            self.load_service_selector()
            self.load_team_service_selector()
        except Exception as e:
            print(f"Error loading services: {e}")
            messagebox.showerror("Error", f"Failed to load services: {e}")

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for s in self.all_services:
            self.tree.insert("", "end", values=(
                s[0], s[1].strftime("%Y-%m-%d") if s[1] else "", s[2], s[3] or "", 
                s[4] or "", str(s[5]) if s[5] else "", s[6]
            ))

    def load_service_selector(self):
        db = DatabaseManager()
        try:
            services = db.fetch_all("""
                SELECT id, service_date, title FROM service_schedule 
                ORDER BY service_date DESC LIMIT 50
            """)
            self.order_service_combo["values"] = [f"{s[0]} - {s[1].strftime('%Y-%m-%d')} - {s[2]}" for s in services]
        except Exception as e:
            print(f"Error loading service selector: {e}")

    def load_team_service_selector(self):
        db = DatabaseManager()
        try:
            services = db.fetch_all("""
                SELECT id, service_date, title FROM service_schedule 
                WHERE service_date >= CURRENT_DATE
                ORDER BY service_date ASC LIMIT 20
            """)
            self.team_service_combo["values"] = [f"{s[0]} - {s[1].strftime('%Y-%m-%d')} - {s[2]}" for s in services]
        except Exception as e:
            print(f"Error loading team service selector: {e}")

    def load_order_items(self):
        if not self.order_service_var.get():
            return
        
        service_id = int(self.order_service_var.get().split(" - ")[0])
        db = DatabaseManager()
        
        try:
            items = db.fetch_all("""
                SELECT si.id, si.item_order, si.item_type, si.title, si.duration_minutes,
                       (SELECT full_name FROM members WHERE id = si.assigned_to), si.notes
                FROM service_items si
                WHERE si.service_id = %s
                ORDER BY si.item_order
            """, (service_id,))
            
            self.order_tree.delete(*self.order_tree.get_children())
            for item in items:
                self.order_tree.insert("", "end", values=(
                    item[0], item[1], item[2], item[3], item[4] or "", item[5] or "", item[6] or ""
                ))
        except Exception as e:
            print(f"Error loading order items: {e}")

    def load_songs(self):
        db = DatabaseManager()
        try:
            search = self.song_search.get().strip()
            if search:
                songs = db.fetch_all("""
                    SELECT id, title, artist, key_signature, tempo, category
                    FROM service_songs 
                    WHERE title ILIKE %s OR artist ILIKE %s
                    ORDER BY title
                """, (f"%{search}%", f"%{search}%"))
            else:
                songs = db.fetch_all("SELECT id, title, artist, key_signature, tempo, category FROM service_songs ORDER BY title")
            
            self.songs_tree.delete(*self.songs_tree.get_children())
            for s in songs:
                self.songs_tree.insert("", "end", values=(s[0], s[1], s[2], s[3], s[4], s[5]))
        except Exception as e:
            print(f"Error loading songs: {e}")

    def load_sermons(self):
        db = DatabaseManager()
        try:
            sermons = db.fetch_all("""
                SELECT id, title, scripture_reference, preacher, service_date, duration_minutes
                FROM sermons ORDER BY service_date DESC
            """)
            self.sermons_tree.delete(*self.sermons_tree.get_children())
            for s in sermons:
                self.sermons_tree.insert("", "end", values=(
                    s[0], s[1], s[2], s[3], 
                    s[4].strftime("%Y-%m-%d") if s[4] else "", s[5] or ""
                ))
        except Exception as e:
            print(f"Error loading sermons: {e}")

    def load_service_teams(self):
        if not self.team_service_var.get():
            return
        
        service_id = int(self.team_service_var.get().split(" - ")[0])
        db = DatabaseManager()
        
        try:
            teams = db.fetch_all("""
                SELECT st.id, st.team_role, 
                       (SELECT full_name FROM members WHERE id = st.member_id),
                       st.status, st.notes
                FROM service_teams st
                WHERE st.service_id = %s
            """, (service_id,))
            
            self.teams_tree.delete(*self.teams_tree.get_children())
            for t in teams:
                self.teams_tree.insert("", "end", values=(t[0], t[1], t[2], t[3], t[4] or ""))
        except Exception as e:
            print(f"Error loading teams: {e}")

    # ===================== CRUD OPERATIONS =====================
    def add_service(self):
        self._open_service_form()

    def edit_service(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Service", "Please select a service to edit.")
            return
        
        service_id = self.tree.item(selected[0])["values"][0]
        self._open_service_form(service_id)

    def _open_service_form(self, service_id=None):
        if self.add_win and self.add_win.winfo_exists():
            self.add_win.lift()
            return

        self.add_win = tk.Toplevel(self.root)
        self.add_win.title("Edit Service" if service_id else "Add New Service")
        self.add_win.geometry("550x600")
        self.add_win.configure(bg=COLOR_BG)
        self.add_win.protocol("WM_DELETE_WINDOW", self._close_service_form)

        self.editing_service_id = service_id
        self.entries = {}

        db = DatabaseManager()
        self.service_type_combo = None

        form_frame = tk.Frame(self.add_win, bg=COLOR_BG)
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)

        fields = [
            ("Service Type", "service_type"),
            ("Date", "date"),
            ("Start Time", "start_time"),
            ("End Time", "end_time"),
            ("Title", "title"),
            ("Theme", "theme"),
            ("Status", "status"),
            ("Notes", "notes"),
        ]

        # Load existing data
        existing = {}
        if service_id:
            row = db.fetch_one("""
                SELECT service_type_id, service_date, start_time, end_time, 
                       title, theme, status, notes
                FROM service_schedule WHERE id = %s
            """, (service_id,))
            if row:
                existing = {
                    "service_type": row[0],
                    "date": row[1],
                    "start_time": row[2],
                    "end_time": row[3],
                    "title": row[4],
                    "theme": row[5],
                    "status": row[6],
                    "notes": row[7],
                }

        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label, bg=COLOR_BG, font=FONTS["text"]).grid(
                row=i, column=0, sticky="w", pady=5
            )
            
            if key == "notes":
                entry = tk.Text(form_frame, height=4, font=FONTS["text"])
            elif key == "service_type":
                type_frame = tk.Frame(form_frame, bg=COLOR_BG)
                type_frame.grid(row=i, column=1, sticky="w", pady=5, padx=5)
                entry = ttk.Combobox(type_frame, width=25, state="readonly")
                entry.pack(side="left")
                tk.Button(type_frame, text="Manage", width=8, bg="#0f766e", fg="#fff",
                          font=FONTS["text"], command=self.open_service_type_manager).pack(side="left", padx=(8, 0))
                self.service_type_combo = entry
                self.refresh_service_type_combo()
            elif key == "status":
                entry = ttk.Combobox(form_frame, width=25, state="readonly")
                entry["values"] = ["Scheduled", "In Progress", "Completed", "Cancelled"]
            elif key == "date":
                entry = DateEntry(form_frame, width=22, background='blue', foreground='white', date_pattern='yyyy-mm-dd')
            else:
                entry = tk.Entry(form_frame, width=27, font=FONTS["text"])

            if key != "service_type":
                entry.grid(row=i, column=1, sticky="w", pady=5, padx=5)
            self.entries[key] = entry

            if key in existing:
                val = existing[key]
                if key == "date" and val:
                    entry.set_date(val)
                elif key == "service_type" and val:
                    self.refresh_service_type_combo(selected_id=val)
                elif val:
                    entry.set(val) if hasattr(entry, 'set') else entry.insert(0, str(val))

        btn_frame = tk.Frame(self.add_win, bg=COLOR_BG)
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(btn_frame, text="💾 Save", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=self.save_service).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", width=15, bg="#666", fg="#fff",
                  font=FONTS["text"], command=self._close_service_form).pack(side="left", padx=5)

    def _close_service_form(self):
        self.service_type_combo = None
        if self.add_win and self.add_win.winfo_exists():
            self.add_win.destroy()
        self.add_win = None

    def save_service(self):
        db = DatabaseManager()
        
        service_type = self.entries["service_type"].get()
        service_type_id = int(service_type.split(" - ")[0]) if service_type else None

        data = {
            "date": self.entries["date"].get_date(),
            "start_time": self.entries["start_time"].get().strip(),
            "end_time": self.entries["end_time"].get().strip(),
            "title": self.entries["title"].get().strip(),
            "theme": self.entries["theme"].get().strip(),
            "status": self.entries["status"].get(),
            "notes": self.entries["notes"].get("1.0", "end").strip(),
        }

        if not data["date"] or not data["start_time"]:
            messagebox.showerror("Error", "Date and Start Time are required.")
            return

        try:
            if self.editing_service_id:
                db.execute_query("""
                    UPDATE service_schedule SET service_type_id=%s, service_date=%s, 
                    start_time=%s, end_time=%s, title=%s, theme=%s, status=%s, notes=%s,
                    updated_at=CURRENT_TIMESTAMP WHERE id=%s
                """, (service_type_id, data["date"], data["start_time"], data["end_time"],
                      data["title"], data["theme"], data["status"], data["notes"], self.editing_service_id))
                log_action(
                    table_name="service_schedule",
                    record_id=self.editing_service_id,
                    action="UPDATE",
                    new_values=data,
                    user_id=self.user_id,
                )
            else:
                inserted = db.execute_returning_one("""
                    INSERT INTO service_schedule (service_type_id, service_date, start_time, 
                    end_time, title, theme, status, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (service_type_id, data["date"], data["start_time"], data["end_time"],
                      data["title"], data["theme"], data["status"], data["notes"], self.user_id))
                new_service_id = inserted[0] if inserted else None
                log_action(
                    table_name="service_schedule",
                    record_id=new_service_id,
                    action="INSERT",
                    new_values=data,
                    user_id=self.user_id,
                )

            messagebox.showinfo("Success", "Service saved!")
            self._close_service_form()
            self.load_services()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")

    def delete_service(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Service", "Please select a service to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Delete this service? This will also delete order items and team assignments."):
            return

        service_id = self.tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM service_items WHERE service_id = %s", (service_id,))
            db.execute_query("DELETE FROM service_teams WHERE service_id = %s", (service_id,))
            db.execute_query("DELETE FROM service_schedule WHERE id = %s", (service_id,))
            self._reset_sequence_if_empty(db, "service_schedule", "service_schedule_id_seq")
            self._reset_sequence_if_empty(db, "service_items", "service_items_id_seq")
            self._reset_sequence_if_empty(db, "service_teams", "service_teams_id_seq")
            log_action(
                table_name="service_schedule",
                record_id=service_id,
                action="DELETE",
                old_values={"service_id": service_id},
                user_id=self.user_id,
            )
            self.load_services()
            messagebox.showinfo("Success", "Service deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def open_service_type_manager(self):
        if self.service_type_win and self.service_type_win.winfo_exists():
            self.service_type_win.lift()
            self.load_service_types_into_manager()
            return

        self.service_type_win = tk.Toplevel(self.root)
        self.service_type_win.title("Manage Service Types")
        self.service_type_win.geometry("760x470")
        self.service_type_win.configure(bg=COLOR_BG)
        self.service_type_win.protocol("WM_DELETE_WINDOW", self._close_service_type_manager)

        container = tk.Frame(self.service_type_win, bg=COLOR_BG)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        left = tk.Frame(container, bg=COLOR_BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right = tk.Frame(container, bg=COLOR_BG, width=260)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        columns = ("id", "name", "duration")
        self.service_type_tree = ttk.Treeview(left, columns=columns, show="headings", height=14)
        self.service_type_tree.heading("id", text="ID")
        self.service_type_tree.heading("name", text="Name")
        self.service_type_tree.heading("duration", text="Default Duration")
        self.service_type_tree.column("id", width=50)
        self.service_type_tree.column("name", width=210)
        self.service_type_tree.column("duration", width=120)
        self.service_type_tree.pack(side="left", fill="both", expand=True)
        self.service_type_tree.bind("<<TreeviewSelect>>", lambda e: self.populate_service_type_form())
        self.service_type_tree.bind("<Double-1>", lambda e: self.populate_service_type_form())

        tree_scroll = ttk.Scrollbar(left, orient="vertical", command=self.service_type_tree.yview)
        self.service_type_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y")

        tk.Label(right, text="Service Type Details", bg=COLOR_BG, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 10))

        tk.Label(right, text="Name", bg=COLOR_BG, font=FONTS["text"]).pack(anchor="w")
        self.service_type_name_entry = tk.Entry(right, width=30, font=FONTS["text"])
        self.service_type_name_entry.pack(fill="x", pady=(4, 10))

        tk.Label(right, text="Description", bg=COLOR_BG, font=FONTS["text"]).pack(anchor="w")
        self.service_type_description_text = tk.Text(right, height=5, width=28, font=FONTS["text"])
        self.service_type_description_text.pack(fill="x", pady=(4, 10))

        tk.Label(right, text="Default Duration (min)", bg=COLOR_BG, font=FONTS["text"]).pack(anchor="w")
        self.service_type_duration_entry = tk.Entry(right, width=30, font=FONTS["text"])
        self.service_type_duration_entry.pack(fill="x", pady=(4, 12))

        action_frame = tk.Frame(right, bg=COLOR_BG)
        action_frame.pack(fill="x", pady=(10, 0))

        tk.Button(action_frame, text="New", width=10, bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=self.clear_service_type_form).pack(side="left", padx=(0, 6))
        tk.Button(action_frame, text="Save", width=10, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=self.save_service_type).pack(side="left")

        tk.Button(right, text="Delete Selected", width=22, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.delete_service_type).pack(anchor="w", pady=(10, 0))

        self.load_service_types_into_manager()
        self.clear_service_type_form()

    def _close_service_type_manager(self):
        if self.service_type_win and self.service_type_win.winfo_exists():
            self.service_type_win.destroy()
        self.service_type_win = None

    def load_service_types_into_manager(self):
        if not self.service_type_win or not self.service_type_win.winfo_exists():
            return

        self.service_type_records = self.fetch_service_types()
        self.service_type_tree.delete(*self.service_type_tree.get_children())
        for row in self.service_type_records:
            self.service_type_tree.insert("", "end", values=(row[0], row[1], row[3]))

        self.refresh_service_type_combo()

    def clear_service_type_form(self):
        self.editing_service_type_id = None
        if not self.service_type_win or not self.service_type_win.winfo_exists():
            return

        self.service_type_name_entry.delete(0, "end")
        self.service_type_description_text.delete("1.0", "end")
        self.service_type_duration_entry.delete(0, "end")
        self.service_type_duration_entry.insert(0, "90")
        if hasattr(self, "service_type_tree"):
            for item in self.service_type_tree.selection():
                self.service_type_tree.selection_remove(item)
        self.service_type_name_entry.focus_set()

    def populate_service_type_form(self):
        if not self.service_type_tree.selection():
            return

        item = self.service_type_tree.item(self.service_type_tree.selection()[0])["values"]
        if not item:
            return

        service_type_id = item[0]
        selected_row = next((row for row in self.service_type_records if row[0] == service_type_id), None)
        if not selected_row:
            return

        self.editing_service_type_id = selected_row[0]
        self.service_type_name_entry.delete(0, "end")
        self.service_type_name_entry.insert(0, selected_row[1])
        self.service_type_description_text.delete("1.0", "end")
        self.service_type_description_text.insert("1.0", selected_row[2] or "")
        self.service_type_duration_entry.delete(0, "end")
        self.service_type_duration_entry.insert(0, str(selected_row[3] or 90))

    def save_service_type(self):
        name = self.service_type_name_entry.get().strip()
        description = self.service_type_description_text.get("1.0", "end").strip()
        duration_raw = self.service_type_duration_entry.get().strip()

        if not name:
            messagebox.showerror("Error", "Service type name is required.", parent=self.service_type_win)
            return

        try:
            duration = int(duration_raw) if duration_raw else 90
            if duration <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Default duration must be a positive whole number.", parent=self.service_type_win)
            return

        db = DatabaseManager()
        try:
            if self.editing_service_type_id:
                db.execute_query("""
                    UPDATE service_types
                    SET name=%s, description=%s, default_duration_minutes=%s
                    WHERE id=%s
                """, (name, description, duration, self.editing_service_type_id))
                selected_id = self.editing_service_type_id
            else:
                inserted = db.execute_returning_one("""
                    INSERT INTO service_types (name, description, default_duration_minutes)
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (name, description, duration))
                selected_id = inserted[0] if inserted else None

            self.load_service_types_into_manager()
            self.refresh_service_type_combo(selected_id=selected_id)
            self.clear_service_type_form()
            messagebox.showinfo("Success", "Service type saved successfully.", parent=self.service_type_win)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save service type: {e}", parent=self.service_type_win)

    def delete_service_type(self):
        if not self.service_type_tree.selection():
            messagebox.showwarning("Select Service Type", "Please select a service type to delete.", parent=self.service_type_win)
            return

        item = self.service_type_tree.item(self.service_type_tree.selection()[0])["values"]
        service_type_id = item[0]
        service_type_name = item[1]

        if not messagebox.askyesno("Confirm Delete", f"Delete service type '{service_type_name}'?", parent=self.service_type_win):
            return

        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM service_types WHERE id = %s", (service_type_id,))
            self._reset_sequence_if_empty(db, "service_types", "service_types_id_seq")
            self.load_service_types_into_manager()
            self.clear_service_type_form()
            messagebox.showinfo("Success", "Service type deleted.", parent=self.service_type_win)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Failed to delete service type.\nIt may already be used by existing services.\n\nDetails: {e}",
                parent=self.service_type_win
            )

    def manage_order(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Service", "Please select a service to manage order.")
            return
        
        service_id = self.tree.item(selected[0])["values"][0]
        service_date = self.tree.item(selected[0])["values"][1]
        service_title = self.tree.item(selected[0])["values"][3]
        
        self.order_service_var.set(f"{service_id} - {service_date} - {service_title}")
        self.notebook.select(self.order_frame)
        self.load_order_items()

    # ===================== ORDER ITEMS =====================
    def add_order_item(self):
        if not self.order_service_var.get():
            messagebox.showwarning("Select Service", "Please select a service first.")
            return

        service_id = int(self.order_service_var.get().split(" - ")[0])
        
        win = tk.Toplevel(self.root)
        win.title("Add Order Item")
        win.geometry("500x450")
        win.configure(bg=COLOR_BG)

        db = DatabaseManager()
        members = db.fetch_all("SELECT id, full_name FROM members ORDER BY full_name")

        tk.Label(win, text="Item Type:", bg=COLOR_BG, font=FONTS["text"]).grid(row=0, column=0, sticky="w", pady=5, padx=10)
        type_var = ttk.Combobox(win, width=30, state="readonly")
        type_var["values"] = ["Opening Prayer", "Worship Song", "Hymn", "Scripture Reading", 
                              "Sermon", "Offering", "Communion", "Announcements", 
                              "Special Item", "Closing Prayer", "Benediction"]
        type_var.grid(row=0, column=1, pady=5, padx=10)

        tk.Label(win, text="Title:", bg=COLOR_BG, font=FONTS["text"]).grid(row=1, column=0, sticky="w", pady=5, padx=10)
        title_entry = tk.Entry(win, width=32)
        title_entry.grid(row=1, column=1, pady=5, padx=10)

        tk.Label(win, text="Duration (min):", bg=COLOR_BG, font=FONTS["text"]).grid(row=2, column=0, sticky="w", pady=5, padx=10)
        duration_entry = tk.Entry(win, width=32)
        duration_entry.grid(row=2, column=1, pady=5, padx=10)

        tk.Label(win, text="Assigned To:", bg=COLOR_BG, font=FONTS["text"]).grid(row=3, column=0, sticky="w", pady=5, padx=10)
        member_var = ttk.Combobox(win, width=30, state="readonly")
        member_var["values"] = [""] + [f"{m[0]} - {m[1]}" for m in members]
        member_var.grid(row=3, column=1, pady=5, padx=10)

        tk.Label(win, text="Notes:", bg=COLOR_BG, font=FONTS["text"]).grid(row=4, column=0, sticky="nw", pady=5, padx=10)
        notes_text = tk.Text(win, height=4, width=30)
        notes_text.grid(row=4, column=1, pady=5, padx=10)

        def save():
            if not type_var.get() or not title_entry.get():
                messagebox.showerror("Error", "Type and Title are required.")
                return

            member_id = None
            if member_var.get():
                member_id = int(member_var.get().split(" - ")[0])

            # Get next order
            row = db.fetch_one("SELECT COALESCE(MAX(item_order), 0) + 1 FROM service_items WHERE service_id = %s", (service_id,))
            order = row[0] if row else 1

            try:
                db.execute_query("""
                    INSERT INTO service_items (service_id, item_order, item_type, title, 
                    duration_minutes, assigned_to, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (service_id, order, type_var.get(), title_entry.get(), 
                      duration_entry.get() or None, member_id, notes_text.get("1.0", "end").strip()))
                messagebox.showinfo("Success", "Item added!")
                win.destroy()
                self.load_order_items()
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {e}")

        tk.Button(win, text="💾 Save", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=save).grid(row=5, column=0, columnspan=2, pady=20)

    def move_item(self, direction):
        selected = self.order_tree.selection()
        if not selected:
            messagebox.showwarning("Select Item", "Select an item to move.")
            return

        item_id = self.order_tree.item(selected[0])["values"][0]
        current_order = self.order_tree.item(selected[0])["values"][1]

        db = DatabaseManager()
        service_id = int(self.order_service_var.get().split(" - ")[0])

        # Get adjacent item
        if direction == -1:  # Move up
            neighbor = db.fetch_one("""
                SELECT id FROM service_items 
                WHERE service_id = %s AND item_order < %s 
                ORDER BY item_order DESC LIMIT 1
            """, (service_id, current_order))
        else:  # Move down
            neighbor = db.fetch_one("""
                SELECT id FROM service_items 
                WHERE service_id = %s AND item_order > %s 
                ORDER BY item_order ASC LIMIT 1
            """, (service_id, current_order))

        if not neighbor:
            return

        neighbor_id = neighbor[0]
        
        try:
            # Swap orders
            db.execute_query("UPDATE service_items SET item_order = %s WHERE id = %s", (current_order, neighbor_id))
            db.execute_query("UPDATE service_items SET item_order = %s WHERE id = %s", (current_order + direction, item_id))
            self.load_order_items()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move: {e}")

    def delete_order_item(self):
        selected = self.order_tree.selection()
        if not selected:
            messagebox.showwarning("Select Item", "Select an item to delete.")
            return
        
        item_id = self.order_tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM service_items WHERE id = %s", (item_id,))
            self._reset_sequence_if_empty(db, "service_items", "service_items_id_seq")
            self.load_order_items()
            messagebox.showinfo("Success", "Item deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    # ===================== SONGS =====================
    def add_song(self):
        self._open_song_form()

    def edit_song(self):
        selected = self.songs_tree.selection()
        if not selected:
            messagebox.showwarning("Select Song", "Select a song to edit.")
            return
        song_id = self.songs_tree.item(selected[0])["values"][0]
        self._open_song_form(song_id)

    def _open_song_form(self, song_id=None):
        win = tk.Toplevel(self.root)
        win.title("Edit Song" if song_id else "Add Song")
        win.geometry("500x500")
        win.configure(bg=COLOR_BG)

        db = DatabaseManager()
        existing = {}
        if song_id:
            row = db.fetch_one("SELECT title, artist, lyrics, key_signature, tempo, category FROM service_songs WHERE id = %s", (song_id,))
            if row:
                existing = {"title": row[0], "artist": row[1], "lyrics": row[2], 
                           "key": row[3], "tempo": row[4], "category": row[5]}

        fields = [("Title", "title"), ("Artist", "artist"), ("Key", "key"), 
                  ("Tempo", "tempo"), ("Category", "category")]
        
        entries = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(win, text=label, bg=COLOR_BG, font=FONTS["text"]).grid(row=i, column=0, sticky="w", pady=5, padx=10)
            if key == "category":
                entry = ttk.Combobox(win, width=30, state="readonly")
                entry["values"] = ["Hymns", "Worship", "Praise", "Communion", "Special", "Youth"]
            else:
                entry = tk.Entry(win, width=32)
            entry.grid(row=i, column=1, pady=5, padx=10)
            entries[key] = entry
            if key in existing and existing[key]:
                entry.set(existing[key])

        tk.Label(win, text="Lyrics:", bg=COLOR_BG, font=FONTS["text"]).grid(row=5, column=0, sticky="nw", pady=5, padx=10)
        lyrics_text = tk.Text(win, height=10, width=32)
        lyrics_text.grid(row=5, column=1, pady=5, padx=10)
        if "lyrics" in existing and existing["lyrics"]:
            lyrics_text.insert("1.0", existing["lyrics"])

        def save():
            try:
                if song_id:
                    db.execute_query("""
                        UPDATE service_songs SET title=%s, artist=%s, lyrics=%s, 
                        key_signature=%s, tempo=%s, category=%s WHERE id=%s
                    """, (entries["title"].get(), entries["artist"].get(), lyrics_text.get("1.0", "end").strip(),
                          entries["key"].get(), entries["tempo"].get(), entries["category"].get(), song_id))
                else:
                    db.execute_query("""
                        INSERT INTO service_songs (title, artist, lyrics, key_signature, tempo, category)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (entries["title"].get(), entries["artist"].get(), lyrics_text.get("1.0", "end").strip(),
                          entries["key"].get(), entries["tempo"].get(), entries["category"].get()))
                messagebox.showinfo("Success", "Song saved!")
                win.destroy()
                self.load_songs()
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {e}")

        tk.Button(win, text="💾 Save", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=save).grid(row=6, column=0, columnspan=2, pady=20)

    def delete_song(self):
        selected = self.songs_tree.selection()
        if not selected:
            return
        if not messagebox.askyesno("Confirm", "Delete this song?"):
            return
        
        song_id = self.songs_tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM service_songs WHERE id = %s", (song_id,))
            self._reset_sequence_if_empty(db, "service_songs", "service_songs_id_seq")
            self.load_songs()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    # ===================== SERMONS =====================
    def add_sermon(self):
        self._open_sermon_form()

    def edit_sermon(self):
        selected = self.sermons_tree.selection()
        if not selected:
            messagebox.showwarning("Select Sermon", "Select a sermon to edit.")
            return
        sermon_id = self.sermons_tree.item(selected[0])["values"][0]
        self._open_sermon_form(sermon_id)

    def _open_sermon_form(self, sermon_id=None):
        win = tk.Toplevel(self.root)
        win.title("Edit Sermon" if sermon_id else "Add Sermon")
        win.geometry("550x500")
        win.configure(bg=COLOR_BG)

        db = DatabaseManager()
        existing = {}
        if sermon_id:
            row = db.fetch_one("""
                SELECT title, scripture_reference, preacher, summary, duration_minutes, service_date
                FROM sermons WHERE id = %s
            """, (sermon_id,))
            if row:
                existing = {"title": row[0], "scripture": row[1], "preacher": row[2],
                           "summary": row[3], "duration": row[4], "date": row[5]}

        entries = {}
        fields = [("Title", "title"), ("Scripture", "scripture"), ("Preacher", "preacher"), ("Duration (min)", "duration")]
        
        for i, (label, key) in enumerate(fields):
            tk.Label(win, text=label, bg=COLOR_BG, font=FONTS["text"]).grid(row=i, column=0, sticky="w", pady=5, padx=10)
            entry = tk.Entry(win, width=32)
            entry.grid(row=i, column=1, pady=5, padx=10)
            entries[key] = entry
            if key in existing and existing[key]:
                entry.insert(0, str(existing[key]))

        tk.Label(win, text="Date:", bg=COLOR_BG, font=FONTS["text"]).grid(row=4, column=0, sticky="w", pady=5, padx=10)
        date_entry = DateEntry(win, width=30, background='blue', foreground='white', date_pattern='yyyy-mm-dd')
        date_entry.set_date(existing.get("date", datetime.now()))
        date_entry.grid(row=4, column=1, pady=5, padx=10)

        tk.Label(win, text="Summary:", bg=COLOR_BG, font=FONTS["text"]).grid(row=5, column=0, sticky="nw", pady=5, padx=10)
        summary_text = tk.Text(win, height=6, width=32)
        summary_text.grid(row=5, column=1, pady=5, padx=10)
        if "summary" in existing and existing["summary"]:
            summary_text.insert("1.0", existing["summary"])

        def save():
            try:
                if sermon_id:
                    db.execute_query("""
                        UPDATE sermons SET title=%s, scripture_reference=%s, preacher=%s, 
                        summary=%s, duration_minutes=%s, service_date=%s WHERE id=%s
                    """, (entries["title"].get(), entries["scripture"].get(), entries["preacher"].get(),
                          summary_text.get("1.0", "end").strip(), entries["duration"].get() or None,
                          date_entry.get_date(), sermon_id))
                else:
                    db.execute_query("""
                        INSERT INTO sermons (title, scripture_reference, preacher, summary, duration_minutes, service_date)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (entries["title"].get(), entries["scripture"].get(), entries["preacher"].get(),
                          summary_text.get("1.0", "end").strip(), entries["duration"].get() or None,
                          date_entry.get_date()))
                messagebox.showinfo("Success", "Sermon saved!")
                win.destroy()
                self.load_sermons()
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {e}")

        tk.Button(win, text="💾 Save", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=save).grid(row=6, column=0, columnspan=2, pady=20)

    def delete_sermon(self):
        selected = self.sermons_tree.selection()
        if not selected:
            return
        if not messagebox.askyesno("Confirm", "Delete this sermon?"):
            return
        
        sermon_id = self.sermons_tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM sermons WHERE id = %s", (sermon_id,))
            self._reset_sequence_if_empty(db, "sermons", "sermons_id_seq")
            self.load_sermons()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    # ===================== TEAMS =====================
    def add_team_member(self):
        if not self.team_service_var.get():
            messagebox.showwarning("Select Service", "Please select a service first.")
            return

        service_id = int(self.team_service_var.get().split(" - ")[0])
        
        win = tk.Toplevel(self.root)
        win.title("Add Team Member")
        win.geometry("450x350")
        win.configure(bg=COLOR_BG)

        db = DatabaseManager()
        members = db.fetch_all("SELECT id, full_name FROM members ORDER BY full_name")

        tk.Label(win, text="Role:", bg=COLOR_BG, font=FONTS["text"]).grid(row=0, column=0, sticky="w", pady=5, padx=10)
        role_var = ttk.Combobox(win, width=30, state="readonly")
        role_var["values"] = ["Worship Leader", "Worship Team", "Usher", "Greeter", "Sound Technician", 
                              "Media Operator", "Camera Operator", "Security", "Prayer Team", "Other"]
        role_var.grid(row=0, column=1, pady=5, padx=10)

        tk.Label(win, text="Member:", bg=COLOR_BG, font=FONTS["text"]).grid(row=1, column=0, sticky="w", pady=5, padx=10)
        member_var = ttk.Combobox(win, width=30, state="readonly")
        member_var["values"] = [f"{m[0]} - {m[1]}" for m in members]
        member_var.grid(row=1, column=1, pady=5, padx=10)

        tk.Label(win, text="Status:", bg=COLOR_BG, font=FONTS["text"]).grid(row=2, column=0, sticky="w", pady=5, padx=10)
        status_var = ttk.Combobox(win, width=30, state="readonly")
        status_var["values"] = ["Confirmed", "Pending", "Declined"]
        status_var.set("Pending")
        status_var.grid(row=2, column=1, pady=5, padx=10)

        tk.Label(win, text="Notes:", bg=COLOR_BG, font=FONTS["text"]).grid(row=3, column=0, sticky="nw", pady=5, padx=10)
        notes_text = tk.Text(win, height=4, width=30)
        notes_text.grid(row=3, column=1, pady=5, padx=10)

        def save():
            if not role_var.get() or not member_var.get():
                messagebox.showerror("Error", "Role and Member are required.")
                return

            member_id = int(member_var.get().split(" - ")[0])

            try:
                db.execute_query("""
                    INSERT INTO service_teams (service_id, team_role, member_id, status, notes)
                    VALUES (%s, %s, %s, %s, %s)
                """, (service_id, role_var.get(), member_id, status_var.get(), notes_text.get("1.0", "end").strip()))
                messagebox.showinfo("Success", "Team member added!")
                win.destroy()
                self.load_service_teams()
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {e}")

        tk.Button(win, text="💾 Save", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=save).grid(row=4, column=0, columnspan=2, pady=20)

    def remove_team_member(self):
        selected = self.teams_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Select a team member to remove.")
            return
        
        team_id = self.teams_tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM service_teams WHERE id = %s", (team_id,))
            self._reset_sequence_if_empty(db, "service_teams", "service_teams_id_seq")
            self.load_service_teams()
            messagebox.showinfo("Success", "Team member removed.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
