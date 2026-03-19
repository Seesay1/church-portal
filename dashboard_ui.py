import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
from PIL import Image, ImageTk
from database import DatabaseManager 
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from tkcalendar import DateEntry

# Import your modules
from modules.members import MembersModule
from modules.attendance import AttendanceModule
from modules.events import EventsModule
from modules.financial_management import FinancialManagement
from modules.branch_management import BranchManagement
from modules.certificates import CertificatesModule
from modules.member_id_cards import MemberIDCards
from modules.prayer import PrayerModule
from modules.resources import ResourcesModule
from modules.sms_center import SMSCenter
from modules.reports import ReportsModule
from modules.settings import SettingsModule
from modules.users import UsersModule
from modules.analytics import AnalyticsModule
from modules.committees import CommitteesModule
from modules.blog import BlogModule
from modules.volunteers import VolunteersModule


FONT_TEXT = ("Helvetica", 10)
THEMES = {
    "light": {"bg": "#e8f1ff", "fg": "#000", "card_bg": "#ffffff", "card_fg": "#000", "accent": "#1f4fa3"},
    "dark":  {"bg": "#2d2d2d", "fg": "#fff", "card_bg": "#3d3d3d", "card_fg": "#fff", "accent": "#d62828"}
}

# ================== CONSTANTS ==================
PAD = 10
SMALL_PAD = 5

# ================== TOOLTIP CLASS ==================
class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
        self.dismissed_notifications = []

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert") or (0, 0, 0, 0)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Helvetica", 9))
        label.pack(ipadx=5, ipady=2)

    def hide_tip(self, event=None):
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None

# ================== DASHBOARD CLASS ==================
class DashboardUI:
    def __init__(self, root, username="Admin", role="Admin", user_id=None, branch_id=None):
        self.root = root
        self.root.title("PCG Mt. Zion - Dashboard")
        self.root.geometry("1400x800")
        self.after_id = None
        self.theme = "light"
        self.username = username
        self.role = role
        self.user_id = user_id
        self.branch_id = branch_id
        self.sidebar_expanded = True
        self.current_module_frame = None
        self.summary_labels = []
        self.auto_update_id = None
        self.dashboard_visible = True
        self.notif_window = None
        self.current_active_button = None
        self.apply_theme()

        # Mapping from display names to internal widget identifiers
        self.widget_map = {
            "Summary Cards": "summary",
            "Contribution Chart": "contrib_chart",
            "Attendance Trend": "attendance_trend",
            "Member Growth": "member_growth",
            "Upcoming Events List": "upcoming_events",
            "Recent Contributions": "recent_contributions"
        }

        # ---------------- Top Navigation ----------------
        self.top_bar = tk.Frame(self.root, bg=self.colors["accent"], height=60)
        self.top_bar.pack(side="top", fill="x")
        
        self.toggle_top_btn = tk.Button(self.top_bar, text="☰", bg=self.colors["accent"], fg="#fff",
                                        font=("Helvetica", 14, "bold"), bd=0,
                                        command=self.toggle_sidebar)
        self.toggle_top_btn.pack(side="left", padx=(PAD, SMALL_PAD))
        self._add_hover(self.toggle_top_btn, self.colors["accent"], "#2a9df4")
        ToolTip(self.toggle_top_btn, "Toggle Sidebar (Ctrl+B)")
        
        tk.Label(self.top_bar, text="PCG Mt. Zion Dashboard", fg="#fff", bg=self.colors["accent"],
                 font=("Helvetica", 16, "bold")).pack(side="left", padx=PAD)
        
        right_frame = tk.Frame(self.top_bar, bg=self.colors["accent"])
        right_frame.pack(side="right", padx=PAD)

        self.notif_btn = tk.Button(right_frame, text="🔔", bg=self.colors["accent"], fg="#fff",
                                   font=("Helvetica", 14), bd=0, command=self.toggle_notifications)
        self.notif_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(self.notif_btn, self.colors["accent"], "#2a9df4")
        ToolTip(self.notif_btn, "Notifications")

        self.theme_btn = tk.Button(right_frame, text="🌙" if self.theme=="light" else "☀️",
                                   bg=self.colors["accent"], fg="#fff",
                                   font=("Helvetica", 14), bd=0, command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(self.theme_btn, self.colors["accent"], "#2a9df4")
        ToolTip(self.theme_btn, "Toggle Dark/Light Mode")

        self.help_btn = tk.Button(right_frame, text="❓", bg=self.colors["accent"], fg="#fff",
                                  font=("Helvetica", 14), bd=0, command=self.show_help)
        self.help_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(self.help_btn, self.colors["accent"], "#2a9df4")
        ToolTip(self.help_btn, "Help (?)")

        self.profile_btn = tk.Button(right_frame, text="👤", bg=self.colors["accent"], fg="#fff",
                                      font=("Helvetica", 14), bd=0, command=self.open_profile)
        self.profile_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(self.profile_btn, self.colors["accent"], "#2a9df4")
        ToolTip(self.profile_btn, "User Profile")

        tk.Label(self.top_bar, text=f"Logged in as: {username} ({role})", fg="#fff", bg=self.colors["accent"],
                 font=FONT_TEXT).pack(side="right", padx=PAD)

        # ---------------- Quick Action Bar ----------------
        self.quick_bar = tk.Frame(self.root, bg=self.colors["bg"], height=50)
        self.quick_bar.pack(side="top", fill="x", padx=PAD, pady=SMALL_PAD)

        self.quick_add_btn = tk.Button(self.quick_bar, text="➕ Quick Add Member", bg=self.colors["accent"], fg="#fff",
                                        font=FONT_TEXT, command=self.quick_add_member)
        self.quick_add_btn.pack(side="left", padx=2)
        self._add_hover(self.quick_add_btn, self.colors["accent"], "#2a9df4")

        self.quick_att_btn = tk.Button(self.quick_bar, text="📋 Record Attendance", bg=self.colors["accent"], fg="#fff",
                                        font=FONT_TEXT, command=self.quick_attendance)
        self.quick_att_btn.pack(side="left", padx=2)
        self._add_hover(self.quick_att_btn, self.colors["accent"], "#2a9df4")

        self.quick_cont_btn = tk.Button(self.quick_bar, text="💰 Add Contribution", bg=self.colors["accent"], fg="#fff",
                                         font=FONT_TEXT, command=self.quick_contribution)
        self.quick_cont_btn.pack(side="left", padx=2)
        self._add_hover(self.quick_cont_btn, self.colors["accent"], "#2a9df4")

        self.quick_evt_btn = tk.Button(self.quick_bar, text="📅 Today's Events", bg=self.colors["accent"], fg="#fff",
                                        font=FONT_TEXT, command=self.quick_events)
        self.quick_evt_btn.pack(side="left", padx=2)
        self._add_hover(self.quick_evt_btn, self.colors["accent"], "#2a9df4")

        # ---------------- Sidebar ----------------
        # Increase sidebar width to accommodate scrollbar
        self.sidebar_width = 160
        self.sidebar = tk.Frame(self.root, bg=self.colors["sidebar"], width=self.sidebar_width)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Top scrollable area (will expand)
        top_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar"])
        top_frame.pack(side="top", fill="both", expand=True)

        self.canvas = tk.Canvas(top_frame, bg=self.colors["sidebar"], highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(top_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["sidebar"])

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner_frame_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        def configure_scrollregion(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.scrollable_frame.bind("<Configure>", configure_scrollregion)
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.inner_frame_window, width=e.width))

        # Bottom fixed frame for logout and collapse
        bottom_frame = tk.Frame(self.sidebar, bg=self.colors["sidebar"])
        bottom_frame.pack(side="bottom", fill="x")

        self.collapse_btn = tk.Button(bottom_frame, text="<<", bg="#d62828", fg="#fff",
                                      width=13, command=self.toggle_sidebar)
        self.collapse_btn.pack(pady=SMALL_PAD, padx=SMALL_PAD)
        self._add_hover(self.collapse_btn, "#d62828", "#f77b7b")
        ToolTip(self.collapse_btn, "Collapse/Expand Sidebar")

        self.logout_btn = tk.Button(bottom_frame, text="🚪 Logout", bg="#d62828", fg="#fff",
                                    font=FONT_TEXT, width=13, command=self.logout)
        self.logout_btn.pack(pady=SMALL_PAD, padx=SMALL_PAD)
        self._add_hover(self.logout_btn, "#d62828", "#f77b7b")
        ToolTip(self.logout_btn, "Logout from the system")

        # ---------------- Sidebar Buttons ----------------
        self.dashboard_btn = tk.Button(self.scrollable_frame, text="🏠 Dashboard", font=FONT_TEXT,
                                        bg="#1f4fa3", fg="#fff", width=13,
                                        command=self.show_dashboard)
        self.dashboard_btn.pack(pady=SMALL_PAD, padx=SMALL_PAD)
        self._add_hover(self.dashboard_btn, "#1f4fa3", "#2a9df4")
        ToolTip(self.dashboard_btn, "Return to Dashboard Home")

        ttk.Separator(self.scrollable_frame, orient="horizontal").pack(fill="x", pady=SMALL_PAD)

        self.all_modules = [
            ("Members", MembersModule, "Members"),
            ("Attendance", AttendanceModule, "Attendance"),
            ("Blog", BlogModule, "Blog"),
            ("Events", EventsModule, "Events"),
            ("Finance", FinancialManagement, "Finance"),
            ("Branches", BranchManagement, "Branches"),
            ("Certificates", CertificatesModule, "Certificates"),
            ("ID Cards", MemberIDCards, "ID Cards"),
            ("SMS Center", SMSCenter, "SMS Center"),
            ("Reports", ReportsModule, "Reports"),
            ("Resources", ResourcesModule, "Resources"),
            ("Prayer", PrayerModule, "Prayer"),
            ("Settings", SettingsModule, "Settings"),
            ("Users", UsersModule, "Users"),
            ("Committees", CommitteesModule, "Committees"),
            ("Analytics", AnalyticsModule, "Analytics"),
            ("Volunteers", VolunteersModule, "Volunteers")
        ]

        role_permissions = {
            "Admin": [name for name, _, perm in self.all_modules],
            "User": ["Members", "Attendance", "Events"]
        }

        allowed = role_permissions.get(role, [])
        self.modules = [(name, mod) for name, mod, perm in self.all_modules if perm in allowed]

        self.module_buttons = []
        for name, mod_class in self.modules:
            btn = tk.Button(self.scrollable_frame, text=name, font=FONT_TEXT,
                            bg="#1f4fa3", fg="#fff", width=13,  # changed from 14 to 13
                            command=lambda m=mod_class, n=name: self.load_module(m, n))
            btn.pack(pady=SMALL_PAD, padx=SMALL_PAD)
            self._add_hover(btn, "#1f4fa3", "#2a9df4")
            ToolTip(btn, f"Open {name}")
            self.module_buttons.append((btn, name))

        # Force scrollregion update after all buttons are packed
        self.scrollable_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        # ---------------- Main Content Area (with scroll) ----------------
        self.main_container = tk.Frame(self.root, bg=self.colors["bg"])
        self.main_container.pack(side="left", fill="both", expand=True, padx=PAD, pady=PAD)

        self.main_canvas = tk.Canvas(self.main_container, bg=self.colors["bg"], highlightthickness=0)
        self.main_scrollbar = ttk.Scrollbar(self.main_container, orient="vertical", command=self.main_canvas.yview)
        self.main_scrollable_frame = tk.Frame(self.main_canvas, bg=self.colors["bg"])
        self.main_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        self.main_canvas.create_window((0, 0), window=self.main_scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_scrollbar.pack(side="right", fill="y")

        self.main_content = self.main_scrollable_frame

        self.set_active_button(self.dashboard_btn)
        self.create_dashboard_view()
        self.bind_shortcuts()
        self.start_auto_refresh()
        self.update_notification_badge()

        self.root.bind_all("<MouseWheel>", self._global_mousewheel)
        self.root.bind_all("<Button-4>", self._global_mousewheel)
        self.root.bind_all("<Button-5>", self._global_mousewheel)
        
    # ---------- Helper: hover effect for buttons ----------
    def _add_hover(self, button, normal_bg, hover_bg):
        """Add hover enter/leave events to a button."""
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=normal_bg))

    # ---------- Toast notification ----------
    def show_toast(self, message, duration=2000):
        """Display a transient toast message."""
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.configure(bg="#333")
        x = self.root.winfo_rootx() + self.root.winfo_width()//2 - 150
        y = self.root.winfo_rooty() + 80
        toast.geometry(f"+{x}+{y}")
        tk.Label(toast, text=message, bg="#333", fg="white",
                 font=("Helvetica", 10), padx=20, pady=10).pack()
        toast.after(duration, toast.destroy)

    # ---------- Theme and layout ----------
    def apply_theme(self):
        self.colors = THEMES[self.theme].copy()
        self.colors["sidebar"] = "#0b3d91"

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme()
        self.theme_btn.config(text="🌙" if self.theme=="light" else "☀️")
        self.root.configure(bg=self.colors["bg"])
        self.top_bar.config(bg=self.colors["accent"])
        for child in self.top_bar.winfo_children():
            if isinstance(child, (tk.Label, tk.Button)):
                child.config(bg=self.colors["accent"], fg="#fff")
        self.quick_bar.config(bg=self.colors["bg"])
        self.main_container.config(bg=self.colors["bg"])
        self.main_canvas.config(bg=self.colors["bg"])
        self.main_scrollable_frame.config(bg=self.colors["bg"])
        if self.dashboard_visible:
            self.create_dashboard_view()
        self.show_toast(f"Theme switched to {self.theme.capitalize()}")

    def _resize_inner_frame(self, event):
        self.canvas.itemconfig(self.inner_frame_window, width=event.width)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def toggle_sidebar(self):
        if self.sidebar_expanded:
            self.sidebar.pack_forget()
            self.sidebar_expanded = False
            self.toggle_top_btn.config(text="▶")
        else:
            self.main_container.pack_forget()
            self.sidebar.pack(side="left", fill="y")
            self.main_container.pack(side="left", fill="both", expand=True, padx=PAD, pady=PAD)
            self.sidebar_expanded = True
            self.toggle_top_btn.config(text="☰")
            self.sidebar.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def set_active_button(self, active_btn):
        for btn, _ in self.module_buttons:
            btn.config(bg="#1f4fa3")
        self.dashboard_btn.config(bg="#1f4fa3")
        if active_btn:
            active_btn.config(bg="#2a9df4")
        self.current_active_button = active_btn

    # ---------- Dashboard View ----------
    def create_dashboard_view(self):
        self.stop_auto_refresh()
        self.dashboard_visible = True
        self.set_active_button(self.dashboard_btn)

        # Clear main content
        for widget in self.main_content.winfo_children():
            widget.destroy()
        self.summary_labels = []

        # --- ADVANCED THEME COLORS ---
        bg_color = "#F0F4F8"        # Light Blue-Gray (Modern SaaS background)
        card_bg = "#FFFFFF"         # Pure White
        primary_color = "#1f4fa3"   # Your Brand Blue
        text_main = "#1F2937"       # Dark Gray (not pure black)
        text_sub = "#6B7280"        # Muted Gray
        border_color = "#E2E8F0"    # Subtle Border

        # --- MAIN CONTAINER ---
        # This provides the light background canvas
        main_container = tk.Frame(self.main_content, bg=bg_color)
        main_container.pack(fill="both", expand=True, padx=0, pady=0)

        # --- DASHBOARD HEADER ---
        # Adds a professional title area
        header_frame = tk.Frame(main_container, bg=bg_color)
        header_frame.pack(fill="x", padx=30, pady=(25, 15))
        
        tk.Label(header_frame, text="Dashboard Overview", bg=bg_color, fg=text_main, 
                 font=("Segoe UI", 24, "bold")).pack(side="left")
        tk.Label(header_frame, text="Real-time analytics and insights", bg=bg_color, fg=text_sub, 
                 font=("Segoe UI", 11)).pack(side="left", padx=(15, 0))

        try:
            # --- FLOATING FILTER TOOLBAR CARD ---
            # A white card floating on the blue-gray background
            filter_card = tk.Frame(main_container, bg=card_bg, highlightbackground=border_color, 
                                   highlightthickness=1, bd=0)
            filter_card.pack(fill="x", padx=30, pady=(0, 20))
            
            # Inner padding for the filter card
            filter_inner = tk.Frame(filter_card, bg=card_bg)
            filter_inner.pack(fill="x", padx=20, pady=15)

            # Helper function for clean labels
            def lbl(text):
                return tk.Label(filter_inner, text=text, bg=card_bg, fg=text_sub, 
                                font=("Segoe UI", 10, "bold"))

            # --- FILTERS ---
            # Branch
            lbl("Branch").pack(side="left", padx=(0, 8))
            self.branch_filter = ttk.Combobox(filter_inner, values=["All"] + self.get_branches(),
                                               state="readonly", width=16, font=("Segoe UI", 10))
            self.branch_filter.pack(side="left", padx=5)
            self.branch_filter.set("All")
            self.branch_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_dashboard())

            # Group
            lbl("Group").pack(side="left", padx=(20, 8))
            self.group_filter = ttk.Combobox(filter_inner, values=["All"] + self.get_groups(),
                                              state="readonly", width=16, font=("Segoe UI", 10))
            self.group_filter.pack(side="left", padx=5)
            self.group_filter.set("All")
            self.group_filter.bind("<<ComboboxSelected>>", lambda e: self.refresh_dashboard())

            # Date Range
            lbl("Period").pack(side="left", padx=(20, 8))
            
            date_container = tk.Frame(filter_inner, bg=card_bg)
            date_container.pack(side="left", padx=5)

            self.date_from = DateEntry(date_container, width=12, background='white', foreground='#333',
                                       borderwidth=0, date_pattern='yyyy-mm-dd', font=("Segoe UI", 10))
            self.date_from.pack(side="left")
            self.date_from.set_date(datetime.now() - timedelta(days=30))
            
            tk.Label(date_container, text="to", bg=card_bg, fg=text_sub).pack(side="left", padx=5)
            
            self.date_to = DateEntry(date_container, width=12, background='white', foreground='#333',
                                     borderwidth=0, date_pattern='yyyy-mm-dd', font=("Segoe UI", 10))
            self.date_to.pack(side="left")
            self.date_to.set_date(datetime.now())

            # Apply Button (Pill shaped style)
            apply_btn = tk.Button(filter_inner, text="Apply Filters", bg=primary_color, fg="white",
                                  font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=8,
                                  cursor="hand2", command=self.refresh_dashboard, relief="flat")
            apply_btn.pack(side="right", padx=(15, 0))
            apply_btn.bind("<Enter>", lambda e: apply_btn.config(bg="#163c82"))
            apply_btn.bind("<Leave>", lambda e: apply_btn.config(bg=primary_color))

            # --- WIDGETS GRID ---
            widgets_scroll_frame = tk.Frame(main_container, bg=bg_color)
            widgets_scroll_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

            visible_widgets = self.load_widget_settings()
            
            # To make it look truly "Advanced", we will use a 2-column grid layout for the widgets
            # rather than stacking them vertically, if possible.
            # For now, let's stick to vertical stacking but style the cards beautifully.
            
            row_count = 0
            for display_name in visible_widgets:
                widget_name = self.widget_map.get(display_name)
                if not widget_name:
                    continue
                
                # --- INDIVIDUAL WIDGET CARD ---
                # A clean white card with a subtle shadow border
                card = tk.Frame(widgets_scroll_frame, bg=card_bg, highlightbackground="#CBD5E0", 
                                highlightthickness=1, bd=0)
                card.pack(fill="both", expand=True, pady=(0, 20))
                
                # --- ACCENT STRIP (Top of card) ---
                # Give each card a color identity
                accent_color = "#3B82F6" # Default Blue
                if widget_name == "summary": accent_color = "#10B981" # Green
                elif widget_name == "contrib_chart": accent_color = "#8B5CF6" # Purple
                elif widget_name == "attendance_trend": accent_color = "#F59E0B" # Amber
                
                tk.Frame(card, bg=accent_color, height=4).pack(fill="x")

                # Card Content Container
                inner_card = tk.Frame(card, bg=card_bg, padx=20, pady=20)
                inner_card.pack(fill="both", expand=True)

                # Widget Title (Visual Eye-Candy)
                title_text = display_name.replace("_", " ").title()
                tk.Label(inner_card, text=title_text, bg=card_bg, fg=text_main, 
                         font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x", pady=(0, 10))
                
                # Content Frame
                content_frame = tk.Frame(inner_card, bg=card_bg)
                content_frame.pack(fill="both", expand=True)

                try:
                    if widget_name == "summary":
                        self.summary_frame = content_frame
                        self.create_summary_panels()
                    elif widget_name == "contrib_chart":
                        self.draw_contributions(content_frame)
                    elif widget_name == "attendance_trend":
                        self.draw_attendance_trend(content_frame)
                    elif widget_name == "member_growth":
                        self.draw_member_growth(content_frame)
                    elif widget_name == "upcoming_events":
                        self.draw_upcoming_events(content_frame)
                    elif widget_name == "recent_contributions":
                        self.draw_recent_contributions(content_frame)
                except Exception as e:
                    print(f"Widget error: {e}")
                    import traceback
                    traceback.print_exc()

            # --- EXPORT FOOTER ---
            # A subtle footer action
            footer_frame = tk.Frame(main_container, bg=bg_color)
            footer_frame.pack(fill="x", padx=30, pady=(0, 20))
            
            export_btn = tk.Button(footer_frame, text="📥 Export Report", bg="white", fg=text_main,
                                   font=("Segoe UI", 10), bd=1, relief="solid", highlightbackground=border_color,
                                   padx=20, pady=8, cursor="hand2", command=self.export_data)
            export_btn.pack(side="right")
            
            def on_enter_export(e): export_btn.config(bg="#F8FAFC", fg=primary_color)
            def on_leave_export(e): export_btn.config(bg="white", fg=text_main)
            export_btn.bind("<Enter>", on_enter_export)
            export_btn.bind("<Leave>", on_leave_export)

        except Exception as e:
            print(f"Fatal error creating dashboard view: {e}")
            import traceback
            traceback.print_exc()
            tk.Label(main_container, text="Error loading dashboard.", bg=bg_color, fg="red").pack(pady=50)

        self.start_auto_refresh()
        self.update_notification_badge()

    # ---------- Data methods ----------
    def get_branches(self):
        db = DatabaseManager()
        rows = db.fetch_all("SELECT name FROM branches ORDER BY name")
        return [r[0] for r in rows]

    def get_groups(self):
        db = DatabaseManager()
        rows = db.fetch_all("SELECT name FROM groups ORDER BY name")
        return [r[0] for r in rows]

    def create_summary_panels(self):
        try:
            panel_texts = ["Total Members", "Today's Attendance", "Total Contributions", "Upcoming Events"]
            panel_icons = ["👥", "📋", "💰", "📅"]
            panel_colors = ["#1f4fa3", "#2a9df4", "#f44336", "#ff9800"]
            self.summary_labels = []
            for text, icon, color in zip(panel_texts, panel_icons, panel_colors):
                card = tk.Frame(self.summary_frame, bg=self.colors["card_bg"], bd=1, relief="solid")
                card.pack(side="left", padx=PAD, pady=SMALL_PAD, ipadx=PAD, ipady=SMALL_PAD)

                # Hover effect for the card
                def on_card_enter(e, c=card):
                    c.config(bg="#e0e0e0")
                def on_card_leave(e, c=card, normal=self.colors["card_bg"]):
                    c.config(bg=normal)
                card.bind("<Enter>", on_card_enter)
                card.bind("<Leave>", on_card_leave)

                tk.Label(card, text=icon, font=("Helvetica", 28), bg=card["bg"],
                         fg=self.colors["card_fg"]).pack(side="left", padx=SMALL_PAD)
                text_frame = tk.Frame(card, bg=card["bg"])
                text_frame.pack(side="left", fill="y")
                tk.Label(text_frame, text=text, fg="#555", bg=card["bg"],
                         font=("Helvetica", 10)).pack(anchor="w")
                lbl_value = tk.Label(text_frame, text="0", fg=color, bg=card["bg"],
                                     font=("Helvetica", 18, "bold"))
                lbl_value.pack(anchor="w")
                self.summary_labels.append(lbl_value)
            self.update_summary()
        except Exception as e:
            print(f"Error in create_summary_panels: {e}")
            import traceback
            traceback.print_exc()

    def refresh_dashboard(self):
        if not self.dashboard_visible:
            return
        self.create_dashboard_view()
        self.show_toast("Dashboard refreshed")

    def update_summary(self):
        if not self.dashboard_visible or not hasattr(self, 'summary_labels') or not self.summary_labels:
            return
        for lbl in self.summary_labels:
            if not lbl.winfo_exists():
                return

        db = DatabaseManager()
        branch = self.branch_filter.get() if hasattr(self, 'branch_filter') else "All"
        group = self.group_filter.get() if hasattr(self, 'group_filter') else "All"
        date_from = self.date_from.get_date().strftime("%Y-%m-%d") if hasattr(self, 'date_from') else None
        date_to = self.date_to.get_date().strftime("%Y-%m-%d") if hasattr(self, 'date_to') else None

        try:
            # Total Members
            query = "SELECT COUNT(*) FROM members m"
            params = []
            if branch != "All":
                query += " WHERE m.branch_id = (SELECT id FROM branches WHERE name=?)"
                params.append(branch)
            if group != "All":
                if "WHERE" in query:
                    query += " AND m.group_id = (SELECT id FROM groups WHERE name=?)"
                else:
                    query += " WHERE m.group_id = (SELECT id FROM groups WHERE name=?)"
                params.append(group)
            res = db.fetch_one(query, params)
            self.summary_labels[0].config(text=str(res[0] if res else 0))

            # Today's Attendance
            query = "SELECT COUNT(*) FROM attendance WHERE date=date('now')"
            params = []
            if branch != "All":
                query += " AND branch_id = (SELECT id FROM branches WHERE name=?)"
                params.append(branch)
            if group != "All":
                query += " AND group_id = (SELECT id FROM groups WHERE name=?)"
                params.append(group)
            res = db.fetch_one(query, params)
            self.summary_labels[1].config(text=str(res[0] if res else 0))

            # Total Contributions
            query = "SELECT SUM(amount) FROM financial_records WHERE type IN ('Tithe', 'Offering', 'Contribution')"
            params = []
            if date_from and date_to:
                query += " AND date BETWEEN ? AND ?"
                params.append(date_from)
                params.append(date_to)
            if branch != "All":
                query += " AND branch_id = (SELECT id FROM branches WHERE name=?)"
                params.append(branch)
            if group != "All":
                query += " AND group_id = (SELECT id FROM groups WHERE name=?)"
                params.append(group)
            res = db.fetch_one(query, params)
            total = res[0] if res and res[0] else 0
            self.summary_labels[2].config(text=f"{total:,.0f}")

            # Upcoming Events
            res = db.fetch_one("SELECT COUNT(*) FROM events WHERE date>=date('now')")
            self.summary_labels[3].config(text=str(res[0] if res else 0))
        except Exception as e:
            print("Summary update error:", e)

    def draw_contributions(self, parent):
        try:
            for widget in parent.winfo_children():
                widget.destroy()
            db = DatabaseManager()
            date_from = self.date_from.get_date().strftime("%Y-%m-%d") if hasattr(self, 'date_from') else None
            date_to = self.date_to.get_date().strftime("%Y-%m-%d") if hasattr(self, 'date_to') else None
            query = """
                SELECT strftime('%m', date), SUM(amount) 
                FROM financial_records 
                WHERE type IN ('Tithe', 'Offering', 'Contribution')
            """
            params = []
            if date_from and date_to:
                query += " AND date BETWEEN ? AND ?"
                params.extend([date_from, date_to])
            query += " GROUP BY strftime('%m', date)"
            data = db.fetch_all(query, params)

            fig = Figure(figsize=(6, 3), dpi=100, facecolor=self.colors["card_bg"])
            ax = fig.add_subplot(111)
            if data:
                months = [row[0] for row in data]
                amounts = [row[1] for row in data]
                ax.bar(months, amounts, color="#2a9df4")
                ax.set_title("Monthly Contributions", fontsize=12)
                ax.set_xlabel("Month", fontsize=10)
                ax.set_ylabel("Amount", fontsize=10)
            else:
                ax.text(0.5, 0.5, "No data for selected range", ha='center', va='center')
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            print(f"Error drawing contributions: {e}")
            import traceback
            traceback.print_exc()

    def draw_attendance_trend(self, parent):
        try:
            for widget in parent.winfo_children():
                widget.destroy()
            db = DatabaseManager()
            end = datetime.now().date()
            start = end - timedelta(days=30)
            dates = []
            counts = []
            for i in range(30):
                day = start + timedelta(days=i)
                date_str = day.strftime("%Y-%m-%d")
                dates.append(day.strftime("%m/%d"))
                cnt = db.fetch_one("SELECT COUNT(*) FROM attendance WHERE date=? AND present=1", (date_str,))
                counts.append(cnt[0] if cnt else 0)

            fig = Figure(figsize=(6, 3), dpi=100, facecolor=self.colors["card_bg"])
            ax = fig.add_subplot(111)
            ax.plot(dates, counts, marker='o', color="#2a9df4")
            ax.set_title("Attendance Trend (Last 30 Days)", fontsize=12)
            ax.set_xlabel("Date", fontsize=10)
            ax.set_ylabel("Present Count", fontsize=10)
            ax.tick_params(axis='x', rotation=45)
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            print(f"Error drawing attendance trend: {e}")
            import traceback
            traceback.print_exc()

    def draw_member_growth(self, parent):
        try:
            for widget in parent.winfo_children():
                widget.destroy()
            db = DatabaseManager()
            data = db.fetch_all("""
                SELECT strftime('%Y-%m', date_joined), COUNT(*) 
                FROM members WHERE date_joined IS NOT NULL 
                GROUP BY strftime('%Y-%m', date_joined) 
                ORDER BY 1
            """)
            fig = Figure(figsize=(6, 3), dpi=100, facecolor=self.colors["card_bg"])
            ax = fig.add_subplot(111)
            if data:
                months = [row[0] for row in data]
                counts = [row[1] for row in data]
                ax.plot(months, counts, marker='s', color="#f44336")
                ax.set_title("Member Growth by Month", fontsize=12)
                ax.set_xlabel("Month", fontsize=10)
                ax.set_ylabel("New Members", fontsize=10)
                ax.tick_params(axis='x', rotation=45)
            else:
                ax.text(0.5, 0.5, "No member growth data", ha='center', va='center')
            fig.tight_layout()
            canvas = FigureCanvasTkAgg(fig, master=parent)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            print(f"Error drawing member growth: {e}")
            import traceback
            traceback.print_exc()

    def draw_upcoming_events(self, parent):
        for widget in parent.winfo_children():
            widget.destroy()
        db = DatabaseManager()
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        events = db.fetch_all(
            "SELECT name, date FROM events WHERE date BETWEEN ? AND ? ORDER BY date",
            (today.strftime("%Y-%m-%d"), next_week.strftime("%Y-%m-%d"))
        )
        print(f"draw_upcoming_events: raw dates = {[r[1] for r in events]}")
        if not events:
            tk.Label(parent, text="No upcoming events in the next 7 days",
                     bg=self.colors["bg"], fg=self.colors["fg"]).pack(pady=PAD)
        else:
            tk.Label(parent, text="Upcoming Events (next 7 days)", font=("Helvetica", 12, "bold"),
                     bg=self.colors["bg"], fg=self.colors["accent"]).pack(pady=SMALL_PAD)
            for name, date_str in events:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                days_left = (event_date - today).days
                tk.Label(parent, text=f"📅 {date_str} - {name} (in {days_left} day{'s' if days_left!=1 else ''})",
                         bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", padx=PAD)
   
    
    def draw_recent_contributions(self, parent):
        for widget in parent.winfo_children():
            widget.destroy()
        db = DatabaseManager()
        today = datetime.now().date()
        start = today - timedelta(days=7)
        contributions = db.fetch_all(
            """
            SELECT f.date, m.full_name, f.amount 
            FROM financial_records f
            LEFT JOIN members m ON f.member_id = m.id
            WHERE f.type IN ('Tithe', 'Offering', 'Contribution') AND f.date >= ?
            ORDER BY f.date DESC
            LIMIT 10
            """,
            (start.strftime("%Y-%m-%d"),)
        )
        if not contributions:
            tk.Label(parent, text="No recent contributions in the last 7 days",
                     bg=self.colors["bg"], fg=self.colors["fg"]).pack(pady=PAD)
        else:
            tk.Label(parent, text="Recent Contributions (last 7 days)", font=("Helvetica", 12, "bold"),
                     bg=self.colors["bg"], fg=self.colors["accent"]).pack(pady=SMALL_PAD)
            for date, name, amount in contributions:
                name_disp = name if name else "Unknown"
                tk.Label(parent, text=f"💰 {date} - {name_disp}: ₵{amount:,.2f}",
                         bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", padx=PAD)

    def export_data(self):
        branch = self.branch_filter.get() if hasattr(self, 'branch_filter') else "All"
        group = self.group_filter.get() if hasattr(self, 'group_filter') else "All"
        date_from = self.date_from.get_date().strftime("%Y%m%d") if hasattr(self, 'date_from') else "start"
        date_to = self.date_to.get_date().strftime("%Y%m%d") if hasattr(self, 'date_to') else "end"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"dashboard_export_{branch}_{group}_{date_from}_to_{date_to}_{timestamp}.csv"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_filename,
            title="Export Dashboard Data"
        )
        if not filepath:
            return

        data = [
            ["Metric", "Value", "Filters Applied"],
            ["Total Members", self.summary_labels[0].cget("text"), f"Branch: {branch}, Group: {group}"],
            ["Today's Attendance", self.summary_labels[1].cget("text"), f"Branch: {branch}, Group: {group}"],
            ["Total Contributions", self.summary_labels[2].cget("text"), f"Date Range: {date_from} to {date_to}"],
            ["Upcoming Events", self.summary_labels[3].cget("text"), ""],
            [],
            ["Additional Info", ""],
            ["Export Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["User", self.username],
            ["Role", self.role]
        ]

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerows(data)
            self.show_toast("Export successful")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

    def quick_add_member(self):
        self.load_module(MembersModule, "Members")

    def quick_attendance(self):
        self.load_module(AttendanceModule, "Attendance")

    def quick_contribution(self):
        self.load_module(FinancialManagement, "Finance")

    def quick_events(self):
        self.load_module(EventsModule, "Events")
    
    def toggle_notifications(self):
        """Displays the notification overlay with forced visibility fixes."""
        # 1. If window exists, close it and exit
        if hasattr(self, 'notif_window') and self.notif_window and self.notif_window.winfo_exists():
            self.notif_window.destroy()
            self.notif_window = None
            return

        # 2. Get data and timestamp
        notifs = self.get_notifications()
        last_sync = datetime.now().strftime("%I:%M %p")
        
        # 3. Calculate Position (Ensure the button is rendered before getting coordinates)
        try:
            x = self.notif_btn.winfo_rootx() - 280
            y = self.notif_btn.winfo_rooty() + 45
        except:
            x, y = 500, 100 # Fallback coordinates

        # 4. Create Window
        self.notif_window = tk.Toplevel(self.root)
        
        # FIX: Order matters for overrideredirect and transient
        self.notif_window.withdraw() # Hide while building
        self.notif_window.transient(self.root) 
        self.notif_window.overrideredirect(True)
        
        self.notif_window.geometry(f"320x480+{x}+{y}")
        self.notif_window.configure(bg="white", highlightbackground="#ddd", highlightthickness=1)
        
        # --- UI CONSTRUCTION ---
        # Header
        header = tk.Frame(self.notif_window, bg="#1f4fa3")
        header.pack(fill="x")
        tk.Label(header, text="Notifications", bg="#1f4fa3", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=10, pady=8)
        
        tk.Button(header, text="✕", bg="#1f4fa3", fg="white", bd=0, cursor="hand2",
                  command=self.notif_window.destroy).pack(side="right", padx=10)

        # Scrollable Area
        container = tk.Frame(self.notif_window, bg="white")
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, bg="white", highlightthickness=0)
        scroll_bar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg="white")
        
        canvas.configure(yscrollcommand=scroll_bar.set)
        scroll_bar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=300)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        # Notification Cards
        if not notifs:
            tk.Label(scroll_frame, text="✨ No new notifications", bg="white", fg="gray", pady=100).pack(fill="x")
        else:
            for n in notifs:
                card = tk.Frame(scroll_frame, bg="#f9f9f9", padx=10, pady=8)
                card.pack(fill="x", padx=5, pady=3)
                
                if "Today" in n.get("message", ""):
                    card.config(highlightbackground="#ff9800", highlightthickness=1)

                tk.Label(card, text=n["icon"], bg="#f9f9f9", font=("Arial", 12)).pack(side="left")
                
                info = tk.Frame(card, bg="#f9f9f9")
                info.pack(side="left", fill="x", padx=5)
                tk.Label(info, text=n["title"], bg="#f9f9f9", font=("Arial", 9, "bold"), anchor="w").pack(fill="x")
                tk.Label(info, text=n["message"], bg="#f9f9f9", font=("Arial", 8), fg="#666", anchor="w").pack(fill="x")

                if n["type"] == "event":
                    tk.Button(card, text="→", bg="#f9f9f9", bd=0, fg="#1f4fa3", cursor="hand2",
                              command=lambda: self.show_module("Events")).pack(side="right")

        # Footer
        footer = tk.Frame(self.notif_window, bg="#f0f0f0")
        footer.pack(fill="x", side="bottom")
        
        # In the footer section of toggle_notifications:
        # Mark as Read Link
        btn_read = tk.Button(footer, text="Mark all as read", bg="#f0f0f0", bd=0, 
                            fg="#1f4fa3", font=("Arial", 8, "bold"), cursor="hand2",
                            command=self.mark_notifications_read)
        btn_read.pack(side="left", padx=10, pady=10)
        btn_read.bind("<Enter>", lambda e: btn_read.config(font=("Arial", 8, "bold", "underline")))
        btn_read.bind("<Leave>", lambda e: btn_read.config(font=("Arial", 8, "bold")))

        # Reset Link
        btn_reset = tk.Button(footer, text="Reset", bg="#f0f0f0", bd=0, 
                             fg="gray", font=("Arial", 8), cursor="hand2",
                             command=self.reset_dismissed_notifications)
        btn_reset.pack(side="right", padx=10)
        btn_reset.bind("<Enter>", lambda e: btn_reset.config(fg="#333", font=("Arial", 8, "underline")))
        btn_reset.bind("<Leave>", lambda e: btn_reset.config(fg="gray", font=("Arial", 8)))

        # NEW: History button
        btn_history = tk.Button(footer, text="View History", bg="#f0f0f0", bd=0, 
                                fg="#666", font=("Arial", 8), cursor="hand2",
                                command=self.open_notification_history)
        btn_history.pack(side="right", padx=10)

        # Hover effect
        btn_history.bind("<Enter>", lambda e: btn_history.config(fg="#1f4fa3", font=("Arial", 8, "underline")))
        btn_history.bind("<Leave>", lambda e: btn_history.config(fg="#666", font=("Arial", 8)))
        
        # 5. FINAL VISIBILITY PUSH
        self.notif_window.deiconify() # Show the window
        self.notif_window.lift()      # Bring to top
        self.notif_window.focus_force() # Grab focus

        # 6. Bind the sticky-fix to the ROOT window
        self.root.bind("<Unmap>", lambda e: self.hide_notif_on_minimize(), add="+")
        self.root.bind("<Map>", lambda e: self.show_notif_on_restore(), add="+")

    def hide_notif_on_minimize(self):
        if hasattr(self, 'notif_window') and self.notif_window:
            self.notif_window.withdraw()

    def show_notif_on_restore(self):
        if hasattr(self, 'notif_window') and self.notif_window:
            self.notif_window.deiconify()
    
    def get_notifications(self):
        try:
            db = DatabaseManager()
            notifications = []
            today = datetime.now().date()
            next_month = today + timedelta(days=30)

            # FETCH EVENTS
            events = db.fetch_all(
                "SELECT id, name, date FROM events WHERE date BETWEEN ? AND ? ORDER BY date",
                (today.strftime("%Y-%m-%d"), next_month.strftime("%Y-%m-%d"))
            )
            print(f"get_notifications: raw events = {events}")   # <-- ADD THIS

            for evt_id, name, date_str in events:
                event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                days_left = (event_date - today).days
                time_msg = "Today" if days_left == 0 else "Tomorrow" if days_left == 1 else f"In {days_left} days"

                notifications.append({
                    "id": f"evt_{evt_id}_{date_str}",
                    "type": "event",
                    "icon": "📅",
                    "title": f"Upcoming: {name}",
                    "message": f"{time_msg} ({date_str})",
                    "timestamp": datetime.now().strftime("%H:%M")
                })

            # ... (attendance check) ...

            # FILTER DISMISSED
            if hasattr(self, 'dismissed_notifications'):
                print(f"get_notifications: dismissed list = {self.dismissed_notifications}")   # <-- ADD THIS
                before = len(notifications)
                notifications = [n for n in notifications if n['id'] not in self.dismissed_notifications]
                print(f"get_notifications: after filter, removed {before - len(notifications)} notifications")
            else:
                print("get_notifications: dismissed_notifications not set")

            return notifications
        except Exception as e:
            print(f"Error in get_notifications: {e}")
            return []
    
    def update_notification_badge(self):
        """Updates the bell icon with the current notification count and schedules the next check."""
        try:
            # Cancel any previously scheduled update to avoid duplicates
            if hasattr(self, 'after_id') and self.after_id:
                try:
                    self.root.after_cancel(self.after_id)
                except Exception:
                    pass  # ignore if already cancelled

            # 1. Fetch the filtered list (handles 30-day window and dismissed items)
            notifications = self.get_notifications()
            count = len(notifications)

            # Debugging check in the terminal
            print(f"update_notification_badge: filtered count = {count}")

            # 2. Update the button UI
            if hasattr(self, 'notif_btn') and self.notif_btn.winfo_exists():
                if count > 0:
                    self.notif_btn.config(
                        text=f"🔔({count})",
                        fg="#ff4444",
                        font=("Helvetica", 10, "bold")
                    )
                else:
                    self.notif_btn.config(
                        text="🔔",
                        fg="white",
                        font=("Helvetica", 10)
                    )
        except Exception as e:
            print(f"Error updating badge UI: {e}")

        # 3. Schedule the next update (only if the root window still exists)
        try:
            self.after_id = self.root.after(60000, self.update_notification_badge)
        except tk.TclError:
            # Root window is destroyed – ignore
            pass
                
    def force_notification_update(self):
        """Called by other modules when data affecting notifications changes."""
        self.update_notification_badge()
    
    def reset_dismissed_notifications(self):
        self.dismissed_notifications = []
        if self.notif_window and self.notif_window.winfo_exists():
            self.notif_window.destroy()
        self.notif_window = None
        self.update_notification_badge()
        self.toggle_notifications()   # re-open the notification window

    def mark_notifications_read(self):
        current_notifs = self.get_notifications()
        if not hasattr(self, 'dismissed_notifications'):
            self.dismissed_notifications = []

        db = DatabaseManager()
        for n in current_notifs:
            if n['id'] not in self.dismissed_notifications:
                self.dismissed_notifications.append(n['id'])
                # Insert into history, allowing user_id to be None if not available
                db.execute_query("""
                    INSERT INTO notification_history (user_id, type, title, message, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.user_id if self.user_id else None,  # use None if no user_id
                    n['type'],
                    n['title'],
                    n['message'],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

        if self.notif_window and self.notif_window.winfo_exists():
            self.notif_window.destroy()
        self.notif_window = None
        self.update_notification_badge()

    def open_notification_history(self):
        """Opens the Notification History view in the main content area."""
        print("DEBUG: open_notification_history called")

        # Close notification dropdown if open
        if self.notif_window and self.notif_window.winfo_exists():
            self.notif_window.destroy()
            self.notif_window = None
            print("DEBUG: notification window destroyed")

        self.stop_auto_refresh()
        self.dashboard_visible = False
        print("DEBUG: auto-refresh stopped")

        # Clear main content
        for widget in self.main_content.winfo_children():
            widget.destroy()
        print("DEBUG: main_content cleared")

        # Create container frame
        history_frame = tk.Frame(self.main_content, bg=self.colors["bg"])
        history_frame.pack(fill="both", expand=True)
        print("DEBUG: history_frame created and packed")

        def on_map(event):
            print("DEBUG: history_frame mapped, scheduling UI creation")
            # Delay long enough for all geometry to settle
            self.root.after(100, lambda: self._create_history_ui(history_frame))
            history_frame.unbind("<Map>")   # ensure it runs only once

        history_frame.bind("<Map>", on_map)

    def _create_history_ui(self, history_frame):
        """Actually instantiate NotificationHistoryUI after delay."""
        print("DEBUG: _create_history_ui called")
        NotificationHistoryUI(history_frame, user_id=self.user_id, controller=self)
        self.set_active_button(None)

    def show_help(self):
        help_text = """Keyboard Shortcuts:
Ctrl+M – Members
Ctrl+A – Attendance
Ctrl+E – Events
Ctrl+F – Finance
Ctrl+B – Toggle Sidebar
Ctrl+S – Settings
Ctrl+R – Reports
Ctrl+D – Dashboard
? – This help"""
        messagebox.showinfo("Help", help_text)

    def show_dashboard(self):
        self.stop_auto_refresh()
        self.create_dashboard_view()
        self.update_notification_badge()
        self.start_auto_refresh()


    def load_module(self, module_class, module_name, **kwargs):
        """Flexible loader that handles UI switching and keyboard focus management."""
        self.stop_auto_refresh()
        self.dashboard_visible = False
        
        # 1. Clear the current dashboard content
        for widget in self.main_content.winfo_children():
            widget.destroy()
            
        # 2. Create the new container frame
        self.current_module_frame = tk.Frame(self.main_content, bg=self.colors["bg"])
        self.current_module_frame.pack(fill="both", expand=True)
        
        # 3. Initialize the module class
        # Passing **kwargs allows 'controller=self' to be passed safely
        self.active_module = module_class(
            self.current_module_frame, 
            user_id=self.user_id, 
            branch_id=self.branch_id, 
            **kwargs
        ) 
        self._add_wheel_support(self.current_module_frame)
        
        # 4. FOCUS FIX: Ensure the new frame is ready to receive keyboard events
        self.current_module_frame.focus_set()
        
        # 5. Update sidebar button states
        if hasattr(self, 'module_buttons'):
            for btn, name in self.module_buttons:
                if name == module_name:
                    self.set_active_button(btn)
                    break

    def show_module(self, module_name):
        """Switches the dashboard view to the actual module."""
        if self.notif_window and self.notif_window.winfo_exists():
            self.notif_window.destroy()
            self.notif_window = None

        print(f"Executing navigation to: {module_name}")

        # Special case: Dashboard
        if module_name == "Dashboard":
            self.show_dashboard()
            return

        # For other modules, try to load them
        for name, mod_class in self.modules:
            if name == module_name:
                self.load_module(mod_class, module_name)
                return
        print(f"No module class found for {module_name}")
    
    
    def logout(self):
        self.stop_auto_refresh()
        if hasattr(self, 'after_id') and self.after_id:
            try:
                self.root.after_cancel(self.after_id)
            except:
                pass
        if messagebox.askyesno("Logout", "Are you sure you want to log out?"):
            self.root.destroy()
            import login
            login.LoginUI(tk.Tk())

    def open_profile(self):
        try:
            from modules.profile import ProfileWindow
            ProfileWindow(self.root, self.username)
        except ImportError:
            messagebox.showinfo("Profile", "Profile module not yet implemented.")

    def start_auto_refresh(self):
        if self.auto_update_id:
            self.root.after_cancel(self.auto_update_id)
        self.update_summary()
        self.auto_update_id = self.root.after(30000, self.start_auto_refresh)

    def stop_auto_refresh(self):
        if self.auto_update_id:
            try:
                self.root.after_cancel(self.auto_update_id)
            except:
                pass
            self.auto_update_id = None

    def bind_shortcuts(self):
        self.root.bind("<Control-m>", lambda e: self.load_module(MembersModule, "Members"))
        self.root.bind("<Control-a>", lambda e: self.load_module(AttendanceModule, "Attendance"))
        self.root.bind("<Control-e>", lambda e: self.load_module(EventsModule, "Events"))
        self.root.bind("<Control-f>", lambda e: self.load_module(FinancialManagement, "Finance"))
        self.root.bind("<Control-b>", lambda e: self.toggle_sidebar())
        self.root.bind("<Control-s>", lambda e: self.load_module(SettingsModule, "Settings"))
        self.root.bind("<Control-r>", lambda e: self.load_module(ReportsModule, "Reports"))
        self.root.bind("<Control-d>", lambda e: self.show_dashboard())
        self.root.bind("<?>", lambda e: self.show_help())
        self.root.bind("<F1>", lambda e: self.show_help())

    def load_widget_settings(self):
        if not self.user_id:
            return ["Summary Cards", "Contribution Chart", "Attendance Trend", "Member Growth"]
        db = DatabaseManager()
        rows = db.fetch_all(
            "SELECT widget_name, is_visible FROM user_widgets WHERE user_id=? ORDER BY widget_order",
            (self.user_id,)
        )
        result = [row[0] for row in rows if row[1] == 1]
        return result if result else ["Summary Cards", "Contribution Chart", "Attendance Trend", "Member Growth"]


    def _global_mousewheel(self, event):
        """Global mouse wheel handler – scrolls main canvas only when cursor is over it."""
        # Get widget under cursor
        x, y = self.root.winfo_pointerxy()
        widget = self.root.winfo_containing(x, y)

        # If cursor is over main canvas, scroll it
        if widget == self.main_canvas:
            if event.delta:
                self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                if event.num == 4:
                    self.main_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.main_canvas.yview_scroll(1, "units")
        # Always consume the event to prevent further propagation
        return "break"

    def _add_wheel_support(self, parent):
        """Recursively bind mouse wheel to any widget that can scroll."""
        for child in parent.winfo_children():
            if hasattr(child, 'yview_scroll'):
                # Bind wheel events to the widget, and return "break" to stop propagation
                def make_handler(w):
                    def handler(event):
                        if event.delta:
                            w.yview_scroll(int(-1 * (event.delta / 120)), "units")
                        else:
                            if event.num == 4:
                                w.yview_scroll(-1, "units")
                            elif event.num == 5:
                                w.yview_scroll(1, "units")
                        return "break"
                    return handler
                child.bind("<MouseWheel>", make_handler(child))
                child.bind("<Button-4>", make_handler(child))
                child.bind("<Button-5>", make_handler(child))
            # Recurse into children
            self._add_wheel_support(child)


class NotificationHistoryUI:
    def __init__(self, parent, user_id=None, branch_id=None, controller=None):
        print("DEBUG: NotificationHistoryUI __init__ started")
        self.container = parent
        self.controller = controller  
        self.user_id = user_id
        self.branch_id = branch_id
        
        # Main Layout
        self.main_frame = tk.Frame(self.container, bg="#f4f4f4")
        self.main_frame.pack(fill="both", expand=True)
        print("DEBUG: main_frame packed")

        # --- 1. HEADER SECTION ---
        header_bg = "#1f4fa3"
        header = tk.Frame(self.main_frame, bg=header_bg, height=60)
        header.pack(fill="x")
        header.pack_propagate(False) 

        # LEFT SIDE (Title and Back)
        left_frame = tk.Frame(header, bg=header_bg)
        left_frame.pack(side="left", padx=20)

        btn_back = tk.Button(left_frame, text="← Back", bg=header_bg, fg="white", 
                            bd=0, font=("Arial", 10, "bold"), cursor="hand2", 
                            activebackground="#163c82", activeforeground="white",
                            command=self.go_back)
        btn_back.pack(side="left", padx=(0, 15))

        tk.Label(left_frame, text="Notification Archive", bg=header_bg, fg="white", 
                font=("Arial", 11, "bold")).pack(side="left")

        # SPACER
        spacer = tk.Frame(header, bg=header_bg)
        spacer.pack(side="left", expand=True, fill="x")

        # RIGHT SIDE (Purge Button)
        right_frame = tk.Frame(header, bg=header_bg)
        right_frame.pack(side="right", padx=20)

        btn_purge = tk.Label(
            right_frame, 
            text="🗑️ Purge All", 
            bg="#d32f2f",
            fg="white",
            font=("Arial", 10, "bold"), 
            cursor="hand2",    
            padx=12,
            pady=6
        )
        btn_purge.pack()
        btn_purge.bind("<Button-1>", lambda e: self.purge_archive())
        btn_purge.bind("<Enter>", lambda e: btn_purge.config(bg="#b71c1c"))
        btn_purge.bind("<Leave>", lambda e: btn_purge.config(bg="#d32f2f"))

        # --- 2. SEARCH BAR SECTION ---
        search_frame = tk.Frame(self.main_frame, bg="white", pady=12)
        search_frame.pack(fill="x", pady=(0, 1))
        
        tk.Label(search_frame, text="🔍", bg="white", fg="#999").pack(side="left", padx=(40, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.load_history())
        
        self.search_ent = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10), 
                                bg="#f0f0f0", bd=1, relief="solid", highlightthickness=0)
        self.search_ent.pack(side="left", padx=10, fill="x", expand=True, ipady=5)
        self.search_ent.bind("<Button-1>", lambda e: self.search_ent.focus_set())
        
        tk.Label(search_frame, text="", bg="white", width=5).pack(side="right", padx=40)

        # --- 3. TREEVIEW WITH SCROLLBARS (replaces old canvas) ---
        tree_container = tk.Frame(self.main_frame, bg="#f4f4f4")
        tree_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Vertical scrollbar
        vsb = ttk.Scrollbar(tree_container, orient="vertical")
        # Horizontal scrollbar
        hsb = ttk.Scrollbar(tree_container, orient="horizontal")

        columns = ("Type", "Title", "Message", "Timestamp")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings",
                                 yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Configure scrollbars
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Set column headings and widths
        self.tree.heading("Type", text="Type")
        self.tree.column("Type", width=80, anchor="center")
        self.tree.heading("Title", text="Title")
        self.tree.column("Title", width=200)
        self.tree.heading("Message", text="Message")
        self.tree.column("Message", width=400)
        self.tree.heading("Timestamp", text="Timestamp")
        self.tree.column("Timestamp", width=150, anchor="center")

        # Layout using grid for precise control
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Mouse wheel support (optional, but good)
        def on_tree_scroll(event):
            if event.delta:
                self.tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                if event.num == 4:
                    self.tree.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.tree.yview_scroll(1, "units")
            return "break"
        self.tree.bind("<MouseWheel>", on_tree_scroll)
        self.tree.bind("<Button-4>", on_tree_scroll)
        self.tree.bind("<Button-5>", on_tree_scroll)

        # Force focus
        self.search_ent.after(100, lambda: self.search_ent.focus_force())

        # Load history
        self.load_history()
        print("DEBUG: NotificationHistoryUI __init__ finished")

    def go_back(self):
        if self.controller and hasattr(self.controller, 'show_module'):
            self.controller.show_module("Dashboard")
        else:
            self.main_frame.destroy()

    def purge_archive(self):
        if not self.user_id:
            return
        if not tk.messagebox.askyesno("Confirm Purge", "Delete all notification history? This cannot be undone."):
            return
        try:
            db = DatabaseManager()
            if hasattr(db, 'execute'):
                db.execute("DELETE FROM notification_history WHERE user_id=?", (self.user_id,))
            elif hasattr(db, 'execute_query'):
                db.execute_query("DELETE FROM notification_history WHERE user_id=?", (self.user_id,))
            elif hasattr(db, 'run'):
                db.run("DELETE FROM notification_history WHERE user_id=?", (self.user_id,))
            else:
                print("ERROR: No suitable database execute method found")
                tk.messagebox.showerror("Error", "Database method not available for purge.")
                return
            self.load_history()
            tk.messagebox.showinfo("Purge Complete", "All notifications have been deleted.")
        except Exception as e:
            print(f"Purge error: {e}")
            tk.messagebox.showerror("Error", f"Failed to purge: {e}")

    def load_history(self):
        """Fetch and display notifications in the treeview."""
        print("DEBUG: load_history started")
        print(f"DEBUG: user_id = {self.user_id}")
        for row in self.tree.get_children():
            self.tree.delete(row)

        query = self.search_var.get().lower()
        
        try:
            db = DatabaseManager()
            history = db.fetch_all(
                "SELECT type, title, message, timestamp FROM notification_history WHERE user_id=? ORDER BY timestamp DESC",
                (self.user_id,)
            )
            print(f"DEBUG: history query returned {len(history) if history else 0} rows")

            if not history:
                # Insert a dummy row to show empty message (or we can just leave empty)
                # Optionally show a message in a label above tree? For now, leave empty.
                # The tree will be empty – you might add a label if desired.
                return

            for n_type, title, message, ts in history:
                if query and (query not in title.lower() and query not in message.lower()):
                    continue
                self.tree.insert("", tk.END, values=(n_type, title, message, ts))

        except Exception as e:
            print(f"Archive Error: {e}")
            # Optionally show error in tree
            self.tree.insert("", tk.END, values=("Error", str(e), "", ""))
            
            
    def _ensure_table(self, db):
        """Create notification_history table if it doesn't exist."""
        try:
            db.execute('''
                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    type TEXT,
                    title TEXT,
                    message TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        except AttributeError:
            # If db.execute doesn't exist, maybe use another method or ignore
            # Depending on your DatabaseManager, you might need to use db.execute_query, etc.
            print("Warning: Could not create notification_history table (execute method missing).")
            pass



if __name__ == "__main__":
    root = tk.Tk()
    root.minsize(1000, 600)
    DashboardUI(root, username="admin", role="Admin", user_id=1)
    root.mainloop()