# modules/members.py
from modules.audit_helper import log_action
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
from tkcalendar import DateEntry
import os
import shutil
import random
import re
from datetime import datetime

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from database import DatabaseManager, hash_password

try:
    from config import PHOTOS_PATH, BRANCH_CODES, FONT_TEXT
except ImportError:
    PHOTOS_PATH = "member_photos"
    BRANCH_CODES = {"Default": "PCG-00"}
    FONT_TEXT = ("Segoe UI", 10)


# ===================== THEME =====================
PAD = 6
SMALL_PAD = 4

COLOR_BLUE = "#1f4fa3"
COLOR_LIGHT_BLUE = "#dfefff"
COLOR_RED = "#d62828"
COLOR_PURPLE = "#8e44ad"
COLOR_WHITE = "#ffffff"
COLOR_BG = "#edf5ff"
COLOR_TEXT = "#1f2937"
COLOR_MUTED = "#6b7280"
COLOR_BORDER = "#c7dbf7"



# ===================== TOOLTIP =====================
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return

        x, y, _, _ = self.widget.bbox("insert") or (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20

        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#fff8c6",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9),
            padx=6,
            pady=3,
        ).pack()

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


# ===================== TOAST =====================
def show_toast(parent, message, duration=2000):
    toast = tk.Toplevel(parent)
    toast.overrideredirect(True)
    toast.configure(bg=COLOR_BLUE)

    parent.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - 150
    y = parent.winfo_rooty() + 70
    toast.geometry(f"+{x}+{y}")

    tk.Label(
        toast,
        text=message,
        bg=COLOR_BLUE,
        fg="white",
        font=("Segoe UI", 10, "bold"),
        padx=18,
        pady=10,
    ).pack()

    toast.after(duration, toast.destroy)


# ===================== MAIN MODULE =====================
class MembersModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.user_id = user_id
        self.branch_id = branch_id

        self.root.configure(bg=COLOR_BG)

        self.editing_member_id = None
        self.add_win = None
        self.photo_path = ""
        self.photo_label = None
        self.entries = {}
        self.all_members = []

        self._setup_styles()
        self._build_main_layout()
        self.load_filters()
        self.load_members()

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

        style.configure("Card.TLabelframe", background=COLOR_WHITE, bordercolor=COLOR_BORDER)
        style.configure("Card.TLabelframe.Label", background=COLOR_WHITE, foreground=COLOR_BLUE)

    # ===================== MAIN LAYOUT =====================
    def _build_main_layout(self):
        self.main_container = tk.Frame(self.root, bg=COLOR_BG)
        self.main_container.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        self.notebook = ttk.Notebook(self.main_container)
        self.notebook.pack(fill="both", expand=True)

        self.list_frame = tk.Frame(self.notebook, bg=COLOR_BG)
        self.stats_frame = tk.Frame(self.notebook, bg=COLOR_BG)

        self.notebook.add(self.list_frame, text="👥 Member List")
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w",
            bg=COLOR_BLUE,
            fg="white",
            font=("Segoe UI", 9),
            padx=8,
            pady=3,
        )
        self.status_bar.pack(fill="x", side="bottom")

        self.setup_list_tab()
        self.setup_stats_tab()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    # ===================== HELPERS =====================
    def set_status(self, text):
        self.status_var.set(text)

    def _add_hover(self, button, normal_bg, hover_bg):
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=normal_bg))

    def _add_hover_tooltip(self, widget, normal_bg, hover_bg, tooltip_text):
        """Add hover effect and a tooltip to a widget."""
        self._add_hover(widget, normal_bg, hover_bg)
        ToolTip(widget, tooltip_text)

    def _lighten_color(self, color, factor=0.2):
        """Lighten a hex color by factor (0-1)."""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        lighter = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return f"#{lighter[0]:02x}{lighter[1]:02x}{lighter[2]:02x}"

    def _clear_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

    def _normalize_gender_label(self, value):
        if not value:
            return "Other"
        g = str(value).strip().lower()
        if g == "male":
            return "Male"
        if g == "female":
            return "Female"
        return "Other"

    def _safe_set_widget_value(self, widget, value):
        if value is None:
            value = ""
        try:
            if isinstance(widget, DateEntry):
                if value and re.match(r"^\d{4}-\d{2}-\d{2}$", str(value)):
                    widget.set_date(value)
            elif isinstance(widget, ttk.Combobox):
                widget.set(value)
            else:
                widget.delete(0, tk.END)
                widget.insert(0, value)
        except Exception:
            pass

    def _extract_form_values(self):
        values = {}
        for key, widget in self.entries.items():
            try:
                values[key] = widget.get().strip()
            except Exception:
                values[key] = ""
        return values

    def _validate_date_string(self, date_str):
        if not date_str:
            return True
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _shorten_label(self, text, max_len=16):
        text = str(text or "")
        return text if len(text) <= max_len else text[: max_len - 3] + "..."

    def _save_photo_copy(self, full_name, source_path):
        if not source_path:
            return ""

        if not os.path.exists(source_path):
            raise FileNotFoundError("Selected photo file no longer exists.")

        os.makedirs(PHOTOS_PATH, exist_ok=True)

        ext = os.path.splitext(source_path)[1] or ".jpg"
        safe_name = "".join(c for c in full_name if c.isalnum() or c in (" ", "_", "-")).strip()
        safe_name = safe_name.replace(" ", "_") or "member_photo"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        destination = os.path.join(PHOTOS_PATH, f"{safe_name}_{timestamp}{ext}")
        shutil.copy2(source_path, destination)
        return destination

    # ===================== DB HELPERS =====================
    def _get_member_record_by_member_id(self, member_id):
        db = DatabaseManager()
        row = db.fetch_one("""
            SELECT
                id, member_id, full_name, gender, phone, email, address, occupation,
                marital_status, parent_name, school_class, branch_id, group_id, department_id,
                baptism_date, baptized_by, baptism_place, confirmation_date, confirmed_by,
                confirmation_place, date_joined, photo, birth_date, place_of_birth
            FROM members
            WHERE member_id = ?
        """, (member_id,))

        if not row:
            return None

        keys = [
            "id", "member_id", "full_name", "gender", "phone", "email", "address",
            "occupation", "marital_status", "parent_name", "school_class", "branch_id",
            "group_id", "department_id", "baptism_date", "baptized_by", "baptism_place",
            "confirmation_date", "confirmed_by", "confirmation_place", "date_joined",
            "photo", "birth_date", "place_of_birth"
        ]
        return dict(zip(keys, row))

    def _get_member_record_by_internal_id(self, internal_id):
        db = DatabaseManager()
        row = db.fetch_one("""
            SELECT
                id, member_id, full_name, gender, phone, email, address, occupation,
                marital_status, parent_name, school_class, branch_id, group_id, department_id,
                baptism_date, baptized_by, baptism_place, confirmation_date, confirmed_by,
                confirmation_place, date_joined, photo, birth_date, place_of_birth
            FROM members
            WHERE id = ?
        """, (internal_id,))

        if not row:
            return None

        keys = [
            "id", "member_id", "full_name", "gender", "phone", "email", "address",
            "occupation", "marital_status", "parent_name", "school_class", "branch_id",
            "group_id", "department_id", "baptism_date", "baptized_by", "baptism_place",
            "confirmation_date", "confirmed_by", "confirmation_place", "date_joined",
            "photo", "birth_date", "place_of_birth"
        ]
        return dict(zip(keys, row))

    def _record_for_audit(self, record):
        if not record:
            return None
        return {
            "member_id": record.get("member_id"),
            "full_name": record.get("full_name"),
            "gender": record.get("gender"),
            "phone": record.get("phone"),
            "email": record.get("email"),
            "address": record.get("address"),
            "occupation": record.get("occupation"),
            "marital_status": record.get("marital_status"),
            "parent_name": record.get("parent_name"),
            "school_class": record.get("school_class"),
            "branch_id": record.get("branch_id"),
            "group_id": record.get("group_id"),
            "department_id": record.get("department_id"),
            "baptism_date": record.get("baptism_date"),
            "baptized_by": record.get("baptized_by"),
            "baptism_place": record.get("baptism_place"),
            "confirmation_date": record.get("confirmation_date"),
            "confirmed_by": record.get("confirmed_by"),
            "confirmation_place": record.get("confirmation_place"),
            "date_joined": record.get("date_joined"),
            "photo": record.get("photo"),
            "birth_date": record.get("birth_date"),
            "place_of_birth": record.get("place_of_birth"),
        }

    def _get_id_or_create(self, table, name):
        if not name or not name.strip():
            return None

        name = name.strip()
        db = DatabaseManager()

        found = db.fetch_one(f"SELECT id FROM {table} WHERE name = ?", (name,))
        if found:
            return found[0]

        db.execute_query(f"INSERT INTO {table} (name) VALUES (?)", (name,))
        found = db.fetch_one(f"SELECT id FROM {table} WHERE name = ?", (name,))
        return found[0] if found else None

    def _generate_member_id(self, branch_name):
        prefix = BRANCH_CODES.get(branch_name, "PCG-00")
        db = DatabaseManager()

        branch = db.fetch_one("SELECT id FROM branches WHERE name = ?", (branch_name,))
        if not branch:
            return f"{prefix}-0001"

        branch_id = branch[0]
        count_row = db.fetch_one("SELECT COUNT(*) FROM members WHERE branch_id = ?", (branch_id,))
        count = (count_row[0] if count_row else 0) + 1
        return f"{prefix}-{str(count).zfill(4)}"

    # ===================== LIST TAB =====================
    def setup_list_tab(self):
        self.list_frame.grid_rowconfigure(2, weight=1)
        self.list_frame.grid_columnconfigure(0, weight=1)

        toolbar = tk.Frame(self.list_frame, bg=COLOR_BG)
        toolbar.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, SMALL_PAD))
        toolbar.grid_columnconfigure(0, weight=1)
        toolbar.grid_columnconfigure(1, weight=0)

        left_buttons = tk.Frame(toolbar, bg=COLOR_BG)
        left_buttons.grid(row=0, column=0, sticky="w")

        right_search = tk.Frame(toolbar, bg=COLOR_BG)
        right_search.grid(row=0, column=1, sticky="e")

        # Buttons with tooltips
        for text, width, bg, cmd, tooltip in [
            ("➕ Add Member", 14, COLOR_RED, self._add_member_window, "Add a new member"),
            ("✏️ Edit Selected", 14, COLOR_BLUE, self._edit_selected, "Edit the selected member"),
            ("🗑️ Delete Selected", 16, "#374151", self._delete_selected, "Delete selected member(s)"),
            ("📄 Export PDF", 11, COLOR_BLUE, lambda: messagebox.showinfo("Export", "PDF export placeholder"), "Export members to PDF"),
            ("📊 Export Excel", 11, COLOR_BLUE, lambda: messagebox.showinfo("Export", "Excel export placeholder"), "Export members to Excel"),
            ("🔑 Set PIN", 11, "#f39c12", self.set_member_pin, "Set a 4-digit PIN for the selected member"),
            ("📋 Committees", 11, COLOR_PURPLE, self.show_member_committees, "Manage committees for the selected member"),
            ("🔐 Set Security Q", 15, "#8e44ad", self.set_security_questions, "Set security questions for PIN reset"),
        
        ]:
            btn = tk.Button(left_buttons, text=text, width=width, bg=bg, fg="white", font=("Segoe UI", 9), command=cmd)
            btn.pack(side="left", padx=SMALL_PAD)
            self._add_hover_tooltip(btn, bg, self._lighten_color(bg), tooltip)

        # Search area
        tk.Label(right_search, text="🔍 Search:", bg=COLOR_BG, fg=COLOR_TEXT, font=("Segoe UI", 9)).pack(side="left", padx=SMALL_PAD)

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.filter_members())
        tk.Entry(right_search, textvariable=self.search_var, font=("Segoe UI", 9), width=20).pack(side="left", padx=SMALL_PAD)

        clear_search_btn = tk.Button(right_search, text="✖", bg=COLOR_BG, fg=COLOR_TEXT, bd=0, font=("Segoe UI", 9), command=self.clear_filters)
        clear_search_btn.pack(side="left", padx=2)
        self._add_hover_tooltip(clear_search_btn, COLOR_BG, "#cccccc", "Clear search")

        filter_card = tk.Frame(self.list_frame, bg=COLOR_WHITE, bd=1, relief="solid")
        filter_card.grid(row=1, column=0, sticky="ew", padx=PAD, pady=(0, SMALL_PAD))

        filter_row = tk.Frame(filter_card, bg=COLOR_WHITE)
        filter_row.pack(fill="x", padx=8, pady=6)

        # Branch filter
        tk.Label(filter_row, text="Branch:", bg=COLOR_WHITE, font=("Segoe UI", 9)).pack(side="left", padx=SMALL_PAD)
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(filter_row, textvariable=self.branch_var, values=["All"], state="readonly", width=13)
        self.branch_combo.pack(side="left", padx=SMALL_PAD)
        self.branch_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        tk.Label(filter_row, text="Group:", bg=COLOR_WHITE, font=("Segoe UI", 9)).pack(side="left", padx=SMALL_PAD)
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(filter_row, textvariable=self.group_var, values=["All"], state="readonly", width=13)
        self.group_combo.pack(side="left", padx=SMALL_PAD)
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        tk.Label(filter_row, text="Department:", bg=COLOR_WHITE, font=("Segoe UI", 9)).pack(side="left", padx=SMALL_PAD)
        self.dept_var = tk.StringVar()
        self.dept_combo = ttk.Combobox(filter_row, textvariable=self.dept_var, values=["All"], state="readonly", width=13)
        self.dept_combo.pack(side="left", padx=SMALL_PAD)
        self.dept_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        tk.Label(filter_row, text="Gender:", bg=COLOR_WHITE, font=("Segoe UI", 9)).pack(side="left", padx=SMALL_PAD)
        self.gender_var = tk.StringVar()
        self.gender_combo = ttk.Combobox(filter_row, textvariable=self.gender_var, values=["All", "Male", "Female", "Other"], state="readonly", width=10)
        self.gender_combo.pack(side="left", padx=SMALL_PAD)
        self.gender_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        tk.Label(filter_row, text="Marital:", bg=COLOR_WHITE, font=("Segoe UI", 9)).pack(side="left", padx=SMALL_PAD)
        self.marital_var = tk.StringVar()
        self.marital_combo = ttk.Combobox(filter_row, textvariable=self.marital_var, values=["All", "Single", "Married", "Divorced", "Widowed"], state="readonly", width=11)
        self.marital_combo.pack(side="left", padx=SMALL_PAD)
        self.marital_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_members())

        clear_filters_btn = tk.Button(filter_row, text="✖ Clear Filters", bg=COLOR_WHITE, fg=COLOR_RED, bd=0, font=("Segoe UI", 9), command=self.clear_filters)
        clear_filters_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover_tooltip(clear_filters_btn, COLOR_WHITE, "#cccccc", "Clear all filters")

        content_card = tk.Frame(self.list_frame, bg=COLOR_WHITE, bd=1, relief="solid")
        content_card.grid(row=2, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        content_card.grid_rowconfigure(1, weight=1)
        content_card.grid_columnconfigure(0, weight=1)

        info_bar = tk.Frame(content_card, bg=COLOR_WHITE)
        info_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
        self.member_count_var = tk.StringVar(value="Members: 0")
        tk.Label(info_bar, textvariable=self.member_count_var, bg=COLOR_WHITE, fg=COLOR_BLUE, font=("Segoe UI", 9, "bold")).pack(anchor="w")

        table_container = tk.Frame(content_card, bg=COLOR_WHITE)
        table_container.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        columns = ("#", "Member ID", "Full Name", "Gender", "Phone", "Email", "Branch", "Group", "Department", "DB_ID")

        self.tree = ttk.Treeview(table_container, columns=columns, show="headings", selectmode="extended")
        self.tree.grid(row=0, column=0, sticky="nsew")

        vsb = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        hsb = ttk.Scrollbar(table_container, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        widths = [40, 110, 190, 80, 120, 190, 120, 110, 120, 0]
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=40 if w > 0 else 0, stretch=(w > 0))

        self.tree.tag_configure("evenrow", background="#ffffff")
        self.tree.tag_configure("oddrow", background="#f6fbff")
        self.tree.bind("<Double-1>", self._edit_member)

    # ===================== LOAD / FILTER =====================
    def load_filters(self):
        db = DatabaseManager()

        branches = [r[0] for r in db.fetch_all("SELECT name FROM branches ORDER BY name")]
        groups = [r[0] for r in db.fetch_all("SELECT name FROM groups ORDER BY name")]
        depts = [r[0] for r in db.fetch_all("SELECT name FROM departments ORDER BY name")]

        self.branch_combo["values"] = ["All"] + branches
        self.group_combo["values"] = ["All"] + groups
        self.dept_combo["values"] = ["All"] + depts
        self.gender_combo["values"] = ["All", "Male", "Female", "Other"]
        self.marital_combo["values"] = ["All", "Single", "Married", "Divorced", "Widowed"]

        self.branch_var.set("All")
        self.group_var.set("All")
        self.dept_var.set("All")
        self.gender_var.set("All")
        self.marital_var.set("All")

    def load_members(self):
        self._clear_tree()
        self.member_data = []  # list of dicts with all member info

        db = DatabaseManager()
        query = """
            SELECT
                m.id,
                m.member_id,
                m.full_name,
                m.gender,
                m.phone,
                m.email,
                m.marital_status,
                b.name,
                g.name,
                d.name
            FROM members m
            LEFT JOIN branches b ON m.branch_id = b.id
            LEFT JOIN groups g ON m.group_id = g.id
            LEFT JOIN departments d ON m.department_id = d.id
        """
        params = []
        if self.branch_id:
            query += " WHERE m.branch_id = ?"
            params.append(self.branch_id)
        query += " ORDER BY m.full_name"
        rows = db.fetch_all(query, params)

        for row in rows:
            internal_id, member_id, full_name, gender, phone, email, marital, branch, group, dept = row
            normalized_gender = self._normalize_gender_label(gender)
            self.member_data.append({
                "internal_id": internal_id,
                "member_id": member_id or "",
                "full_name": full_name or "",
                "gender": normalized_gender,
                "phone": phone or "",
                "email": email or "",
                "marital": marital or "",
                "branch": branch or "",
                "group": group or "",
                "dept": dept or "",
                "search_text": f"{member_id or ''} {full_name or ''} {phone or ''} {email or ''}".lower()
            })

        self.filter_members()
        self.set_status(f"Loaded {len(rows)} member(s)")

    def filter_members(self):
        # Clear tree
        for row in self.tree.get_children():
            self.tree.delete(row)

        search_term = self.search_var.get().strip().lower()
        branch_filter = self.branch_var.get()
        group_filter = self.group_var.get()
        dept_filter = self.dept_var.get()
        gender_filter = self.gender_var.get()
        marital_filter = self.marital_var.get()

        visible_members = []
        for m in self.member_data:
            match = True
            if branch_filter != "All" and m["branch"] != branch_filter:
                match = False
            elif group_filter != "All" and m["group"] != group_filter:
                match = False
            elif dept_filter != "All" and m["dept"] != dept_filter:
                match = False
            elif gender_filter != "All" and m["gender"] != gender_filter:
                match = False
            elif marital_filter != "All" and m["marital"] != marital_filter:
                match = False
            elif search_term and search_term not in m["search_text"]:
                match = False

            if match:
                visible_members.append(m)

        # Insert with sequential row numbers
        for idx, m in enumerate(visible_members, start=1):
            values = [
                idx,                     # Row number
                m["member_id"],
                m["full_name"],
                m["gender"],
                m["phone"],
                m["email"],
                m["branch"],
                m["group"],
                m["dept"],
                m["internal_id"]          # hidden DB ID
            ]
            tag = "evenrow" if idx % 2 == 0 else "oddrow"
            self.tree.insert("", tk.END, values=values, tags=(tag,))

        self.member_count_var.set(f"Members: {len(visible_members)}")
        self.set_status(f"Showing {len(visible_members)} member(s)")

    def clear_filters(self):
        self.search_var.set("")
        self.branch_var.set("All")
        self.group_var.set("All")
        self.dept_var.set("All")
        self.gender_var.set("All")
        self.marital_var.set("All")
        self.filter_members()

    # ===================== DELETE =====================
    def _delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select at least one member to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", f"Delete {len(selected)} member(s)?"):
            return

        db = DatabaseManager()

        for item in selected:
            values = self.tree.item(item, "values")
            internal_id = values[9]  # Internal ID is now at index 9

            old_record = self._get_member_record_by_internal_id(internal_id)
            old_values = self._record_for_audit(old_record)

            db.execute_query("DELETE FROM attendance WHERE member_id = ?", (internal_id,))
            db.execute_query("DELETE FROM family_members WHERE member_id = ?", (internal_id,))
            db.execute_query("DELETE FROM financial_records WHERE member_id = ?", (internal_id,))
            db.execute_query("DELETE FROM member_portal WHERE member_id = ?", (internal_id,))
            db.execute_query("DELETE FROM members WHERE id = ?", (internal_id,))

            if self.user_id and old_values:
                log_action(
                    table_name="members",
                    record_id=internal_id,
                    action="DELETE",
                    old_values=old_values,
                    user_id=self.user_id
                )

        self.load_members()
        self.refresh_stats()
        show_toast(self.root, f"{len(selected)} member(s) deleted")
        self.set_status(f"Deleted {len(selected)} member(s)")

    # ===================== EDIT =====================
    def _edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a member to edit.")
            return

        member_id = self.tree.item(selected[0], "values")[1]   # Member ID is now at index 1
        self._add_member_window(member_id)

    def _edit_member(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        member_id = self.tree.item(selected[0], "values")[1]
        self._add_member_window(member_id)

    # ===================== ADD / EDIT WINDOW =====================
    def _add_member_window(self, member_id=None):
        self.editing_member_id = member_id
        self.entries = {}
        self.photo_path = ""

        win = tk.Toplevel(self.root)
        win.title("Add New Member" if not member_id else "Edit Member")
        win.geometry("860x680")
        win.minsize(760, 600)
        win.configure(bg=COLOR_BG)
        win.transient(self.root)
        win.grab_set()
        win.lift()
        win.focus_force()

        # Main layout: scrollable body + fixed footer
        win.grid_rowconfigure(0, weight=1)
        win.grid_rowconfigure(1, weight=0)
        win.grid_columnconfigure(0, weight=1)

        body = tk.Frame(win, bg=COLOR_BG)
        body.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 0))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(body, bg=COLOR_BG, highlightthickness=0)
        canvas.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=v_scroll.set)

        form_container = tk.Frame(canvas, bg=COLOR_BG)
        canvas.create_window((0, 0), window=form_container, anchor="nw")

        def update_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        form_container.bind("<Configure>", update_scroll_region)

        # Personal
        card1 = ttk.LabelFrame(form_container, text="👤 Personal Information", padding=10, style="Card.TLabelframe")
        card1.pack(fill="x", padx=10, pady=6)

        fields_personal = [
            ("Full Name *", "entry"),
            ("Gender", "combobox", ["Male", "Female", "Other"]),
            ("Phone", "entry"),
            ("Email", "entry"),
            ("Address", "entry"),
            ("Occupation", "entry"),
            ("Marital Status", "entry"),
            ("Parent Name", "entry"),
            ("School/Class", "entry"),
        ]

        for i, field in enumerate(fields_personal):
            if len(field) == 2:
                label, typ = field
                values = None
            else:
                label, typ, values = field

            tk.Label(card1, text=label, bg=COLOR_WHITE, font=("Segoe UI", 9)).grid(row=i, column=0, sticky="w", padx=5, pady=4)

            if typ == "entry":
                widget = ttk.Entry(card1, width=38)
            else:
                widget = ttk.Combobox(card1, values=values, width=35, state="readonly")

            widget.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            self.entries[label] = widget

        # --- NEW FIELDS: Date of Birth and Place of Birth ---
        next_row = len(fields_personal)  # current row index after the loop

        # Date of Birth
        tk.Label(card1, text="Date of Birth:", bg=COLOR_WHITE, font=("Segoe UI", 9)).grid(row=next_row, column=0, sticky="w", padx=5, pady=4)
        dob_entry = DateEntry(
            card1,
            width=35,
            background=COLOR_BLUE,
            foreground="white",
            borderwidth=2,
            date_pattern="yyyy-mm-dd",
            font=("Segoe UI", 9)
        )
        dob_entry.grid(row=next_row, column=1, sticky="w", padx=5, pady=4)
        self.entries["Date of Birth"] = dob_entry
        next_row += 1

        # Place of Birth
        tk.Label(card1, text="Place of Birth:", bg=COLOR_WHITE, font=("Segoe UI", 9)).grid(row=next_row, column=0, sticky="w", padx=5, pady=4)
        pob_entry = ttk.Entry(card1, width=38)
        pob_entry.grid(row=next_row, column=1, sticky="w", padx=5, pady=4)
        self.entries["Place of Birth"] = pob_entry
        # --- END NEW FIELDS ---

        # Church
        card2 = ttk.LabelFrame(form_container, text="⛪ Church Information", padding=10, style="Card.TLabelframe")
        card2.pack(fill="x", padx=10, pady=6)

        db = DatabaseManager()
        branches = [r[0] for r in db.fetch_all("SELECT name FROM branches ORDER BY name")] or ["Default"]
        groups = [r[0] for r in db.fetch_all("SELECT name FROM groups ORDER BY name")] or ["Default"]
        depts = [r[0] for r in db.fetch_all("SELECT name FROM departments ORDER BY name")] or ["Default"]

        for i, (label, values) in enumerate([
            ("Branch *", branches),
            ("Group *", groups),
            ("Department *", depts)
        ]):
            tk.Label(card2, text=label, bg=COLOR_WHITE, font=("Segoe UI", 9)).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            combo = ttk.Combobox(card2, values=values, width=35)
            combo.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            self.entries[label] = combo

        # Dates
        card3 = ttk.LabelFrame(form_container, text="📅 Important Dates", padding=10, style="Card.TLabelframe")
        card3.pack(fill="x", padx=10, pady=6)

        date_fields = ["Baptism Date", "Confirmation Date", "Date Joined"]
        for i, label in enumerate(date_fields):
            tk.Label(card3, text=label, bg=COLOR_WHITE, font=("Segoe UI", 9)).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            entry = DateEntry(
                card3,
                width=35,
                background=COLOR_BLUE,
                foreground="white",
                borderwidth=2,
                date_pattern="yyyy-mm-dd",
                font=("Segoe UI", 9)
            )
            entry.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            self.entries[label] = entry

        extras = ["Baptized By", "Baptism Place", "Confirmed By", "Confirmation Place"]
        for i, label in enumerate(extras, start=len(date_fields)):
            tk.Label(card3, text=label, bg=COLOR_WHITE, font=("Segoe UI", 9)).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            entry = ttk.Entry(card3, width=38)
            entry.grid(row=i, column=1, sticky="w", padx=5, pady=4)
            self.entries[label] = entry

        # Photo
        card4 = ttk.LabelFrame(form_container, text="📸 Member Photo", padding=10, style="Card.TLabelframe")
        card4.pack(fill="x", padx=10, pady=6)

        upload_btn = tk.Button(card4, text="Upload Photo", bg=COLOR_BLUE, fg="white", font=("Segoe UI", 9), command=self._upload_photo)
        upload_btn.pack(pady=4)
        self._add_hover_tooltip(upload_btn, COLOR_BLUE, self._lighten_color(COLOR_BLUE), "Upload a photo for this member")

        self.photo_label = tk.Label(card4, bg=COLOR_WHITE)
        self.photo_label.pack(pady=6)

        # Fixed footer with buttons
        footer = tk.Frame(win, bg=COLOR_WHITE, bd=1, relief="solid")
        footer.grid(row=1, column=0, sticky="ew", padx=0, pady=(6, 0))
        footer.grid_columnconfigure(0, weight=1)

        footer_buttons = tk.Frame(footer, bg=COLOR_WHITE)
        footer_buttons.pack(fill="x", padx=10, pady=8)

        cancel_btn = tk.Button(
            footer_buttons,
            text="❌ Cancel",
            bg="#9ca3af",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=12,
            command=win.destroy
        )
        cancel_btn.pack(side="right", padx=5)
        self._add_hover_tooltip(cancel_btn, "#9ca3af", self._lighten_color("#9ca3af"), "Cancel and close window")

        save_btn = tk.Button(
            footer_buttons,
            text="💾 Save Member",
            bg=COLOR_RED,
            fg="white",
            font=("Segoe UI", 10, "bold"),
            width=15,
            command=self._save_member
        )
        save_btn.pack(side="right", padx=5)
        self._add_hover_tooltip(save_btn, COLOR_RED, self._lighten_color(COLOR_RED), "Save member information")

        if member_id:
            self._load_member_data(member_id)

        self.add_win = win

    def _load_member_data(self, member_id):
        record = self._get_member_record_by_member_id(member_id)
        if not record:
            messagebox.showerror("Error", "Member not found.")
            return

        field_map = {
            "Full Name *": record["full_name"],
            "Gender": self._normalize_gender_label(record["gender"]),
            "Phone": record["phone"],
            "Email": record["email"],
            "Address": record["address"],
            "Occupation": record["occupation"],
            "Marital Status": record["marital_status"],
            "Parent Name": record["parent_name"],
            "School/Class": record["school_class"],
        }

        for key, value in field_map.items():
            self._safe_set_widget_value(self.entries[key], value)

        db = DatabaseManager()
        branch_name = db.fetch_one("SELECT name FROM branches WHERE id = ?", (record["branch_id"],))
        group_name = db.fetch_one("SELECT name FROM groups WHERE id = ?", (record["group_id"],))
        dept_name = db.fetch_one("SELECT name FROM departments WHERE id = ?", (record["department_id"],))

        if branch_name:
            self.entries["Branch *"].set(branch_name[0])
        if group_name:
            self.entries["Group *"].set(group_name[0])
        if dept_name:
            self.entries["Department *"].set(dept_name[0])

        self._safe_set_widget_value(self.entries["Baptism Date"], record["baptism_date"])
        self._safe_set_widget_value(self.entries["Confirmation Date"], record["confirmation_date"])
        self._safe_set_widget_value(self.entries["Date Joined"], record["date_joined"])
        self._safe_set_widget_value(self.entries["Baptized By"], record["baptized_by"])
        self._safe_set_widget_value(self.entries["Baptism Place"], record["baptism_place"])
        self._safe_set_widget_value(self.entries["Confirmed By"], record["confirmed_by"])
        self._safe_set_widget_value(self.entries["Confirmation Place"], record["confirmation_place"])

        # NEW: Load Date of Birth and Place of Birth
        self._safe_set_widget_value(self.entries["Date of Birth"], record.get("birth_date"))
        self._safe_set_widget_value(self.entries["Place of Birth"], record.get("place_of_birth"))

        photo_file = record["photo"]
        if photo_file and os.path.exists(photo_file):
            self.photo_path = photo_file
            try:
                img = Image.open(photo_file).resize((100, 100))
                img_tk = ImageTk.PhotoImage(img)
                self.photo_label.config(image=img_tk)
                self.photo_label.image = img_tk
            except Exception:
                pass

    def _upload_photo(self):
        parent_window = self.add_win if self.add_win and self.add_win.winfo_exists() else self.root

        file_path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")],
            parent=parent_window
        )
        if not file_path:
            return

        self.photo_path = file_path
        try:
            img = Image.open(file_path).resize((100, 100))
            img_tk = ImageTk.PhotoImage(img)
            self.photo_label.config(image=img_tk)
            self.photo_label.image = img_tk
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")

    def _save_member(self):
        values = self._extract_form_values()

        for field in ["Full Name *", "Branch *", "Group *", "Department *"]:
            if not values.get(field):
                messagebox.showerror("Error", f"{field} is required.")
                return

        if values.get("Email") and "@" not in values["Email"]:
            messagebox.showerror("Error", "Invalid email address.")
            return

        if values.get("Phone") and not re.match(r"^[\d+\-\s()]+$", values["Phone"]):
            messagebox.showerror("Error", "Phone contains invalid characters.")
            return

        for field in ["Baptism Date", "Confirmation Date", "Date Joined", "Date of Birth"]:
            if not self._validate_date_string(values.get(field, "")):
                messagebox.showerror("Error", f"Invalid date for {field}. Use YYYY-MM-DD.")
                return

        db = DatabaseManager()

        branch_id = self._get_id_or_create("branches", values["Branch *"])
        group_id = self._get_id_or_create("groups", values["Group *"])
        dept_id = self._get_id_or_create("departments", values["Department *"])

        if not branch_id or not group_id or not dept_id:
            messagebox.showerror("Error", "Failed to resolve branch, group, or department.")
            return

        existing_photo = ""
        if self.editing_member_id:
            old_rec = self._get_member_record_by_member_id(self.editing_member_id)
            if old_rec:
                existing_photo = old_rec.get("photo") or ""

        photo_file = existing_photo
        try:
            if self.photo_path:
                if not existing_photo or os.path.abspath(self.photo_path) != os.path.abspath(existing_photo):
                    photo_file = self._save_photo_copy(values["Full Name *"], self.photo_path)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save photo: {e}")
            return

        normalized_gender = self._normalize_gender_label(values.get("Gender"))

        # Extract new fields
        birth_date = values.get("Date of Birth") or None
        place_of_birth = values.get("Place of Birth") or None

        if self.editing_member_id:
            old_record = self._get_member_record_by_member_id(self.editing_member_id)
            old_values = self._record_for_audit(old_record)
            old_id = old_record["id"] if old_record else None

            query = """
                UPDATE members SET
                    full_name=?, gender=?, phone=?, email=?, address=?, occupation=?,
                    marital_status=?, parent_name=?, school_class=?, branch_id=?, group_id=?, department_id=?,
                    baptism_date=?, baptized_by=?, baptism_place=?, confirmation_date=?, confirmed_by=?,
                    confirmation_place=?, date_joined=?, photo=?, birth_date=?, place_of_birth=?
                WHERE member_id=?
            """
            params = (
                values["Full Name *"], normalized_gender, values.get("Phone", ""), values.get("Email", ""),
                values.get("Address", ""), values.get("Occupation", ""), values.get("Marital Status", ""),
                values.get("Parent Name", ""), values.get("School/Class", ""),
                branch_id, group_id, dept_id,
                values.get("Baptism Date", ""), values.get("Baptized By", ""), values.get("Baptism Place", ""),
                values.get("Confirmation Date", ""), values.get("Confirmed By", ""), values.get("Confirmation Place", ""),
                values.get("Date Joined", ""), photo_file, birth_date, place_of_birth,
                self.editing_member_id
            )

            if db.execute_query(query, params):
                if self.user_id and old_id:
                    log_action(
                        table_name="members",
                        record_id=old_id,
                        action="UPDATE",
                        old_values=old_values,
                        new_values={
                            "member_id": self.editing_member_id,
                            "full_name": values["Full Name *"],
                            "gender": normalized_gender,
                            "phone": values.get("Phone", ""),
                            "email": values.get("Email", ""),
                            "address": values.get("Address", ""),
                            "occupation": values.get("Occupation", ""),
                            "marital_status": values.get("Marital Status", ""),
                            "parent_name": values.get("Parent Name", ""),
                            "school_class": values.get("School/Class", ""),
                            "branch_id": branch_id,
                            "group_id": group_id,
                            "department_id": dept_id,
                            "baptism_date": values.get("Baptism Date", ""),
                            "baptized_by": values.get("Baptized By", ""),
                            "baptism_place": values.get("Baptism Place", ""),
                            "confirmation_date": values.get("Confirmation Date", ""),
                            "confirmed_by": values.get("Confirmed By", ""),
                            "confirmation_place": values.get("Confirmation Place", ""),
                            "date_joined": values.get("Date Joined", ""),
                            "photo": photo_file,
                            "birth_date": birth_date,
                            "place_of_birth": place_of_birth,
                        },
                        user_id=self.user_id
                    )

                messagebox.showinfo("Success", f"Member '{values['Full Name *']}' updated.")
                self.add_win.destroy()
                self.load_members()
                self.refresh_stats()
            else:
                messagebox.showerror("Error", "Could not update member.")

        else:
            member_id = self._generate_member_id(values["Branch *"])
            query = """
                INSERT INTO members (
                    member_id, full_name, gender, phone, email, address, occupation,
                    marital_status, parent_name, school_class, branch_id, group_id, department_id,
                    baptism_date, baptized_by, baptism_place, confirmation_date, confirmed_by,
                    confirmation_place, date_joined, photo, birth_date, place_of_birth
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """
            params = (
                member_id, values["Full Name *"], normalized_gender, values.get("Phone", ""),
                values.get("Email", ""), values.get("Address", ""), values.get("Occupation", ""),
                values.get("Marital Status", ""), values.get("Parent Name", ""), values.get("School/Class", ""),
                branch_id, group_id, dept_id,
                values.get("Baptism Date", ""), values.get("Baptized By", ""), values.get("Baptism Place", ""),
                values.get("Confirmation Date", ""), values.get("Confirmed By", ""), values.get("Confirmation Place", ""),
                values.get("Date Joined", ""), photo_file, birth_date, place_of_birth
            )

            if db.execute_query(query, params):
                new_record = self._get_member_record_by_member_id(member_id)
                new_id = new_record["id"] if new_record else None

                if self.user_id and new_id:
                    log_action(
                        table_name="members",
                        record_id=new_id,
                        action="INSERT",
                        new_values={
                            "member_id": member_id,
                            "full_name": values["Full Name *"],
                            "gender": normalized_gender,
                            "phone": values.get("Phone", ""),
                            "email": values.get("Email", ""),
                            "address": values.get("Address", ""),
                            "occupation": values.get("Occupation", ""),
                            "marital_status": values.get("Marital Status", ""),
                            "parent_name": values.get("Parent Name", ""),
                            "school_class": values.get("School/Class", ""),
                            "branch_id": branch_id,
                            "group_id": group_id,
                            "department_id": dept_id,
                            "baptism_date": values.get("Baptism Date", ""),
                            "baptized_by": values.get("Baptized By", ""),
                            "baptism_place": values.get("Baptism Place", ""),
                            "confirmation_date": values.get("Confirmation Date", ""),
                            "confirmed_by": values.get("Confirmed By", ""),
                            "confirmation_place": values.get("Confirmation Place", ""),
                            "date_joined": values.get("Date Joined", ""),
                            "photo": photo_file,
                            "birth_date": birth_date,
                            "place_of_birth": place_of_birth,
                        },
                        user_id=self.user_id
                    )

                messagebox.showinfo("Success", f"Member '{values['Full Name *']}' added with ID {member_id}")
                self.add_win.destroy()
                self.load_members()
                self.load_filters()
                self.refresh_stats()
            else:
                messagebox.showerror("Error", "Could not save member.")

    # ===================== STATS TAB =====================
    def setup_stats_tab(self):
        self.stats_frame.grid_rowconfigure(1, weight=1)
        self.stats_frame.grid_columnconfigure(0, weight=1)

        header = tk.Frame(self.stats_frame, bg=COLOR_BG)
        header.grid(row=0, column=0, sticky="ew", padx=PAD, pady=(PAD, SMALL_PAD))
        header.grid_columnconfigure(0, weight=1)

        tk.Label(header, text="Statistics Overview", bg=COLOR_BG, fg=COLOR_BLUE, font=("Segoe UI", 12, "bold")).grid(row=0, column=0, sticky="w")

        refresh_btn = tk.Button(header, text="🔄 Refresh", bg=COLOR_BLUE, fg="white", font=("Segoe UI", 9), command=self.refresh_stats)
        refresh_btn.grid(row=0, column=1, sticky="e")
        self._add_hover_tooltip(refresh_btn, COLOR_BLUE, self._lighten_color(COLOR_BLUE), "Refresh statistics")

        dashboard = tk.Frame(self.stats_frame, bg=COLOR_BG)
        dashboard.grid(row=1, column=0, sticky="nsew", padx=PAD, pady=(0, PAD))
        dashboard.grid_rowconfigure(1, weight=1)
        dashboard.grid_columnconfigure(0, weight=1)

        self.summary_row = tk.Frame(dashboard, bg=COLOR_BG)
        self.summary_row.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        for i in range(4):
            self.summary_row.grid_columnconfigure(i, weight=1)

        self.card_total = self._create_stat_card(self.summary_row, "Total Members", "0", COLOR_BLUE)
        self.card_total.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.card_male = self._create_stat_card(self.summary_row, "Male", "0", "#2a9df4")
        self.card_male.grid(row=0, column=1, sticky="ew", padx=4)

        self.card_female = self._create_stat_card(self.summary_row, "Female", "0", COLOR_RED)
        self.card_female.grid(row=0, column=2, sticky="ew", padx=4)

        self.card_other = self._create_stat_card(self.summary_row, "Other", "0", "#f39c12")
        self.card_other.grid(row=0, column=3, sticky="ew", padx=(4, 0))

        charts_row = tk.Frame(dashboard, bg=COLOR_BG)
        charts_row.grid(row=1, column=0, sticky="nsew")
        charts_row.grid_rowconfigure(0, weight=1)
        charts_row.grid_columnconfigure(0, weight=1)
        charts_row.grid_columnconfigure(1, weight=1)

        self.gender_card = tk.Frame(charts_row, bg=COLOR_WHITE, bd=1, relief="solid")
        self.gender_card.grid(row=0, column=0, sticky="nsew", padx=(0, 3))

        self.branch_card = tk.Frame(charts_row, bg=COLOR_WHITE, bd=1, relief="solid")
        self.branch_card.grid(row=0, column=1, sticky="nsew", padx=(3, 0))

        tk.Label(self.gender_card, text="Gender Distribution", bg=COLOR_WHITE, fg=COLOR_BLUE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 0))
        tk.Label(self.branch_card, text="Members by Branch", bg=COLOR_WHITE, fg=COLOR_BLUE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=8, pady=(8, 0))

        self.gender_chart_area = tk.Frame(self.gender_card, bg=COLOR_WHITE)
        self.gender_chart_area.pack(fill="both", expand=True, padx=4, pady=4)

        self.branch_chart_area = tk.Frame(self.branch_card, bg=COLOR_WHITE)
        self.branch_chart_area.pack(fill="both", expand=True, padx=4, pady=4)

        self.refresh_stats()

    def _create_stat_card(self, parent, title, value, color):
        card = tk.Frame(parent, bg=COLOR_WHITE, bd=1, relief="solid")
        tk.Label(card, text=title, bg=COLOR_WHITE, fg=COLOR_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=10, pady=(8, 2))
        value_label = tk.Label(card, text=value, bg=COLOR_WHITE, fg=color, font=("Segoe UI", 20, "bold"))
        value_label.pack(anchor="w", padx=10, pady=(0, 8))
        card.value_label = value_label
        return card

    def on_tab_changed(self, event):
        if self.notebook.index("current") == 1:
            self.refresh_stats()

    def _fetch_gender_stats(self):
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT
                CASE
                    WHEN LOWER(TRIM(COALESCE(gender, ''))) = 'male' THEN 'Male'
                    WHEN LOWER(TRIM(COALESCE(gender, ''))) = 'female' THEN 'Female'
                    ELSE 'Other'
                END AS gender_group,
                COUNT(*)
            FROM members
            GROUP BY gender_group
        """)

        result = {"Male": 0, "Female": 0, "Other": 0}
        for label, count in rows:
            result[label] = count
        return result

    def refresh_stats(self):
        for w in self.gender_chart_area.winfo_children():
            w.destroy()
        for w in self.branch_chart_area.winfo_children():
            w.destroy()

        db = DatabaseManager()
        total_row = db.fetch_one("SELECT COUNT(*) FROM members")
        total = total_row[0] if total_row else 0

        gender_stats = self._fetch_gender_stats()
        male = gender_stats["Male"]
        female = gender_stats["Female"]
        other = gender_stats["Other"]

        self.card_total.value_label.config(text=str(total))
        self.card_male.value_label.config(text=str(male))
        self.card_female.value_label.config(text=str(female))
        self.card_other.value_label.config(text=str(other))

        self.draw_gender_pie(self.gender_chart_area, gender_stats)
        self.draw_branch_bar(self.branch_chart_area)
        self.set_status("Statistics refreshed")

    def draw_gender_pie(self, parent, stats):
        male = stats["Male"]
        female = stats["Female"]
        other = stats["Other"]

        fig = Figure(figsize=(4.2, 2.9), dpi=100, facecolor=COLOR_WHITE)
        ax = fig.add_subplot(111)

        if male + female + other == 0:
            ax.text(0.5, 0.5, "No gender data", ha="center", va="center", fontsize=11)
            ax.axis("off")
        else:
            labels = []
            sizes = []
            colors = []

            if male > 0:
                labels.append("Male")
                sizes.append(male)
                colors.append("#2a9df4")

            if female > 0:
                labels.append("Female")
                sizes.append(female)
                colors.append(COLOR_RED)

            if other > 0:
                labels.append("Other")
                sizes.append(other)
                colors.append("#f39c12")

            wedges, texts, autotexts = ax.pie(
                sizes,
                colors=colors,
                autopct="%1.1f%%",
                startangle=90,
                wedgeprops={"linewidth": 1, "edgecolor": "white"},
                textprops={"fontsize": 9}
            )
            for at in autotexts:
                at.set_color("white")
                at.set_fontsize(8)
                at.set_weight("bold")

            # Add legend to the right
            ax.legend(wedges, labels, title="Gender", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=8)
            ax.set_aspect("equal")

        fig.subplots_adjust(left=0.05, right=0.75, top=0.95, bottom=0.05)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def draw_branch_bar(self, parent):
        db = DatabaseManager()
        data = db.fetch_all("""
            SELECT b.name, COUNT(m.id) AS total_members
            FROM branches b
            LEFT JOIN members m ON b.id = m.branch_id
            GROUP BY b.id, b.name
            ORDER BY total_members DESC, b.name ASC
            LIMIT 10
        """)

        fig = Figure(figsize=(4.6, 2.9), dpi=100, facecolor=COLOR_WHITE)
        ax = fig.add_subplot(111)

        if not data:
            ax.text(0.5, 0.5, "No branch data", ha="center", va="center", fontsize=11)
            ax.axis("off")
        else:
            branches = [self._shorten_label(r[0] or "Unknown", 16) for r in data]
            counts = [r[1] for r in data]

            branches = branches[::-1]
            counts = counts[::-1]

            bars = ax.barh(branches, counts, color=COLOR_BLUE)

            max_count = max(counts) if counts else 1
            ax.set_xlim(0, max_count * 1.18)
            ax.grid(axis="x", linestyle="--", alpha=0.25)
            ax.tick_params(axis="y", labelsize=8)
            ax.tick_params(axis="x", labelsize=8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            for bar in bars:
                width = bar.get_width()
                ax.text(
                    width + max_count * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    f"{int(width)}",
                    va="center",
                    ha="left",
                    fontsize=8
                )

        fig.subplots_adjust(left=0.20, right=0.97, top=0.95, bottom=0.12)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ===================== PIN =====================
    def set_member_pin(self):
        selected = self.tree.selection()
        if len(selected) != 1:
            messagebox.showwarning("Select One", "Please select exactly one member to set a PIN.")
            return

        values = self.tree.item(selected[0], "values")
        internal_id = values[9]          # hidden DB_ID at index 9
        member_name = values[2]          # Full Name at index 2
        
        db = DatabaseManager()
        existing = db.fetch_one("SELECT id FROM member_portal WHERE member_id = ?", (internal_id,))
        if existing:
            if not messagebox.askyesno("Overwrite PIN", f"A PIN already exists for {member_name}.\nDo you want to replace it?"):
                return

        pin = str(random.randint(1000, 9999))
        hashed_pin = hash_password(pin)

        success = db.execute_query(
            "INSERT OR REPLACE INTO member_portal (member_id, pin) VALUES (?, ?)",
            (internal_id, hashed_pin)
        )

        if success:
            messagebox.showinfo("PIN Generated", f"PIN for {member_name} is: {pin}\n\nPlease share this securely.")
            show_toast(self.root, f"PIN set for {member_name}")
        else:
            messagebox.showerror("Error", "Failed to set PIN.")
    
    def show_member_committees(self):
        selected = self.tree.selection()
        if len(selected) != 1:
            messagebox.showwarning("Select One", "Please select exactly one member.")
            return

        values = self.tree.item(selected[0], "values")
        member_display_id = values[1]      # Member ID at index 1
        member_name = values[2]             # Full name at index 2
        internal_id = values[9]              # hidden DB_ID at index 9
    
        # Import the committee window (we'll create it now)
        from modules.committee_member_window import CommitteeMemberWindow
        CommitteeMemberWindow(self.root, internal_id, member_display_id, member_name)


    def set_security_questions(self):
        """Open a window to set/update security questions for the selected member."""
        selected = self.tree.selection()
        if len(selected) != 1:
            messagebox.showwarning("Select One", "Please select exactly one member.")
            return

        values = self.tree.item(selected[0], "values")
        internal_id = values[9]          # hidden DB_ID at index 9
        member_name = values[2]           # Full Name at index 2

        db = DatabaseManager()
        # Check if member_portal record exists; if not, we'll create one
        portal = db.fetch_one("SELECT security_question1, security_answer1, security_question2, security_answer2 FROM member_portal WHERE member_id=?", (internal_id,))
        existing_q1 = portal[0] if portal else ""
        existing_q2 = portal[2] if portal else ""

        # Create a new top-level window
        win = tk.Toplevel(self.root)
        win.title(f"Security Questions – {member_name}")
        win.geometry("550x450")
        win.configure(bg=COLOR_BG)
        win.transient(self.root)
        win.grab_set()

        main = tk.Frame(win, bg=COLOR_BG, padx=20, pady=20)
        main.pack(fill="both", expand=True)

        tk.Label(main, text="Set Security Questions", font=("Segoe UI", 14, "bold"),
                bg=COLOR_BG, fg=COLOR_BLUE).pack(pady=(0,15))

        # Question 1
        tk.Label(main, text="Question 1:", bg=COLOR_BG, font=FONT_TEXT).pack(anchor="w")
        q1_entry = tk.Entry(main, font=FONT_TEXT, width=50)
        q1_entry.pack(fill="x", pady=(0,10))
        if existing_q1:
            q1_entry.insert(0, existing_q1)

        tk.Label(main, text="Answer 1:", bg=COLOR_BG, font=FONT_TEXT).pack(anchor="w")
        a1_entry = tk.Entry(main, font=FONT_TEXT, width=50, show="*")
        a1_entry.pack(fill="x", pady=(0,10))

        # Question 2
        tk.Label(main, text="Question 2:", bg=COLOR_BG, font=FONT_TEXT).pack(anchor="w")
        q2_entry = tk.Entry(main, font=FONT_TEXT, width=50)
        q2_entry.pack(fill="x", pady=(0,10))
        if existing_q2:
            q2_entry.insert(0, existing_q2)

        tk.Label(main, text="Answer 2:", bg=COLOR_BG, font=FONT_TEXT).pack(anchor="w")
        a2_entry = tk.Entry(main, font=FONT_TEXT, width=50, show="*")
        a2_entry.pack(fill="x", pady=(0,10))

        # Note about hashing
        tk.Label(main, text="Answers will be hashed before saving.", bg=COLOR_BG,
                fg=COLOR_MUTED, font=("Segoe UI", 9)).pack(pady=(10,0))

        # Buttons
        btn_frame = tk.Frame(main, bg=COLOR_BG)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="Cancel", bg="#9ca3af", fg="white",
                font=FONT_TEXT, width=10, command=win.destroy).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save", bg=COLOR_BLUE, fg="white",
                font=FONT_TEXT, width=10,
                command=lambda: self.save_security_questions(internal_id, q1_entry, a1_entry, q2_entry, a2_entry, win)).pack(side="left", padx=5)
    
    
    def save_security_questions(self, internal_id, q1_entry, a1_entry, q2_entry, a2_entry, win):
        """Save hashed security questions to the database."""
        q1 = q1_entry.get().strip()
        a1 = a1_entry.get().strip()
        q2 = q2_entry.get().strip()
        a2 = a2_entry.get().strip()

        if not q1 or not a1 or not q2 or not a2:
            messagebox.showerror("Error", "All fields are required.")
            return

        from database import hash_password
        hashed_a1 = hash_password(a1)
        hashed_a2 = hash_password(a2)

        db = DatabaseManager()
        # Check if portal record exists
        portal = db.fetch_one("SELECT id FROM member_portal WHERE member_id=?", (internal_id,))
        if portal:
            # Update
            db.execute_query("""
                UPDATE member_portal SET 
                    security_question1=?, security_answer1=?,
                    security_question2=?, security_answer2=?
                WHERE member_id=?
            """, (q1, hashed_a1, q2, hashed_a2, internal_id))
        else:
            # Insert new record (PIN remains NULL initially)
            db.execute_query("""
                INSERT INTO member_portal (member_id, security_question1, security_answer1, security_question2, security_answer2)
                VALUES (?, ?, ?, ?, ?)
            """, (internal_id, q1, hashed_a1, q2, hashed_a2))

        win.destroy()
        messagebox.showinfo("Success", f"Security questions saved for {internal_id}.")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Church Members Module")
    root.geometry("1240x700")
    root.minsize(1020, 620)
    app = MembersModule(root)
    root.mainloop()