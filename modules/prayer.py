# modules/prayer.py
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from database import DatabaseManager
from datetime import datetime
import csv

try:
    from config import FONT_TEXT
except ImportError:
    FONT_TEXT = ("Segoe UI", 10)

# --- Enhanced Color Palette ---
COLOR_BG = "#f3f4f6"           # Light Gray
COLOR_WHITE = "#ffffff"
COLOR_PRIMARY = "#1f4fa3"      # Brand Blue
COLOR_PRIMARY_LIGHT = "#e0e7ff"
COLOR_DANGER = "#dc2626"        # Red
COLOR_DANGER_LIGHT = "#fee2e2"
COLOR_SUCCESS = "#10b981"       # Green
COLOR_SUCCESS_LIGHT = "#d1fae5"
COLOR_WARNING = "#f59e0b"       # Orange
COLOR_TEXT = "#1f2937"
COLOR_TEXT_LIGHT = "#6b7280"
COLOR_BORDER = "#d1d5db"

class PrayerModule:
    def __init__(self, parent, user_id=None, branch_id=None):
        self.parent = parent
        self.user_id = user_id
        self.branch_id = branch_id
        self.show_private_only = False
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.on_search)  # Live search trigger

        self.main_frame = tk.Frame(parent, bg=COLOR_BG)
        self.main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.setup_ui()
        self.load_requests()

    def setup_ui(self):
        # --- Top Control Panel (Glass effect) ---
        control_frame = tk.Frame(self.main_frame, bg=COLOR_WHITE, bd=1, relief="solid", highlightbackground=COLOR_BORDER)
        control_frame.pack(fill="x", pady=(0, 15), ipady=10, ipadx=10)

        # Left: Search with clear button
        search_container = tk.Frame(control_frame, bg=COLOR_WHITE)
        search_container.pack(side="left", padx=10)

        tk.Label(search_container, text="🔍", bg=COLOR_WHITE, font=("Segoe UI", 12)).pack(side="left")
        search_entry = ttk.Entry(search_container, textvariable=self.search_var, width=30, font=FONT_TEXT)
        search_entry.pack(side="left", padx=5)

        # Clear search button
        self.clear_btn = tk.Button(search_container, text="✕", bg=COLOR_WHITE, fg=COLOR_TEXT_LIGHT,
                                   bd=0, cursor="hand2", command=self.clear_search)
        self.clear_btn.pack(side="left")
        self.clear_btn.bind("<Enter>", lambda e: self.clear_btn.config(fg=COLOR_DANGER))
        self.clear_btn.bind("<Leave>", lambda e: self.clear_btn.config(fg=COLOR_TEXT_LIGHT))
        self.clear_btn.pack_forget()  # Hide initially

        # Update clear button visibility on search change
        self.search_var.trace_add("write", self.update_clear_btn)

        # Right: Action Buttons
        btn_container = tk.Frame(control_frame, bg=COLOR_WHITE)
        btn_container.pack(side="right", padx=10)

        self.btn_add = self.create_button(btn_container, "➕ Add Request", COLOR_PRIMARY, self.open_add_window)
        self.btn_add.pack(side="left", padx=5)

        self.btn_filter = self.create_button(btn_container, "🔒 Show All", COLOR_DANGER, self.toggle_filter)
        self.btn_filter.pack(side="left", padx=5)

        self.btn_export = self.create_button(btn_container, "📥 Export", "#374151", self.export_to_csv)
        self.btn_export.pack(side="left", padx=5)

        self.btn_refresh = self.create_button(btn_container, "🔄 Refresh", COLOR_PRIMARY, self.load_requests)
        self.btn_refresh.pack(side="left", padx=5)

        # --- Data Table (Treeview) ---
        table_frame = tk.Frame(self.main_frame, bg=COLOR_WHITE, highlightbackground=COLOR_BORDER, highlightthickness=1)
        table_frame.pack(fill="both", expand=True)

        # Create style for Treeview
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Prayer.Treeview", background=COLOR_WHITE, fieldbackground=COLOR_WHITE,
                        foreground=COLOR_TEXT, rowheight=30, font=FONT_TEXT)
        style.configure("Prayer.Treeview.Heading", background=COLOR_PRIMARY, foreground="white",
                        font=("Segoe UI", 10, "bold"), relief="flat")
        style.map("Prayer.Treeview", background=[("selected", COLOR_PRIMARY_LIGHT)])

        columns = ("ID", "Member", "Request", "Date", "Status", "Privacy")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended",
                                 style="Prayer.Treeview")

        # Headings
        self.tree.heading("ID", text="ID")
        self.tree.heading("Member", text="Member Name")
        self.tree.heading("Request", text="Prayer Request")
        self.tree.heading("Date", text="Submitted")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Privacy", text="Privacy")

        # Column Widths & Alignment
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Member", width=150, anchor="w")
        self.tree.column("Request", width=300, anchor="w")
        self.tree.column("Date", width=120, anchor="center")
        self.tree.column("Status", width=100, anchor="center")
        self.tree.column("Privacy", width=80, anchor="center")

        # Scrollbars
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Tags for coloring
        self.tree.tag_configure('private', background=COLOR_DANGER_LIGHT, foreground='#991b1b')
        self.tree.tag_configure('public', background=COLOR_SUCCESS_LIGHT, foreground='#065f46')
        self.tree.tag_configure('answered', foreground='#9ca3af', font=('Segoe UI', 10, 'italic'))

        # Bindings
        self.tree.bind("<Double-1>", self.view_full_request)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # --- Bottom Action Bar ---
        action_frame = tk.Frame(self.main_frame, bg=COLOR_BG)
        action_frame.pack(fill="x", pady=(10, 0))

        self.btn_delete = self.create_button(action_frame, "🗑️ Delete Selected", COLOR_DANGER, self.delete_selected)
        self.btn_delete.pack(side="right", padx=2)

        self.btn_answered = self.create_button(action_frame, "✅ Mark Answered", COLOR_SUCCESS, self.mark_as_answered)
        self.btn_answered.pack(side="right", padx=2)

    def create_button(self, parent, text, color, command):
        """Helper to create consistent styled buttons with hover effect"""
        btn = tk.Button(parent, text=text, bg=color, fg="white",
                        font=FONT_TEXT, cursor="hand2", relief="flat",
                        padx=10, pady=5, command=command)
        btn.bind("<Enter>", lambda e: btn.config(bg=self.lighten_color(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn

    def lighten_color(self, color, factor=0.2):
        """Lighten a hex color (simple version)"""
        color = color.lstrip('#')
        rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        lighter = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
        return f"#{lighter[0]:02x}{lighter[1]:02x}{lighter[2]:02x}"

    def update_clear_btn(self, *args):
        """Show or hide the clear button based on search text"""
        if self.search_var.get():
            self.clear_btn.pack(side="left", padx=2)
        else:
            self.clear_btn.pack_forget()

    def clear_search(self):
        self.search_var.set("")
        self.load_requests()

    # --- Data Loading with Search ---
    def load_requests(self):
        search_term = self.search_var.get().strip()

        # Clear current list
        for row in self.tree.get_children():
            self.tree.delete(row)

        db = DatabaseManager()

        # Build query with search and filter
        query = """
            SELECT p.id, m.full_name, p.request, p.created_at, 
                   COALESCE(p.status, 'Active') as status, p.is_public
            FROM prayer_requests p
            LEFT JOIN members m ON p.member_id = m.id
            WHERE 1=1
        """
        params = []

        if self.show_private_only:
            query += " AND p.is_public = 0"

        if search_term:
            query += " AND (m.full_name LIKE ? OR p.request LIKE ?)"
            params.extend([f"%{search_term}%", f"%{search_term}%"])

        query += " ORDER BY p.created_at DESC"

        try:
            rows = db.fetch_all(query, params)
        except Exception as e:
            # Fallback if 'status' column missing
            if "no such column: status" in str(e):
                query = query.replace("COALESCE(p.status, 'Active') as status", "'Active' as status")
                rows = db.fetch_all(query, params)
            else:
                messagebox.showerror("Database Error", str(e))
                return

        for r in rows:
            req_id, member, request_text, created_at, status, is_public = r
            if not member:
                member = "Anonymous"

            date_str = created_at[:10] if created_at else "N/A"
            privacy = "Public" if is_public else "Private"
            display_text = (request_text[:45] + "...") if len(request_text) > 45 else request_text

            tags = ('public',) if is_public else ('private',)
            if status == 'Answered':
                tags = tags + ('answered',)

            self.tree.insert("", tk.END, values=(req_id, member, display_text, date_str, status, privacy), tags=tags)

    def on_search(self, *args):
        """Triggered by search_var trace – load data with debounce (optional)"""
        # For simplicity, just call load_requests. Could add a debounce timer.
        self.load_requests()

    # --- Event Handlers ---
    def toggle_filter(self):
        self.show_private_only = not self.show_private_only
        if self.show_private_only:
            self.btn_filter.config(text="🔒 Show Private", bg=COLOR_DANGER)
        else:
            self.btn_filter.config(text="🌐 Show All", bg=COLOR_PRIMARY)
        self.load_requests()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select at least one request to delete.")
            return
        if messagebox.askyesno("Confirm Delete", f"Delete {len(selected)} request(s)?"):
            db = DatabaseManager()
            for item in selected:
                req_id = self.tree.item(item, "values")[0]
                db.execute_query("DELETE FROM prayer_requests WHERE id = ?", (req_id,))
            self.load_requests()
            messagebox.showinfo("Success", "Requests deleted.")

    def mark_as_answered(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a request to mark as answered.")
            return

        db = DatabaseManager()
        count = 0
        try:
            for item in selected:
                req_id = self.tree.item(item, "values")[0]
                db.execute_query("UPDATE prayer_requests SET status = 'Answered' WHERE id = ?", (req_id,))
                count += 1
            self.load_requests()
            messagebox.showinfo("Success", f"{count} request(s) marked as Answered.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not update status: {e}")

    # --- Add Request Window ---
    def open_add_window(self):
        win = tk.Toplevel(self.parent)
        win.title("New Prayer Request")
        win.geometry("500x480")
        win.configure(bg=COLOR_WHITE)
        win.grab_set()

        tk.Label(win, text="Submit New Prayer Request", font=("Segoe UI", 16, "bold"),
                 bg=COLOR_WHITE, fg=COLOR_PRIMARY).pack(pady=20)

        form_frame = tk.Frame(win, bg=COLOR_WHITE)
        form_frame.pack(fill="x", padx=30)

        tk.Label(form_frame, text="Member (optional):", bg=COLOR_WHITE, font=FONT_TEXT).pack(anchor="w")
        entry_name = ttk.Entry(form_frame, font=FONT_TEXT)
        entry_name.pack(fill="x", pady=(0, 10))
        entry_name.insert(0, "Anonymous")

        tk.Label(form_frame, text="Prayer Request:", bg=COLOR_WHITE, font=FONT_TEXT).pack(anchor="w")
        txt_request = scrolledtext.ScrolledText(form_frame, height=8, font=FONT_TEXT)
        txt_request.pack(fill="x", pady=(0, 10))

        is_private_var = tk.BooleanVar()
        chk_privacy = tk.Checkbutton(form_frame, text="Keep private (Admin only)", variable=is_private_var,
                                     bg=COLOR_WHITE, font=FONT_TEXT)
        chk_privacy.pack(anchor="w", pady=5)

        def submit():
            text = txt_request.get("1.0", "end-1c").strip()
            name = entry_name.get().strip()
            if not text:
                messagebox.showwarning("Missing Info", "Please enter a prayer request.")
                return

            db = DatabaseManager()
            # In a real app, you might want to lookup member_id by name. For now, use current user if not Anonymous.
            member_id = self.user_id if name.lower() == "anonymous" else None  # You could add a lookup here.

            try:
                db.execute_query("""
                    INSERT INTO prayer_requests (member_id, request, is_public, created_at)
                    VALUES (?, ?, ?, ?)
                """, (member_id, text, 0 if is_private_var.get() else 1, datetime.now()))
                win.destroy()
                self.load_requests()
                messagebox.showinfo("Success", "Prayer request submitted.")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(win, text="Submit Request", bg=COLOR_PRIMARY, fg="white",
                  font=FONT_TEXT, command=submit).pack(pady=20)

    # --- View Full Request Window ---
    def view_full_request(self, event):
        selected = self.tree.selection()
        if not selected:
            return

        req_id = self.tree.item(selected[0], "values")[0]
        db = DatabaseManager()
        row = db.fetch_one("""
            SELECT m.full_name, p.request, p.created_at, p.is_public, COALESCE(p.status, 'Active')
            FROM prayer_requests p
            LEFT JOIN members m ON p.member_id = m.id
            WHERE p.id = ?
        """, (req_id,))

        if not row:
            return

        member, req_text, created_at, is_public, status = row

        win = tk.Toplevel(self.parent)
        win.title("Prayer Request Details")
        win.geometry("550x450")
        win.configure(bg=COLOR_WHITE)

        # Header
        header_frame = tk.Frame(win, bg=COLOR_PRIMARY_LIGHT)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text=f"From: {member or 'Anonymous'}", font=("Segoe UI", 14, "bold"),
                 bg=COLOR_PRIMARY_LIGHT, fg=COLOR_PRIMARY).pack(pady=15, padx=20, anchor="w")

        # Meta
        meta_frame = tk.Frame(win, bg=COLOR_WHITE)
        meta_frame.pack(fill="x", padx=20, pady=10)

        status_color = COLOR_SUCCESS if status == 'Answered' else COLOR_PRIMARY
        tk.Label(meta_frame, text=f"Status: {status}", fg=status_color, font=("Segoe UI", 11, "bold"),
                 bg=COLOR_WHITE).pack(side="left", padx=(0, 20))

        privacy_label = "Private" if not is_public else "Public"
        privacy_color = COLOR_DANGER if not is_public else COLOR_SUCCESS
        tk.Label(meta_frame, text=f"Privacy: {privacy_label}", fg=privacy_color,
                 font=("Segoe UI", 11), bg=COLOR_WHITE).pack(side="left")

        # Content
        txt_area = scrolledtext.ScrolledText(win, wrap="word", font=("Segoe UI", 11), bg="#f9fafb", bd=0)
        txt_area.pack(fill="both", expand=True, padx=20, pady=10)
        txt_area.insert("1.0", req_text)
        txt_area.config(state="disabled")

        tk.Button(win, text="Close", command=win.destroy, bg=COLOR_TEXT_LIGHT, fg="white").pack(pady=10)

    # --- Context Menu ---
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return

        self.tree.selection_set(item)
        menu = tk.Menu(self.parent, tearoff=0)
        menu.add_command(label="View Details", command=lambda: self.view_full_request(None))
        menu.add_command(label="Mark as Answered", command=self.mark_as_answered)
        menu.add_separator()
        menu.add_command(label="Delete", command=self.delete_selected)
        menu.post(event.x_root, event.y_root)

    # --- Export to CSV ---
    def export_to_csv(self):
        if not self.tree.get_children():
            messagebox.showinfo("Info", "No data to export.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Prayer Requests"
        )

        if filename:
            try:
                with open(filename, mode='w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(["ID", "Member", "Request", "Date", "Status", "Privacy"])
                    for item in self.tree.get_children():
                        writer.writerow(self.tree.item(item)['values'])
                messagebox.showinfo("Success", f"Exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")