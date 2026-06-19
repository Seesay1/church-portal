# modules/assets.py
from modules.audit_helper import log_action
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from tkcalendar import DateEntry
import os
import shutil
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from database import DatabaseManager, hash_password
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
class AssetsModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.user_id = user_id
        self.branch_id = branch_id

        self.root.configure(bg=COLOR_BG)

        self.editing_asset_id = None
        self.add_win = None
        self.photo_path = ""
        self.photo_label = None
        self.entries = {}
        self.all_assets = []

        self._setup_styles()
        self._build_main_layout()
        self.load_filters()
        self.load_assets()

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

    def _reset_sequence_if_empty(self, db, table_name, sequence_name):
        remaining = db.fetch_one(f"SELECT COUNT(*) FROM {table_name}")
        if remaining and remaining[0] == 0:
            db.execute_query(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")

    # ===================== MAIN LAYOUT =====================
    def _build_main_layout(self):
        # Create Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Assets List
        self.list_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.list_frame, text="📦 Assets List")

        # Tab 2: Maintenance
        self.maint_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.maint_frame, text="🔧 Maintenance")

        # Tab 3: Assignments
        self.assign_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.assign_frame, text="📤 Assignments")

        # Tab 4: Reports
        self.reports_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.notebook.add(self.reports_frame, text="📊 Reports")

        self.setup_list_tab()
        self.setup_maintenance_tab()
        self.setup_assignments_tab()
        self.setup_reports_tab()

    # ===================== ASSETS LIST TAB =====================
    def setup_list_tab(self):
        # ---------- Top Toolbar ----------
        toolbar = tk.Frame(self.list_frame, bg=COLOR_BG)
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        btn_frame = tk.Frame(toolbar, bg=COLOR_BG)
        btn_frame.pack(side="left", fill="x", expand=True)

        tk.Button(btn_frame, text="Add", width=12, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.add_asset).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Edit", width=10, bg=COLOR_BLUE, fg="#fff",
                  font=FONTS["text"], command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete", width=10, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.delete_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Add Photo", width=12, bg=COLOR_PURPLE, fg="#fff",
                  font=FONTS["text"], command=self.add_photo).pack(side="left", padx=5)

        # ---------- Filter Bar ----------
        filter_frame = tk.Frame(self.list_frame, bg=COLOR_BG)
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Search
        tk.Label(filter_frame, text="🔍 Search:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda a,b,c: self.filter_assets())
        tk.Entry(filter_frame, textvariable=self.search_var, font=FONTS["text"], width=20).pack(side="left", padx=5)

        # Category Filter
        tk.Label(filter_frame, text="Category:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, width=15, state="readonly")
        self.category_combo.pack(side="left", padx=5)
        self.category_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_assets())

        # Status Filter
        tk.Label(filter_frame, text="Status:", bg=COLOR_BG, font=FONTS["text"]).pack(side="left", padx=5)
        self.status_var = tk.StringVar()
        status_combo = ttk.Combobox(filter_frame, textvariable=self.status_var, width=12, 
                                     values=["All", "Available", "In Use", "Under Maintenance", "Retired"],
                                     state="readonly")
        status_combo.pack(side="left", padx=5)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_assets())
        status_combo.set("All")

        # ---------- Assets Treeview ----------
        tree_frame = tk.Frame(self.list_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "asset_id", "name", "category", "location", "condition", "status", "value")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.tree.heading("id", text="ID")
        self.tree.heading("asset_id", text="Asset ID")
        self.tree.heading("name", text="Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("location", text="Location")
        self.tree.heading("condition", text="Condition")
        self.tree.heading("status", text="Status")
        self.tree.heading("value", text="Value")

        self.tree.column("id", width=40)
        self.tree.column("asset_id", width=80)
        self.tree.column("name", width=180)
        self.tree.column("category", width=100)
        self.tree.column("location", width=120)
        self.tree.column("condition", width=80)
        self.tree.column("status", width=100)
        self.tree.column("value", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    # ===================== MAINTENANCE TAB =====================
    def setup_maintenance_tab(self):
        # ---------- Toolbar ----------
        toolbar = tk.Frame(self.maint_frame, bg=COLOR_BG)
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        tk.Button(toolbar, text="Add Record", width=15, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.add_maintenance).pack(side="left", padx=5)
        tk.Button(toolbar, text="Delete", width=12, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.delete_maintenance).pack(side="left", padx=5)

        # ---------- Maintenance Treeview ----------
        tree_frame = tk.Frame(self.maint_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "asset_name", "type", "description", "cost", "date", "next_date")
        self.maint_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.maint_tree.heading("id", text="ID")
        self.maint_tree.heading("asset_name", text="Asset")
        self.maint_tree.heading("type", text="Type")
        self.maint_tree.heading("description", text="Description")
        self.maint_tree.heading("cost", text="Cost")
        self.maint_tree.heading("date", text="Date")
        self.maint_tree.heading("next_date", text="Next Due")

        self.maint_tree.column("id", width=40)
        self.maint_tree.column("asset_name", width=150)
        self.maint_tree.column("type", width=100)
        self.maint_tree.column("description", width=250)
        self.maint_tree.column("cost", width=80)
        self.maint_tree.column("date", width=100)
        self.maint_tree.column("next_date", width=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.maint_tree.yview)
        self.maint_tree.configure(yscrollcommand=scrollbar.set)

        self.maint_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_maintenance()

    # ===================== ASSIGNMENTS TAB =====================
    def setup_assignments_tab(self):
        # ---------- Toolbar ----------
        toolbar = tk.Frame(self.assign_frame, bg=COLOR_BG)
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        tk.Button(toolbar, text="Assign", width=12, bg=COLOR_RED, fg="#fff",
                  font=FONTS["text"], command=self.assign_asset).pack(side="left", padx=5)
        tk.Button(toolbar, text="Return", width=12, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=self.return_asset).pack(side="left", padx=5)
        tk.Button(toolbar, text="Delete", width=10, bg="#333", fg="#fff",
                  font=FONTS["text"], command=self.delete_assignment).pack(side="left", padx=5)

        # ---------- Assignments Treeview ----------
        tree_frame = tk.Frame(self.assign_frame, bg=COLOR_BG)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("id", "asset_name", "assigned_to", "assigned_by", "assigned_date", "return_date", "status")
        self.assign_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        self.assign_tree.heading("id", text="ID")
        self.assign_tree.heading("asset_name", text="Asset")
        self.assign_tree.heading("assigned_to", text="Assigned To")
        self.assign_tree.heading("assigned_by", text="Assigned By")
        self.assign_tree.heading("assigned_date", text="Assigned Date")
        self.assign_tree.heading("return_date", text="Return Date")
        self.assign_tree.heading("status", text="Status")

        self.assign_tree.column("id", width=40)
        self.assign_tree.column("asset_name", width=150)
        self.assign_tree.column("assigned_to", width=150)
        self.assign_tree.column("assigned_by", width=100)
        self.assign_tree.column("assigned_date", width=100)
        self.assign_tree.column("return_date", width=100)
        self.assign_tree.column("status", width=80)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.assign_tree.yview)
        self.assign_tree.configure(yscrollcommand=scrollbar.set)

        self.assign_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_assignments()

    # ===================== REPORTS TAB =====================
    def setup_reports_tab(self):
        # Summary Cards
        cards_frame = tk.Frame(self.reports_frame, bg=COLOR_BG)
        cards_frame.pack(fill="x", padx=10, pady=10)

        self.total_assets_card = self._create_card(cards_frame, "Total Assets", "0", COLOR_BLUE)
        self.available_card = self._create_card(cards_frame, "Available", "0", COLOR_GREEN)
        self.in_use_card = self._create_card(cards_frame, "In Use", "0", COLOR_PURPLE)
        self.maintenance_card = self._create_card(cards_frame, "Maintenance", "0", COLOR_RED)

        # Charts
        chart_frame = tk.Frame(self.reports_frame, bg=COLOR_BG)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Category distribution
        self.fig = Figure(figsize=(8, 4), facecolor=COLOR_BG)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, chart_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.load_reports()

    def _create_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=COLOR_WHITE, bd=1, relief="solid")
        card.pack(side="left", padx=10, pady=5, fill="both", expand=True)
        
        tk.Label(card, text=title, bg=COLOR_WHITE, fg=COLOR_MUTED, font=("Segoe UI", 10)).pack(pady=(10, 5))
        tk.Label(card, text=value, bg=COLOR_WHITE, fg=color, font=("Segoe UI", 24, "bold")).pack(pady=(0, 10))
        
        return card

    # ===================== DATA LOADING =====================
    def load_filters(self):
        db = DatabaseManager()
        try:
            categories = db.fetch_all("SELECT id, name FROM asset_categories ORDER BY name")
            cat_list = ["All"] + [c[1] for c in categories]
            self.category_combo["values"] = cat_list
            self.category_combo.set("All")
            self.categories = {c[1]: c[0] for c in categories}
        except Exception as e:
            print(f"Error loading categories: {e}")
            self.categories = {}

    def load_assets(self):
        db = DatabaseManager()
        try:
            self.all_assets = db.fetch_all("""
                SELECT a.id, a.asset_id, a.name, COALESCE(c.name, 'Uncategorized'), 
                       a.location, a.condition, a.status, COALESCE(a.current_value, 0)
                FROM assets a
                LEFT JOIN asset_categories c ON a.category_id = c.id
                ORDER BY a.id DESC
            """)
            self.filter_assets()
        except Exception as e:
            print(f"Error loading assets: {e}")
            messagebox.showerror("Error", f"Failed to load assets: {e}")

    def filter_assets(self):
        search = self.search_var.get().lower()
        category = self.category_var.get()
        status = self.status_var.get()

        filtered = []
        for asset in self.all_assets:
            if search and search not in str(asset[2]).lower():
                continue
            if category != "All" and asset[3] != category:
                continue
            if status != "All" and asset[6] != status:
                continue
            filtered.append(asset)

        self.tree.delete(*self.tree.get_children())
        for a in filtered:
            self.tree.insert("", "end", values=(
                a[0], a[1], a[2], a[3], a[4], a[5], a[6], f"${a[7]:,.2f}"
            ))

    def load_maintenance(self):
        db = DatabaseManager()
        try:
            records = db.fetch_all("""
                SELECT m.id, a.name, m.maintenance_type, m.description, 
                       COALESCE(m.cost, 0), m.maintenance_date, m.next_maintenance_date
                FROM asset_maintenance m
                JOIN assets a ON m.asset_id = a.id
                ORDER BY m.maintenance_date DESC
            """)
            self.maint_tree.delete(*self.maint_tree.get_children())
            for r in records:
                self.maint_tree.insert("", "end", values=(
                    r[0], r[1], r[2], r[3][:50] if r[3] else "", 
                    f"${r[4]:,.2f}" if r[4] else "-",
                    r[5].strftime("%Y-%m-%d") if r[5] else "-",
                    r[6].strftime("%Y-%m-%d") if r[6] else "-"
                ))
        except Exception as e:
            print(f"Error loading maintenance: {e}")

    def load_assignments(self):
        db = DatabaseManager()
        try:
            records = db.fetch_all("""
                SELECT aa.id, a.name, 
                       (SELECT full_name FROM members WHERE id = aa.assigned_to),
                       (SELECT username FROM users WHERE id = aa.assigned_by),
                       aa.assigned_date, aa.expected_return_date, aa.status
                FROM asset_assignments aa
                JOIN assets a ON aa.asset_id = a.id
                ORDER BY aa.assigned_date DESC
            """)
            self.assign_tree.delete(*self.assign_tree.get_children())
            for r in records:
                self.assign_tree.insert("", "end", values=(
                    r[0], r[1], r[2] or "Unknown", r[3] or "Unknown",
                    r[4].strftime("%Y-%m-%d") if r[4] else "-",
                    r[5].strftime("%Y-%m-%d") if r[5] else "-",
                    r[6]
                ))
        except Exception as e:
            print(f"Error loading assignments: {e}")

    def load_reports(self):
        db = DatabaseManager()
        try:
            # Get counts
            total = db.fetch_one("SELECT COUNT(*) FROM assets")
            available = db.fetch_one("SELECT COUNT(*) FROM assets WHERE status = 'Available'")
            in_use = db.fetch_one("SELECT COUNT(*) FROM assets WHERE status = 'In Use'")
            maintenance = db.fetch_one("SELECT COUNT(*) FROM assets WHERE status = 'Under Maintenance'")

            # Update cards
            for card, val in [(self.total_assets_card, total[0] if total else 0),
                              (self.available_card, available[0] if available else 0),
                              (self.in_use_card, in_use[0] if in_use else 0),
                              (self.maintenance_card, maintenance[0] if maintenance else 0)]:
                card.winfo_children()[1].config(text=str(val))

            # Category chart
            categories = db.fetch_all("""
                SELECT c.name, COUNT(a.id) 
                FROM asset_categories c
                LEFT JOIN assets a ON a.category_id = c.id
                GROUP BY c.name
            """)
            
            self.ax.clear()
            if categories:
                labels = [c[0] for c in categories if c[1] > 0]
                values = [c[1] for c in categories if c[1] > 0]
                if values:
                    self.ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
                    self.ax.set_title("Assets by Category", color=COLOR_TEXT)
            self.canvas.draw()

        except Exception as e:
            print(f"Error loading reports: {e}")

    # ===================== CRUD OPERATIONS =====================
    def add_asset(self):
        self._open_asset_form()

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Asset", "Please select an asset to edit.")
            return
        
        item = self.tree.item(selected[0])
        asset_id = item["values"][0]
        self._open_asset_form(asset_id)

    def _open_asset_form(self, asset_id=None):
        if self.add_win and self.add_win.winfo_exists():
            self.add_win.lift()
            return

        self.add_win = tk.Toplevel(self.root)
        self.add_win.title("Edit Asset" if asset_id else "Add New Asset")
        self.add_win.geometry("600x700")
        self.add_win.configure(bg=COLOR_BG)

        self.editing_asset_id = asset_id
        self.entries = {}

        # Form fields
        form_frame = tk.Frame(self.add_win, bg=COLOR_BG)
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)

        fields = [
            ("Asset ID", "asset_id"),
            ("Name", "name"),
            ("Description", "description"),
            ("Category", "category"),
            ("Location", "location"),
            ("Purchase Date", "purchase_date"),
            ("Purchase Price", "purchase_price"),
            ("Current Value", "current_value"),
            ("Condition", "condition"),
            ("Status", "status"),
            ("Notes", "notes"),
        ]

        # Load existing data if editing
        existing_data = {}
        if asset_id:
            db = DatabaseManager()
            row = db.fetch_one("""
                SELECT asset_id, name, description, category_id, location, 
                       purchase_date, purchase_price, current_value, condition, status, notes
                FROM assets WHERE id = %s
            """, (asset_id,))
            if row:
                existing_data = {
                    "asset_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "category": row[3],
                    "location": row[4],
                    "purchase_date": row[5],
                    "purchase_price": row[6],
                    "current_value": row[7],
                    "condition": row[8],
                    "status": row[9],
                    "notes": row[10],
                }

        # Create fields
        for i, (label, key) in enumerate(fields):
            tk.Label(form_frame, text=label, bg=COLOR_BG, font=FONTS["text"]).grid(
                row=i, column=0, sticky="w", pady=5
            )
            
            if key == "description" or key == "notes":
                entry = tk.Text(form_frame, height=3, font=FONTS["text"])
            elif key == "category":
                entry = ttk.Combobox(form_frame, width=25, state="readonly")
                entry["values"] = list(self.categories.keys())
            elif key == "condition":
                entry = ttk.Combobox(form_frame, width=25, state="readonly")
                entry["values"] = ["Excellent", "Good", "Fair", "Poor"]
            elif key == "status":
                entry = ttk.Combobox(form_frame, width=25, state="readonly")
                entry["values"] = ["Available", "In Use", "Under Maintenance", "Retired"]
            elif key == "purchase_date":
                entry = DateEntry(form_frame, width=22, background='blue', foreground='white',
                                  borderwidth=2, date_pattern='yyyy-mm-dd')
            else:
                entry = tk.Entry(form_frame, width=27, font=FONTS["text"])

            entry.grid(row=i, column=1, sticky="w", pady=5, padx=5)
            self.entries[key] = entry

            # Set existing value
            if key in existing_data:
                val = existing_data[key]
                if key in ("description", "notes"):
                    entry.insert("1.0", str(val) if val else "")
                elif key == "purchase_date" and val:
                    entry.set_date(val)
                elif val:
                    entry.set(val) if hasattr(entry, 'set') else entry.insert(0, str(val))

        # Buttons
        btn_frame = tk.Frame(self.add_win, bg=COLOR_BG)
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(btn_frame, text="💾 Save", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=self.save_asset).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", width=15, bg="#666", fg="#fff",
                  font=FONTS["text"], command=self.add_win.destroy).pack(side="left", padx=5)

    def save_asset(self):
        db = DatabaseManager()
        
        data = {
            "asset_id": self.entries["asset_id"].get().strip(),
            "name": self.entries["name"].get().strip(),
            "description": self.entries["description"].get("1.0", "end").strip(),
            "location": self.entries["location"].get().strip(),
            "purchase_price": self.entries["purchase_price"].get().strip(),
            "current_value": self.entries["current_value"].get().strip(),
            "condition": self.entries["condition"].get(),
            "status": self.entries["status"].get(),
            "notes": self.entries["notes"].get("1.0", "end").strip(),
        }

        # Get category ID
        cat_name = self.entries["category"].get()
        data["category_id"] = self.categories.get(cat_name)

        # Get date
        try:
            data["purchase_date"] = self.entries["purchase_date"].get_date()
        except:
            data["purchase_date"] = None

        # Convert prices
        try:
            data["purchase_price"] = float(data["purchase_price"]) if data["purchase_price"] else None
        except:
            data["purchase_price"] = None
        try:
            data["current_value"] = float(data["current_value"]) if data["current_value"] else None
        except:
            data["current_value"] = None

        if not data["asset_id"] or not data["name"]:
            messagebox.showerror("Error", "Asset ID and Name are required.")
            return

        try:
            if self.editing_asset_id:
                db.execute_query("""
                    UPDATE assets SET asset_id=%s, name=%s, description=%s, category_id=%s,
                    location=%s, purchase_date=%s, purchase_price=%s, current_value=%s,
                    condition=%s, status=%s, notes=%s, updated_at=CURRENT_TIMESTAMP
                    WHERE id=%s
                """, (data["asset_id"], data["name"], data["description"], data["category_id"],
                      data["location"], data["purchase_date"], data["purchase_price"],
                      data["current_value"], data["condition"], data["status"],
                      data["notes"], self.editing_asset_id))
                log_action(
                    table_name="assets",
                    record_id=self.editing_asset_id,
                    action="UPDATE",
                    new_values=data,
                    user_id=self.user_id,
                )
            else:
                inserted = db.execute_returning_one("""
                    INSERT INTO assets (asset_id, name, description, category_id, location,
                    purchase_date, purchase_price, current_value, condition, status, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (data["asset_id"], data["name"], data["description"], data["category_id"],
                      data["location"], data["purchase_date"], data["purchase_price"],
                      data["current_value"], data["condition"], data["status"],
                      data["notes"], self.user_id))
                new_asset_id = inserted[0] if inserted else None
                log_action(
                    table_name="assets",
                    record_id=new_asset_id,
                    action="INSERT",
                    new_values=data,
                    user_id=self.user_id,
                )

            messagebox.showinfo("Success", "Asset saved successfully!")
            self.add_win.destroy()
            self.load_assets()
            self.load_reports()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save asset: {e}")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Asset", "Please select an asset to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this asset?"):
            return

        asset_id = self.tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM assets WHERE id = %s", (asset_id,))
            self._reset_sequence_if_empty(db, "assets", "assets_id_seq")
            log_action(
                table_name="assets",
                record_id=asset_id,
                action="DELETE",
                old_values={"asset_id": asset_id},
                user_id=self.user_id,
            )
            self.load_assets()
            self.load_reports()
            messagebox.showinfo("Success", "Asset deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete: {e}")

    def add_photo(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Asset", "Please select an asset to add photo.")
            return

        file_path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.gif"), ("All files", "*.*")]
        )
        if not file_path:
            return

        asset_id = self.tree.item(selected[0])["values"][0]
        
        # Copy to photos folder
        photos_dir = os.path.join(os.path.dirname(__file__), "..", "photos", "assets")
        os.makedirs(photos_dir, exist_ok=True)
        
        filename = f"asset_{asset_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{os.path.splitext(file_path)[1]}"
        dest_path = os.path.join(photos_dir, filename)
        shutil.copy2(file_path, dest_path)

        db = DatabaseManager()
        try:
            db.execute_query("UPDATE assets SET photo_path = %s WHERE id = %s", (dest_path, asset_id))
            messagebox.showinfo("Success", "Photo added successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save photo: {e}")

    # ===================== MAINTENANCE OPERATIONS =====================
    def add_maintenance(self):
        # Get asset list
        db = DatabaseManager()
        assets = db.fetch_all("SELECT id, name FROM assets ORDER BY name")
        if not assets:
            messagebox.showwarning("No Assets", "Please add assets first.")
            return

        win = tk.Toplevel(self.root)
        win.title("Add Maintenance Record")
        win.geometry("500x450")
        win.configure(bg=COLOR_BG)

        tk.Label(win, text="Asset:", bg=COLOR_BG, font=FONTS["text"]).grid(row=0, column=0, sticky="w", pady=5, padx=10)
        asset_var = ttk.Combobox(win, width=30, state="readonly")
        asset_var["values"] = [f"{a[0]} - {a[1]}" for a in assets]
        asset_var.grid(row=0, column=1, pady=5, padx=10)

        tk.Label(win, text="Type:", bg=COLOR_BG, font=FONTS["text"]).grid(row=1, column=0, sticky="w", pady=5, padx=10)
        type_var = ttk.Combobox(win, width=30, state="readonly")
        type_var["values"] = ["Repair", "Cleaning", "Inspection", "Service", "Replacement"]
        type_var.grid(row=1, column=1, pady=5, padx=10)

        tk.Label(win, text="Description:", bg=COLOR_BG, font=FONTS["text"]).grid(row=2, column=0, sticky="nw", pady=5, padx=10)
        desc_text = tk.Text(win, height=4, width=30)
        desc_text.grid(row=2, column=1, pady=5, padx=10)

        tk.Label(win, text="Cost:", bg=COLOR_BG, font=FONTS["text"]).grid(row=3, column=0, sticky="w", pady=5, padx=10)
        cost_entry = tk.Entry(win, width=32)
        cost_entry.grid(row=3, column=1, pady=5, padx=10)

        tk.Label(win, text="Performed By:", bg=COLOR_BG, font=FONTS["text"]).grid(row=4, column=0, sticky="w", pady=5, padx=10)
        performer_entry = tk.Entry(win, width=32)
        performer_entry.grid(row=4, column=1, pady=5, padx=10)

        tk.Label(win, text="Date:", bg=COLOR_BG, font=FONTS["text"]).grid(row=5, column=0, sticky="w", pady=5, padx=10)
        date_entry = DateEntry(win, width=30, background='blue', foreground='white', date_pattern='yyyy-mm-dd')
        date_entry.set_date(datetime.now())
        date_entry.grid(row=5, column=1, pady=5, padx=10)

        tk.Label(win, text="Next Maintenance:", bg=COLOR_BG, font=FONTS["text"]).grid(row=6, column=0, sticky="w", pady=5, padx=10)
        next_date_entry = DateEntry(win, width=30, background='blue', foreground='white', date_pattern='yyyy-mm-dd')
        next_date_entry.grid(row=6, column=1, pady=5, padx=10)

        def save():
            if not asset_var.get() or not type_var.get():
                messagebox.showerror("Error", "Asset and Type are required.")
                return

            asset_id = int(asset_var.get().split(" - ")[0])
            try:
                cost = float(cost_entry.get()) if cost_entry.get() else None
            except:
                cost = None

            try:
                db.execute_query("""
                    INSERT INTO asset_maintenance (asset_id, maintenance_type, description, cost, 
                    performed_by, maintenance_date, next_maintenance_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (asset_id, type_var.get(), desc_text.get("1.0", "end").strip(), cost,
                      performer_entry.get(), date_entry.get_date(), next_date_entry.get_date()))
                messagebox.showinfo("Success", "Maintenance record added!")
                win.destroy()
                self.load_maintenance()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {e}")

        tk.Button(win, text="💾 Save", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=save).grid(row=7, column=0, columnspan=2, pady=20)

    def delete_maintenance(self):
        selected = self.maint_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a record to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete this maintenance record?"):
            return
        
        maint_id = self.maint_tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM asset_maintenance WHERE id = %s", (maint_id,))
            self._reset_sequence_if_empty(db, "asset_maintenance", "asset_maintenance_id_seq")
            self.load_maintenance()
            messagebox.showinfo("Success", "Record deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    # ===================== ASSIGNMENT OPERATIONS =====================
    def assign_asset(self):
        db = DatabaseManager()
        assets = db.fetch_all("SELECT id, name FROM assets WHERE status = 'Available' ORDER BY name")
        members = db.fetch_all("SELECT id, full_name FROM members ORDER BY full_name")
        
        if not assets:
            messagebox.showwarning("No Assets", "No available assets to assign.")
            return
        if not members:
            messagebox.showwarning("No Members", "No members found.")
            return

        win = tk.Toplevel(self.root)
        win.title("Assign Asset")
        win.geometry("450x400")
        win.configure(bg=COLOR_BG)

        tk.Label(win, text="Asset:", bg=COLOR_BG, font=FONTS["text"]).grid(row=0, column=0, sticky="w", pady=5, padx=10)
        asset_var = ttk.Combobox(win, width=30, state="readonly")
        asset_var["values"] = [f"{a[0]} - {a[1]}" for a in assets]
        asset_var.grid(row=0, column=1, pady=5, padx=10)

        tk.Label(win, text="Assign To (Member):", bg=COLOR_BG, font=FONTS["text"]).grid(row=1, column=0, sticky="w", pady=5, padx=10)
        member_var = ttk.Combobox(win, width=30, state="readonly")
        member_var["values"] = [f"{m[0]} - {m[1]}" for m in members]
        member_var.grid(row=1, column=1, pady=5, padx=10)

        tk.Label(win, text="Expected Return:", bg=COLOR_BG, font=FONTS["text"]).grid(row=2, column=0, sticky="w", pady=5, padx=10)
        return_date = DateEntry(win, width=28, background='blue', foreground='white', date_pattern='yyyy-mm-dd')
        return_date.set_date(datetime.now() + timedelta(days=7))
        return_date.grid(row=2, column=1, pady=5, padx=10)

        tk.Label(win, text="Notes:", bg=COLOR_BG, font=FONTS["text"]).grid(row=3, column=0, sticky="nw", pady=5, padx=10)
        notes_text = tk.Text(win, height=4, width=30)
        notes_text.grid(row=3, column=1, pady=5, padx=10)

        def save():
            if not asset_var.get() or not member_var.get():
                messagebox.showerror("Error", "Asset and Member are required.")
                return

            asset_id = int(asset_var.get().split(" - ")[0])
            member_id = int(member_var.get().split(" - ")[0])

            try:
                db.execute_query("""
                    INSERT INTO asset_assignments (asset_id, assigned_to, assigned_by, 
                    assigned_date, expected_return_date, status)
                    VALUES (%s, %s, %s, %s, %s, 'Active')
                """, (asset_id, member_id, self.user_id, datetime.now().date(), return_date.get_date()))
                
                db.execute_query("UPDATE assets SET status = 'In Use' WHERE id = %s", (asset_id,))
                
                messagebox.showinfo("Success", "Asset assigned!")
                win.destroy()
                self.load_assignments()
                self.load_assets()
                self.load_reports()
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {e}")

        tk.Button(win, text="💾 Assign", width=15, bg=COLOR_GREEN, fg="#fff",
                  font=FONTS["text"], command=save).grid(row=4, column=0, columnspan=2, pady=20)

    def return_asset(self):
        selected = self.assign_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select an assignment to return.")
            return

        assign_id = self.assign_tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        
        try:
            # Get asset_id
            row = db.fetch_one("SELECT asset_id FROM asset_assignments WHERE id = %s", (assign_id,))
            asset_id = row[0] if row else None

            db.execute_query("""
                UPDATE asset_assignments SET status = 'Returned', actual_return_date = %s 
                WHERE id = %s
            """, (datetime.now().date(), assign_id))

            if asset_id:
                db.execute_query("UPDATE assets SET status = 'Available' WHERE id = %s", (asset_id,))

            messagebox.showinfo("Success", "Asset returned!")
            self.load_assignments()
            self.load_assets()
            self.load_reports()
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def delete_assignment(self):
        selected = self.assign_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select an assignment to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete this assignment record?"):
            return
        
        assign_id = self.assign_tree.item(selected[0])["values"][0]
        db = DatabaseManager()
        try:
            db.execute_query("DELETE FROM asset_assignments WHERE id = %s", (assign_id,))
            self._reset_sequence_if_empty(db, "asset_assignments", "asset_assignments_id_seq")
            self.load_assignments()
            messagebox.showinfo("Success", "Assignment deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")
