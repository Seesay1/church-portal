# modules/committees.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import csv
import os
import re
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from database import DatabaseManager

try:
    from config import FONT_TEXT
except ImportError:
    FONT_TEXT = ("Helvetica", 10)

# ================== CONSTANTS ==================
PAD = 10
SMALL_PAD = 5
COLORS = {
    "bg": "#e8f1ff",
    "card_bg": "#ffffff",
    "accent": "#1f4fa3",
    "accent_light": "#2a9df4",
    "red": "#d62828",
    "red_light": "#f77b7b",
    "gray": "#333333",
    "gray_light": "#5a5a5a",
    "sidebar": "#0b3d91",
    "green": "#27ae60",
    "green_light": "#2ecc71"
}

# ================== TOOLTIP CLASS ==================
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

# ================== TOAST NOTIFICATION ==================
def show_toast(parent, message, duration=2000):
    toast = tk.Toplevel(parent)
    toast.overrideredirect(True)
    toast.configure(bg=COLORS["gray"])
    x = parent.winfo_rootx() + parent.winfo_width()//2 - 150
    y = parent.winfo_rooty() + 80
    toast.geometry(f"+{x}+{y}")
    tk.Label(toast, text=message, bg=COLORS["gray"], fg="white",
             font=("Helvetica", 10), padx=20, pady=10).pack()
    toast.after(duration, toast.destroy)

# ================== COMMITTEES MODULE ==================
class CommitteesModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg=COLORS["bg"])
        self.user_id = user_id
        self.branch_id = branch_id

        self.search_var = tk.StringVar()
        self.branch_filter_var = tk.StringVar(value="All")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        self.list_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.list_frame, text="📋 Committees")

        self.setup_list_tab()
        self.load_committees()

    def _add_hover(self, button, normal_bg, hover_bg):
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=normal_bg))

    def _lighten(self, color):
        if color == COLORS["red"]:
            return COLORS["red_light"]
        if color == COLORS["accent"]:
            return COLORS["accent_light"]
        if color == COLORS["gray"]:
            return COLORS["gray_light"]
        if color == COLORS["green"]:
            return COLORS["green_light"]
        return color

    # ---------- Committees List Tab ----------
    def setup_list_tab(self):
    # Top row: action buttons
        top_toolbar = tk.Frame(self.list_frame, bg=COLORS["bg"])
        top_toolbar.pack(fill="x", padx=PAD, pady=(SMALL_PAD, 0))

        btn_frame = tk.Frame(top_toolbar, bg=COLORS["bg"])
        btn_frame.pack(side="left")

        buttons = [
            ("➕ New Committee", COLORS["red"], self.add_committee, "Create a new committee"),
            ("✏️ Edit Selected", COLORS["accent"], self.edit_committee, "Edit the selected committee"),
            ("🗑️ Delete Selected", COLORS["gray"], self.delete_committee, "Delete selected committee (and all related data)"),
            ("🗑️ Clear All", COLORS["gray"], self.clear_all_committees, "Delete ALL committees and start fresh"),
            ("🔄 Refresh", COLORS["green"], self.load_committees, "Refresh the committee list"),
            ("🖨️ Print List", COLORS["green"], self.print_committee_list, "Print list of all committees"),
        ]
        for text, bg, cmd, tip in buttons:
            btn = tk.Button(btn_frame, text=text, bg=bg, fg="white", font=FONT_TEXT,
                            command=cmd, padx=SMALL_PAD)
            btn.pack(side="left", padx=SMALL_PAD)
            self._add_hover(btn, bg, self._lighten(bg))
            ToolTip(btn, tip)

        # Second row: search and filter
        bottom_toolbar = tk.Frame(self.list_frame, bg=COLORS["bg"])
        bottom_toolbar.pack(fill="x", padx=PAD, pady=(0, SMALL_PAD))

        # Push controls to the right
        tk.Label(bottom_toolbar, bg=COLORS["bg"]).pack(side="left", expand=True, fill="x")

        # Branch filter
        tk.Label(bottom_toolbar, text="Branch:", bg=COLORS["bg"], font=FONT_TEXT).pack(side="left", padx=SMALL_PAD)
        db = DatabaseManager()
        branches = db.fetch_all("SELECT id, name FROM branches ORDER BY name")
        self.branch_list = ["All"] + [b[1] for b in branches]
        self.branch_id_map = {b[1]: b[0] for b in branches}
        self.branch_filter_combo = ttk.Combobox(bottom_toolbar, textvariable=self.branch_filter_var,
                                                values=self.branch_list, state="readonly", width=12)
        self.branch_filter_combo.pack(side="left", padx=SMALL_PAD)
        self.branch_filter_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_committees())

        # Search
        tk.Label(bottom_toolbar, text="🔍 Search:", bg=COLORS["bg"], font=FONT_TEXT).pack(side="left", padx=SMALL_PAD)
        self.search_var.trace("w", lambda a,b,c: self.filter_committees())
        tk.Entry(bottom_toolbar, textvariable=self.search_var, font=FONT_TEXT, width=12).pack(side="left", padx=SMALL_PAD)
        clear_btn = tk.Button(bottom_toolbar, text="✖", bg=COLORS["bg"], fg=COLORS["gray"], font=("Helvetica", 10),
                            bd=0, command=self.clear_search)
        clear_btn.pack(side="left", padx=2)
        self._add_hover(clear_btn, COLORS["bg"], "#cccccc")

        # Treeview frame (unchanged)
        tree_frame = tk.Frame(self.list_frame, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        # Added "Branch" column
        columns = ("ID", "Committee Name", "Chairperson", "Members", "Branch", "Created")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        widths = [50, 250, 150, 80, 120, 120]
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=50, stretch=False)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.open_committee_details)

        self.all_committees = []  # will store (item_id, name, branch) for filtering

    def load_committees(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.all_committees.clear()
        db = DatabaseManager()
        # Updated query to include branch name
        rows = db.fetch_all("""
            SELECT c.id, c.name, m.full_name,
                   (SELECT COUNT(*) FROM committee_members WHERE committee_id = c.id) as member_count,
                   COALESCE(b.name, '') as branch_name,
                   c.created_date
            FROM committees c
            LEFT JOIN members m ON c.chairperson_id = m.id
            LEFT JOIN branches b ON c.branch_id = b.id
            ORDER BY c.name
        """)
        for r in rows:
            item_id = self.tree.insert("", tk.END, values=r)
            self.all_committees.append((item_id, r[1].lower(), r[4].lower()))  # name, branch
        self.filter_committees()

    def filter_committees(self):
        search = self.search_var.get().strip().lower()
        branch_filter = self.branch_filter_var.get()
        for item_id, name, branch in self.all_committees:
            show = True
            if search and search not in name:
                show = False
            if branch_filter != "All" and branch != branch_filter.lower():
                show = False
            if show:
                self.tree.reattach(item_id, "", "end")
            else:
                self.tree.detach(item_id)

    def clear_search(self):
        self.search_var.set("")
        self.filter_committees()

    def add_committee(self):
        self._committee_form("Add Committee")

    def edit_committee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a committee to edit.")
            return
        item = self.tree.item(selected[0])
        committee_id = item['values'][0]
        self._committee_form("Edit Committee", committee_id)

    def delete_committee(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a committee to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected committee? This will also delete all members, meetings, activities, and expenses."):
            return
        db = DatabaseManager()
        for item in selected:
            committee_id = self.tree.item(item)['values'][0]
            # Delete related records
            db.execute_query("DELETE FROM committee_expenses WHERE activity_id IN (SELECT id FROM committee_activities WHERE committee_id=?)", (committee_id,))
            db.execute_query("DELETE FROM committee_activities WHERE committee_id=?", (committee_id,))
            db.execute_query("DELETE FROM committee_meetings WHERE committee_id=?", (committee_id,))
            db.execute_query("DELETE FROM committee_members WHERE committee_id=?", (committee_id,))
            db.execute_query("DELETE FROM committee_roles WHERE committee_id=?", (committee_id,))
            db.execute_query("DELETE FROM committees WHERE id=?", (committee_id,))
        self.load_committees()
        show_toast(self.root, "Committee(s) deleted")

    def clear_all_committees(self):
        """Delete ALL committees and all related data. Use with caution."""
        if not messagebox.askyesno("Confirm Clear All", "This will delete ALL committees and all their members, meetings, activities, expenses, and custom roles. This action cannot be undone. Continue?"):
            return
        db = DatabaseManager()
        # Delete in correct order (foreign keys)
        db.execute_query("DELETE FROM committee_expenses")
        db.execute_query("DELETE FROM committee_activities")
        db.execute_query("DELETE FROM committee_meetings")
        db.execute_query("DELETE FROM committee_members")
        db.execute_query("DELETE FROM committee_roles")
        db.execute_query("DELETE FROM committees")
        self.load_committees()
        show_toast(self.root, "All committees cleared")

    def print_committee_list(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save Committees List as PDF",
            initialfile=f"Committees_List_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        if not file_path:
            return
        try:
            doc = SimpleDocTemplate(file_path, pagesize=landscape(A4),
                                    rightMargin=10*mm, leftMargin=10*mm,
                                    topMargin=15*mm, bottomMargin=10*mm)
            elements = []
            styles = getSampleStyleSheet()
            title = f"Committees List - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            elements.append(Paragraph(title, styles['Title']))
            elements.append(Spacer(1, 5*mm))

            data = [["ID", "Committee Name", "Chairperson", "Members", "Branch", "Created"]]
            for row in self.tree.get_children():
                values = self.tree.item(row)['values']  # keep all
                data.append([str(v) for v in values])

            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLORS["accent"])),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
            ]))
            elements.append(table)

            doc.build(elements)
            show_toast(self.root, "PDF generated successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {e}")

    def _committee_form(self, title, committee_id=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("550x600")  # a bit taller to include branch
        win.minsize(550, 600)
        win.configure(bg=COLORS["bg"])
        win.transient(self.root)
        win.grab_set()
        win.resizable(True, True)

        win.update_idletasks()
        x = (win.winfo_screenwidth() - win.winfo_width()) // 2
        y = (win.winfo_screenheight() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

        main = tk.Frame(win, bg=COLORS["bg"])
        main.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        card = tk.Frame(main, bg="white", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=SMALL_PAD, pady=SMALL_PAD)

        field_frame = tk.Frame(card, bg="white")
        field_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        row = 0
        # Committee Name
        tk.Label(field_frame, text="Committee Name:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        name_entry = tk.Entry(field_frame, font=FONT_TEXT, width=40, bg="#f9f9f9")
        name_entry.grid(row=row, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")
        row += 1

        # Description
        tk.Label(field_frame, text="Description:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="nw", pady=SMALL_PAD)
        desc_text = tk.Text(field_frame, height=6, width=40, font=FONT_TEXT, bg="#f9f9f9")
        desc_text.grid(row=row, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")
        row += 1

        # Chairperson (Member ID)
        tk.Label(field_frame, text="Chairperson (Member ID):", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        chair_entry = tk.Entry(field_frame, font=FONT_TEXT, width=40, bg="#f9f9f9")
        chair_entry.grid(row=row, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")
        row += 1

        # Branch selection
        tk.Label(field_frame, text="Branch:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        db = DatabaseManager()
        branches = db.fetch_all("SELECT id, name FROM branches ORDER BY name")
        branch_names = ["None"] + [b[1] for b in branches]
        branch_id_map = {b[1]: b[0] for b in branches}
        branch_combo = ttk.Combobox(field_frame, values=branch_names, state="readonly", width=37)
        branch_combo.set("None")
        branch_combo.grid(row=row, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="w")
        row += 1

        field_frame.columnconfigure(1, weight=1)

        if committee_id:
            db = DatabaseManager()
            comm = db.fetch_one("SELECT name, description, chairperson_id, branch_id FROM committees WHERE id=?", (committee_id,))
            if comm:
                name_entry.insert(0, comm[0] or "")
                desc_text.insert("1.0", comm[1] or "")
                if comm[2]:
                    mem = db.fetch_one("SELECT member_id FROM members WHERE id=?", (comm[2],))
                    if mem:
                        chair_entry.insert(0, mem[0])
                if comm[3]:
                    # find branch name
                    branch_name = next((b[1] for b in branches if b[0] == comm[3]), "None")
                    branch_combo.set(branch_name)

        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(fill="x", pady=PAD)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Committee name is required.")
                return
            desc = desc_text.get("1.0", tk.END).strip()
            chair_member_id = chair_entry.get().strip()
            branch_name = branch_combo.get()
            branch_id = branch_id_map.get(branch_name) if branch_name != "None" else None

            db = DatabaseManager()
            chairperson_id = None
            if chair_member_id:
                mem = db.fetch_one("SELECT id FROM members WHERE member_id=?", (chair_member_id,))
                if not mem:
                    messagebox.showerror("Error", "Member not found with that ID.")
                    return
                chairperson_id = mem[0]

            if committee_id:
                db.execute_query(
                    "UPDATE committees SET name=?, description=?, chairperson_id=?, branch_id=? WHERE id=?",
                    (name, desc, chairperson_id, branch_id, committee_id)
                )
                show_toast(win, "Committee updated")
            else:
                created = datetime.now().strftime("%Y-%m-%d")
                db.execute_query(
                    "INSERT INTO committees (name, description, chairperson_id, branch_id, created_date) VALUES (?,?,?,?,?)",
                    (name, desc, chairperson_id, branch_id, created)
                )
                show_toast(win, "Committee added")
            win.destroy()
            self.load_committees()

        save_btn = tk.Button(btn_frame, text="Save", bg=COLORS["accent"], fg="white",
                             font=FONT_TEXT, width=12, command=save)
        save_btn.pack(side="right", padx=SMALL_PAD)
        self._add_hover(save_btn, COLORS["accent"], COLORS["accent_light"])

        cancel_btn = tk.Button(btn_frame, text="Cancel", bg=COLORS["gray"], fg="white",
                               font=FONT_TEXT, width=12, command=win.destroy)
        cancel_btn.pack(side="right", padx=SMALL_PAD)
        self._add_hover(cancel_btn, COLORS["gray"], COLORS["gray_light"])

    def open_committee_details(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        committee_id = item['values'][0]
        committee_name = item['values'][1]
        CommitteeDetailsWindow(self.root, committee_id, committee_name, self.user_id)


# ================== COMMITTEE DETAILS WINDOW (unchanged) ==================
class CommitteeDetailsWindow:
    def __init__(self, parent, committee_id, committee_name, user_id):
        self.win = tk.Toplevel(parent)
        self.win.title(f"Committee: {committee_name}")
        self.win.geometry("1100x750")
        self.win.minsize(900, 600)
        self.win.configure(bg=COLORS["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        self.committee_id = committee_id
        self.user_id = user_id

        # Header with committee name and print button
        header = tk.Frame(self.win, bg=COLORS["accent"], height=50)
        header.pack(fill="x")
        tk.Label(header, text=committee_name, font=("Helvetica", 14, "bold"),
                 bg=COLORS["accent"], fg="white").pack(side="left", padx=PAD)

        self.print_btn = tk.Button(header, text="🖨️ Print Full Report", bg=COLORS["green"], fg="white",
                                   font=FONT_TEXT, command=self.print_full_report)
        self.print_btn.pack(side="right", padx=PAD)
        self._add_hover(self.print_btn, COLORS["green"], COLORS["green_light"])

        # Main paned window
        self.paned = ttk.PanedWindow(self.win, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        # Left sidebar
        self.left_frame = tk.Frame(self.paned, bg=COLORS["bg"], width=250)
        self.paned.add(self.left_frame, weight=0)
        self.setup_left_panel()

        # Right notebook
        self.right_frame = tk.Frame(self.paned, bg=COLORS["bg"])
        self.paned.add(self.right_frame, weight=1)

        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill="both", expand=True)

        self.members_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.members_frame, text="👥 Members")

        self.meetings_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.meetings_frame, text="📅 Meetings")

        self.activities_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.activities_frame, text="📋 Activities")

        self.expenses_frame = tk.Frame(self.notebook, bg=COLORS["bg"])
        self.notebook.add(self.expenses_frame, text="💰 Expenses")

        self.setup_members_tab()
        self.setup_meetings_tab()
        self.setup_activities_tab()
        self.setup_expenses_tab()

        self.load_stats()

    def _add_hover(self, button, normal_bg, hover_bg):
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=normal_bg))

    def setup_left_panel(self):
        card = tk.Frame(self.left_frame, bg="white", bd=1, relief="solid")
        card.pack(fill="x", padx=SMALL_PAD, pady=SMALL_PAD)

        tk.Label(card, text="Committee Info", font=("Helvetica", 12, "bold"),
                 bg="white", fg=COLORS["accent"]).pack(pady=SMALL_PAD)

        self.stats_labels = {}
        stats = [("Members", "0"), ("Activities", "0"), ("Total Budget", "₵0"), ("Total Expenses", "₵0")]
        for label, value in stats:
            frame = tk.Frame(card, bg="white")
            frame.pack(fill="x", pady=2)
            tk.Label(frame, text=label, bg="white", font=FONT_TEXT, width=12, anchor="w").pack(side="left", padx=SMALL_PAD)
            lbl = tk.Label(frame, text=value, bg="white", font=("Helvetica", 10, "bold"), fg=COLORS["accent"])
            lbl.pack(side="right", padx=SMALL_PAD)
            self.stats_labels[label] = lbl

    def load_stats(self):
        db = DatabaseManager()
        member_count = db.fetch_one("SELECT COUNT(*) FROM committee_members WHERE committee_id=?", (self.committee_id,))[0] or 0
        activity_count = db.fetch_one("SELECT COUNT(*) FROM committee_activities WHERE committee_id=?", (self.committee_id,))[0] or 0
        total_budget = db.fetch_one("SELECT SUM(budget) FROM committee_activities WHERE committee_id=?", (self.committee_id,))[0] or 0
        total_expenses = db.fetch_one("""
            SELECT SUM(e.amount) FROM committee_expenses e
            JOIN committee_activities a ON e.activity_id = a.id
            WHERE a.committee_id = ?
        """, (self.committee_id,))[0] or 0

        self.stats_labels["Members"].config(text=str(member_count))
        self.stats_labels["Activities"].config(text=str(activity_count))
        self.stats_labels["Total Budget"].config(text=f"₵{total_budget:,.2f}")
        self.stats_labels["Total Expenses"].config(text=f"₵{total_expenses:,.2f}")

    # ---------- Members Tab (with search) ----------
    def setup_members_tab(self):
        toolbar = tk.Frame(self.members_frame, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=PAD, pady=SMALL_PAD)

        # Left side buttons
        btn_frame = tk.Frame(toolbar, bg=COLORS["bg"])
        btn_frame.pack(side="left")

        add_btn = tk.Button(btn_frame, text="➕ Add Member", bg=COLORS["accent"], fg="white",
                            font=FONT_TEXT, command=self.add_member)
        add_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(add_btn, COLORS["accent"], COLORS["accent_light"])

        remove_btn = tk.Button(btn_frame, text="🗑️ Remove Selected", bg=COLORS["gray"], fg="white",
                               font=FONT_TEXT, command=self.remove_member)
        remove_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(remove_btn, COLORS["gray"], COLORS["gray_light"])

        export_btn = tk.Button(btn_frame, text="📥 Export CSV", bg=COLORS["green"], fg="white",
                               font=FONT_TEXT, command=self.export_members_csv)
        export_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(export_btn, COLORS["green"], COLORS["green_light"])

        roles_btn = tk.Button(btn_frame, text="⚙️ Manage Roles", bg=COLORS["accent"], fg="white",
                              font=FONT_TEXT, command=self.manage_roles)
        roles_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(roles_btn, COLORS["accent"], COLORS["accent_light"])
        ToolTip(roles_btn, "Add, edit, or delete committee‑specific roles")

        # Search on the right
        search_frame = tk.Frame(toolbar, bg=COLORS["bg"])
        search_frame.pack(side="right", padx=SMALL_PAD)
        tk.Label(search_frame, text="🔍 Search Members:", bg=COLORS["bg"], font=FONT_TEXT).pack(side="left", padx=SMALL_PAD)
        self.member_search_var = tk.StringVar()
        self.member_search_var.trace("w", lambda a,b,c: self.filter_members())
        tk.Entry(search_frame, textvariable=self.member_search_var, font=FONT_TEXT, width=20).pack(side="left", padx=SMALL_PAD)
        clear_member_btn = tk.Button(search_frame, text="✖", bg=COLORS["bg"], fg=COLORS["gray"], font=("Helvetica", 10),
                                     bd=0, command=self.clear_member_search)
        clear_member_btn.pack(side="left", padx=2)
        self._add_hover(clear_member_btn, COLORS["bg"], "#cccccc")

        # Treeview frame
        tree_frame = tk.Frame(self.members_frame, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=SMALL_PAD)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Member ID", "Full Name", "Role", "Joined")
        self.members_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                          yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.members_tree.yview)
        hsb.config(command=self.members_tree.xview)

        widths = [50, 100, 180, 150, 100]
        for col, w in zip(columns, widths):
            self.members_tree.heading(col, text=col)
            self.members_tree.column(col, width=w, minwidth=50, stretch=False)

        self.members_tree.pack(fill="both", expand=True)

        # Store all members for filtering
        self.all_members = []

        self.load_members()

    def load_members(self):
        for row in self.members_tree.get_children():
            self.members_tree.delete(row)
        self.all_members.clear()
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT cm.id, m.member_id, m.full_name, cm.role, cm.joined_date
            FROM committee_members cm
            LEFT JOIN members m ON cm.member_id = m.id
            WHERE cm.committee_id = ?
            ORDER BY m.full_name
        """, (self.committee_id,))
        for r in rows:
            item_id = self.members_tree.insert("", tk.END, values=r)
            # Store for filtering: (item_id, member_id, full_name, role)
            self.all_members.append((item_id, r[1] or "", r[2] or "", r[3] or ""))
        self.filter_members()
        self.load_stats()

    def filter_members(self):
        search = self.member_search_var.get().strip().lower()
        for item_id, member_id, full_name, role in self.all_members:
            if search and search not in member_id.lower() and search not in full_name.lower() and search not in role.lower():
                self.members_tree.detach(item_id)
            else:
                self.members_tree.reattach(item_id, "", "end")

    def clear_member_search(self):
        self.member_search_var.set("")
        self.filter_members()

    def export_members_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Members",
            initialfile=f"committee_{self.committee_id}_members.csv"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Member ID", "Full Name", "Role", "Joined Date"])
                for row in self.members_tree.get_children():
                    values = self.members_tree.item(row)['values'][1:-1]
                    writer.writerow(values)
            show_toast(self.win, "Members exported")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def manage_roles(self):
        ManageRolesDialog(self.win, self.committee_id)

    def add_member(self):
        db = DatabaseManager()
        role_rows = db.fetch_all("SELECT name FROM committee_roles WHERE committee_id=? ORDER BY name", (self.committee_id,))
        predefined_roles = [r[0] for r in role_rows]

        win = tk.Toplevel(self.win)
        win.title("Add Member to Committee")
        win.geometry("400x250")
        win.configure(bg=COLORS["bg"])
        win.transient(self.win)
        win.grab_set()

        tk.Label(win, text="Member ID:", bg=COLORS["bg"], font=FONT_TEXT).pack(pady=PAD)
        member_entry = tk.Entry(win, font=FONT_TEXT, width=30, bg="#f9f9f9")
        member_entry.pack(pady=SMALL_PAD)

        tk.Label(win, text="Role:", bg=COLORS["bg"], font=FONT_TEXT).pack(pady=PAD)
        role_var = tk.StringVar()
        role_combo = ttk.Combobox(win, textvariable=role_var, values=predefined_roles, width=27)
        role_combo.pack(pady=SMALL_PAD)
        if predefined_roles:
            role_combo.set(predefined_roles[0])

        def save():
            member_id_str = member_entry.get().strip()
            role = role_var.get().strip()
            if not member_id_str:
                messagebox.showerror("Error", "Member ID is required.")
                return
            if not role:
                messagebox.showerror("Error", "Role is required.")
                return

            # If role not in list, add it automatically
            if role not in predefined_roles:
                try:
                    db.execute_query(
                        "INSERT INTO committee_roles (committee_id, name) VALUES (?,?)",
                        (self.committee_id, role)
                    )
                except Exception as e:
                    messagebox.showerror("Error", f"Could not add role: {e}")
                    return

            member = db.fetch_one("SELECT id FROM members WHERE member_id=?", (member_id_str,))
            if not member:
                messagebox.showerror("Error", "Member not found.")
                return
            member_db_id = member[0]
            existing = db.fetch_one("SELECT id FROM committee_members WHERE committee_id=? AND member_id=?", (self.committee_id, member_db_id))
            if existing:
                messagebox.showerror("Error", "Member already in this committee.")
                return
            joined = datetime.now().strftime("%Y-%m-%d")
            db.execute_query(
                "INSERT INTO committee_members (committee_id, member_id, role, joined_date) VALUES (?,?,?,?)",
                (self.committee_id, member_db_id, role, joined)
            )
            win.destroy()
            self.load_members()
            show_toast(self.win, "Member added")

        btn_frame = tk.Frame(win, bg=COLORS["bg"])
        btn_frame.pack(pady=PAD)
        tk.Button(btn_frame, text="Add", bg=COLORS["accent"], fg="white",
                  command=save).pack(side="left", padx=SMALL_PAD)
        tk.Button(btn_frame, text="Cancel", bg=COLORS["gray"], fg="white",
                  command=win.destroy).pack(side="left", padx=SMALL_PAD)

    def remove_member(self):
        selected = self.members_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a member to remove.")
            return
        if not messagebox.askyesno("Confirm", "Remove selected member from committee?"):
            return
        db = DatabaseManager()
        for item in selected:
            mem_id = self.members_tree.item(item)['values'][0]
            db.execute_query("DELETE FROM committee_members WHERE id=?", (mem_id,))
        self.load_members()
        show_toast(self.win, "Member(s) removed")

    # ---------- Meetings Tab ----------
    def setup_meetings_tab(self):
        toolbar = tk.Frame(self.meetings_frame, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=PAD, pady=SMALL_PAD)

        add_btn = tk.Button(toolbar, text="➕ Add Meeting", bg=COLORS["accent"], fg="white",
                            font=FONT_TEXT, command=self.add_meeting)
        add_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(add_btn, COLORS["accent"], COLORS["accent_light"])

        delete_btn = tk.Button(toolbar, text="🗑️ Delete Selected", bg=COLORS["gray"], fg="white",
                               font=FONT_TEXT, command=self.delete_meeting)
        delete_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(delete_btn, COLORS["gray"], COLORS["gray_light"])

        export_btn = tk.Button(toolbar, text="📥 Export CSV", bg=COLORS["green"], fg="white",
                               font=FONT_TEXT, command=self.export_meetings_csv)
        export_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(export_btn, COLORS["green"], COLORS["green_light"])

        tree_frame = tk.Frame(self.meetings_frame, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=SMALL_PAD)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Date", "Agenda", "Location")
        self.meetings_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.meetings_tree.yview)
        hsb.config(command=self.meetings_tree.xview)

        widths = [50, 100, 400, 150]
        for col, w in zip(columns, widths):
            self.meetings_tree.heading(col, text=col)
            self.meetings_tree.column(col, width=w, minwidth=50, stretch=False)

        self.meetings_tree.pack(fill="both", expand=True)
        self.load_meetings()

    def load_meetings(self):
        for row in self.meetings_tree.get_children():
            self.meetings_tree.delete(row)
        db = DatabaseManager()
        rows = db.fetch_all("SELECT id, meeting_date, agenda, location FROM committee_meetings WHERE committee_id=? ORDER BY meeting_date DESC", (self.committee_id,))
        for r in rows:
            self.meetings_tree.insert("", tk.END, values=r)

    def export_meetings_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Meetings",
            initialfile=f"committee_{self.committee_id}_meetings.csv"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Agenda", "Location"])
                for row in self.meetings_tree.get_children():
                    values = self.meetings_tree.item(row)['values'][1:]
                    writer.writerow(values)
            show_toast(self.win, "Meetings exported")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def add_meeting(self):
        from tkcalendar import DateEntry
        win = tk.Toplevel(self.win)
        win.title("Add Meeting")
        win.geometry("500x450")
        win.configure(bg=COLORS["bg"])
        win.transient(self.win)
        win.grab_set()

        card = tk.Frame(win, bg="white", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        field_frame = tk.Frame(card, bg="white")
        field_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        tk.Label(field_frame, text="Date:", bg="white", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=SMALL_PAD)
        date_entry = DateEntry(field_frame, width=12, background=COLORS["accent"], foreground='white',
                               borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        date_entry.grid(row=0, column=1, sticky="w", pady=SMALL_PAD, padx=SMALL_PAD)

        tk.Label(field_frame, text="Agenda:", bg="white", font=FONT_TEXT).grid(row=1, column=0, sticky="nw", pady=SMALL_PAD)
        agenda_text = tk.Text(field_frame, height=6, width=40, font=FONT_TEXT, bg="#f9f9f9")
        agenda_text.grid(row=1, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")

        tk.Label(field_frame, text="Location:", bg="white", font=FONT_TEXT).grid(row=2, column=0, sticky="w", pady=SMALL_PAD)
        location_entry = tk.Entry(field_frame, font=FONT_TEXT, width=40, bg="#f9f9f9")
        location_entry.grid(row=2, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")

        field_frame.columnconfigure(1, weight=1)

        def save():
            date = date_entry.get_date().strftime("%Y-%m-%d")
            agenda = agenda_text.get("1.0", tk.END).strip()
            location = location_entry.get().strip()
            db = DatabaseManager()
            db.execute_query(
                "INSERT INTO committee_meetings (committee_id, meeting_date, agenda, location) VALUES (?,?,?,?)",
                (self.committee_id, date, agenda, location)
            )
            win.destroy()
            self.load_meetings()
            show_toast(self.win, "Meeting added")

        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(pady=PAD)
        tk.Button(btn_frame, text="Save", bg=COLORS["accent"], fg="white",
                  command=save).pack(side="left", padx=SMALL_PAD)
        tk.Button(btn_frame, text="Cancel", bg=COLORS["gray"], fg="white",
                  command=win.destroy).pack(side="left", padx=SMALL_PAD)

    def delete_meeting(self):
        selected = self.meetings_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a meeting to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected meeting?"):
            return
        db = DatabaseManager()
        for item in selected:
            meet_id = self.meetings_tree.item(item)['values'][0]
            db.execute_query("DELETE FROM committee_meetings WHERE id=?", (meet_id,))
        self.load_meetings()
        show_toast(self.win, "Meeting(s) deleted")

    # ---------- Activities Tab ----------
    def setup_activities_tab(self):
        toolbar = tk.Frame(self.activities_frame, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=PAD, pady=SMALL_PAD)

        add_btn = tk.Button(toolbar, text="➕ Add Activity", bg=COLORS["accent"], fg="white",
                            font=FONT_TEXT, command=self.add_activity)
        add_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(add_btn, COLORS["accent"], COLORS["accent_light"])

        delete_btn = tk.Button(toolbar, text="🗑️ Delete Selected", bg=COLORS["gray"], fg="white",
                               font=FONT_TEXT, command=self.delete_activity)
        delete_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(delete_btn, COLORS["gray"], COLORS["gray_light"])

        export_btn = tk.Button(toolbar, text="📥 Export CSV", bg=COLORS["green"], fg="white",
                               font=FONT_TEXT, command=self.export_activities_csv)
        export_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(export_btn, COLORS["green"], COLORS["green_light"])

        tree_frame = tk.Frame(self.activities_frame, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=SMALL_PAD)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Name", "Start", "End", "Budget", "Status")
        self.activities_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                             yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.activities_tree.yview)
        hsb.config(command=self.activities_tree.xview)

        widths = [50, 200, 100, 100, 100, 100]
        for col, w in zip(columns, widths):
            self.activities_tree.heading(col, text=col)
            self.activities_tree.column(col, width=w, minwidth=50, stretch=False)

        self.activities_tree.pack(fill="both", expand=True)
        self.load_activities()

    def load_activities(self):
        for row in self.activities_tree.get_children():
            self.activities_tree.delete(row)
        db = DatabaseManager()
        rows = db.fetch_all("SELECT id, name, start_date, end_date, budget, status FROM committee_activities WHERE committee_id=? ORDER BY start_date", (self.committee_id,))
        for r in rows:
            self.activities_tree.insert("", tk.END, values=r)
        self.load_stats()

    def export_activities_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Activities",
            initialfile=f"committee_{self.committee_id}_activities.csv"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Name", "Start Date", "End Date", "Budget", "Status"])
                for row in self.activities_tree.get_children():
                    values = self.activities_tree.item(row)['values'][1:-1]
                    writer.writerow(values)
            show_toast(self.win, "Activities exported")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def add_activity(self):
        from tkcalendar import DateEntry
        win = tk.Toplevel(self.win)
        win.title("Add Activity")
        win.geometry("550x500")
        win.configure(bg=COLORS["bg"])
        win.transient(self.win)
        win.grab_set()

        card = tk.Frame(win, bg="white", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        field_frame = tk.Frame(card, bg="white")
        field_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        row = 0
        tk.Label(field_frame, text="Activity Name:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        name_entry = tk.Entry(field_frame, font=FONT_TEXT, width=40, bg="#f9f9f9")
        name_entry.grid(row=row, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")
        row += 1

        tk.Label(field_frame, text="Description:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="nw", pady=SMALL_PAD)
        desc_text = tk.Text(field_frame, height=4, width=40, font=FONT_TEXT, bg="#f9f9f9")
        desc_text.grid(row=row, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")
        row += 1

        tk.Label(field_frame, text="Start Date:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        start_date = DateEntry(field_frame, width=12, background=COLORS["accent"], foreground='white',
                               borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        start_date.grid(row=row, column=1, sticky="w", pady=SMALL_PAD, padx=SMALL_PAD)
        start_date.set_date(datetime.now())
        row += 1

        tk.Label(field_frame, text="End Date:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        end_date = DateEntry(field_frame, width=12, background=COLORS["accent"], foreground='white',
                             borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        end_date.grid(row=row, column=1, sticky="w", pady=SMALL_PAD, padx=SMALL_PAD)
        end_date.set_date(datetime.now())
        row += 1

        tk.Label(field_frame, text="Budget (₵):", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        budget_entry = tk.Entry(field_frame, font=FONT_TEXT, width=20, bg="#f9f9f9")
        budget_entry.grid(row=row, column=1, sticky="w", pady=SMALL_PAD, padx=SMALL_PAD)
        budget_entry.insert(0, "0")
        row += 1

        tk.Label(field_frame, text="Status:", bg="white", font=FONT_TEXT).grid(row=row, column=0, sticky="w", pady=SMALL_PAD)
        status_combo = ttk.Combobox(field_frame, values=["planned", "ongoing", "completed", "cancelled"],
                                     font=FONT_TEXT, width=20, state="readonly")
        status_combo.grid(row=row, column=1, sticky="w", pady=SMALL_PAD, padx=SMALL_PAD)
        status_combo.set("planned")
        row += 1

        field_frame.columnconfigure(1, weight=1)

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Activity name is required.")
                return
            desc = desc_text.get("1.0", tk.END).strip()
            start = start_date.get_date().strftime("%Y-%m-%d")
            end = end_date.get_date().strftime("%Y-%m-%d")
            budget_str = budget_entry.get().strip()
            if not budget_str:
                budget_str = "0"
            try:
                budget = float(budget_str)
            except:
                messagebox.showerror("Error", "Budget must be a number.")
                return
            status = status_combo.get()
            db = DatabaseManager()
            db.execute_query(
                "INSERT INTO committee_activities (committee_id, name, description, start_date, end_date, budget, status) VALUES (?,?,?,?,?,?,?)",
                (self.committee_id, name, desc, start, end, budget, status)
            )
            win.destroy()
            self.load_activities()
            show_toast(self.win, "Activity added")

        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(pady=PAD)
        tk.Button(btn_frame, text="Save", bg=COLORS["accent"], fg="white",
                  command=save).pack(side="left", padx=SMALL_PAD)
        tk.Button(btn_frame, text="Cancel", bg=COLORS["gray"], fg="white",
                  command=win.destroy).pack(side="left", padx=SMALL_PAD)

    def delete_activity(self):
        selected = self.activities_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select an activity to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected activity? This will also delete all expenses for this activity."):
            return
        db = DatabaseManager()
        for item in selected:
            act_id = self.activities_tree.item(item)['values'][0]
            db.execute_query("DELETE FROM committee_expenses WHERE activity_id=?", (act_id,))
            db.execute_query("DELETE FROM committee_activities WHERE id=?", (act_id,))
        self.load_activities()
        self.load_expenses()
        show_toast(self.win, "Activity(s) deleted")

    # ---------- Expenses Tab ----------
    def setup_expenses_tab(self):
        toolbar = tk.Frame(self.expenses_frame, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=PAD, pady=SMALL_PAD)

        add_btn = tk.Button(toolbar, text="➕ Add Expense", bg=COLORS["accent"], fg="white",
                            font=FONT_TEXT, command=self.add_expense)
        add_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(add_btn, COLORS["accent"], COLORS["accent_light"])

        delete_btn = tk.Button(toolbar, text="🗑️ Delete Selected", bg=COLORS["gray"], fg="white",
                               font=FONT_TEXT, command=self.delete_expense)
        delete_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(delete_btn, COLORS["gray"], COLORS["gray_light"])

        export_btn = tk.Button(toolbar, text="📥 Export CSV", bg=COLORS["green"], fg="white",
                               font=FONT_TEXT, command=self.export_expenses_csv)
        export_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(export_btn, COLORS["green"], COLORS["green_light"])

        tree_frame = tk.Frame(self.expenses_frame, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=SMALL_PAD)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Date", "Amount", "Description", "Activity")
        self.expenses_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.expenses_tree.yview)
        hsb.config(command=self.expenses_tree.xview)

        widths = [50, 100, 100, 300, 150]
        for col, w in zip(columns, widths):
            self.expenses_tree.heading(col, text=col)
            self.expenses_tree.column(col, width=w, minwidth=50, stretch=False)

        self.expenses_tree.pack(fill="both", expand=True)
        self.load_expenses()

    def load_expenses(self):
        for row in self.expenses_tree.get_children():
            self.expenses_tree.delete(row)
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT e.id, e.expense_date, e.amount, e.description, a.name
            FROM committee_expenses e
            LEFT JOIN committee_activities a ON e.activity_id = a.id
            WHERE a.committee_id = ?
            ORDER BY e.expense_date DESC
        """, (self.committee_id,))
        for r in rows:
            self.expenses_tree.insert("", tk.END, values=r)
        self.load_stats()

    def export_expenses_csv(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Expenses",
            initialfile=f"committee_{self.committee_id}_expenses.csv"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Amount", "Description", "Activity"])
                for row in self.expenses_tree.get_children():
                    values = self.expenses_tree.item(row)['values'][1:]
                    writer.writerow(values)
            show_toast(self.win, "Expenses exported")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export: {e}")

    def add_expense(self):
        from tkcalendar import DateEntry
        db = DatabaseManager()
        activities = db.fetch_all("SELECT id, name FROM committee_activities WHERE committee_id=? ORDER BY name", (self.committee_id,))
        activity_dict = {name: aid for aid, name in activities}
        activity_names = list(activity_dict.keys())

        win = tk.Toplevel(self.win)
        win.title("Add Expense")
        win.geometry("500x400")
        win.configure(bg=COLORS["bg"])
        win.transient(self.win)
        win.grab_set()

        card = tk.Frame(win, bg="white", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        field_frame = tk.Frame(card, bg="white")
        field_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        tk.Label(field_frame, text="Activity:", bg="white", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=SMALL_PAD)
        activity_combo = ttk.Combobox(field_frame, values=activity_names, font=FONT_TEXT, width=35, state="readonly")
        activity_combo.grid(row=0, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="w")
        if activity_names:
            activity_combo.set(activity_names[0])

        tk.Label(field_frame, text="Date:", bg="white", font=FONT_TEXT).grid(row=1, column=0, sticky="w", pady=SMALL_PAD)
        date_entry = DateEntry(field_frame, width=12, background=COLORS["accent"], foreground='white',
                               borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        date_entry.grid(row=1, column=1, sticky="w", pady=SMALL_PAD, padx=SMALL_PAD)

        tk.Label(field_frame, text="Amount (₵):", bg="white", font=FONT_TEXT).grid(row=2, column=0, sticky="w", pady=SMALL_PAD)
        amount_entry = tk.Entry(field_frame, font=FONT_TEXT, width=20, bg="#f9f9f9")
        amount_entry.grid(row=2, column=1, sticky="w", pady=SMALL_PAD, padx=SMALL_PAD)

        tk.Label(field_frame, text="Description:", bg="white", font=FONT_TEXT).grid(row=3, column=0, sticky="w", pady=SMALL_PAD)
        desc_entry = tk.Entry(field_frame, font=FONT_TEXT, width=40, bg="#f9f9f9")
        desc_entry.grid(row=3, column=1, pady=SMALL_PAD, padx=SMALL_PAD, sticky="ew")

        field_frame.columnconfigure(1, weight=1)

        def save():
            act_name = activity_combo.get()
            if not act_name:
                messagebox.showerror("Error", "Select an activity.")
                return
            activity_id = activity_dict[act_name]
            date = date_entry.get_date().strftime("%Y-%m-%d")
            amount_str = amount_entry.get().strip()
            if not amount_str:
                messagebox.showerror("Error", "Enter amount.")
                return
            try:
                amount = float(amount_str)
            except:
                messagebox.showerror("Error", "Amount must be a number.")
                return
            desc = desc_entry.get().strip()
            db.execute_query(
                "INSERT INTO committee_expenses (activity_id, amount, expense_date, description) VALUES (?,?,?,?)",
                (activity_id, amount, date, desc)
            )
            win.destroy()
            self.load_expenses()
            show_toast(self.win, "Expense added")

        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(pady=PAD)
        tk.Button(btn_frame, text="Save", bg=COLORS["accent"], fg="white",
                  command=save).pack(side="left", padx=SMALL_PAD)
        tk.Button(btn_frame, text="Cancel", bg=COLORS["gray"], fg="white",
                  command=win.destroy).pack(side="left", padx=SMALL_PAD)

    def delete_expense(self):
        selected = self.expenses_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select an expense to delete.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected expense?"):
            return
        db = DatabaseManager()
        for item in selected:
            exp_id = self.expenses_tree.item(item)['values'][0]
            db.execute_query("DELETE FROM committee_expenses WHERE id=?", (exp_id,))
        self.load_expenses()
        show_toast(self.win, "Expense(s) deleted")

    def print_full_report(self):
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save Committee Report as PDF",
            initialfile=f"Committee_{self.committee_id}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        if not file_path:
            return
        try:
            doc = SimpleDocTemplate(file_path, pagesize=landscape(A4),
                                    rightMargin=10*mm, leftMargin=10*mm,
                                    topMargin=15*mm, bottomMargin=10*mm)
            elements = []
            styles = getSampleStyleSheet()

            title = f"Committee Report: {self.win.title().replace('Committee: ', '')}"
            elements.append(Paragraph(title, styles['Title']))
            elements.append(Spacer(1, 5*mm))

            db = DatabaseManager()
            member_count = db.fetch_one("SELECT COUNT(*) FROM committee_members WHERE committee_id=?", (self.committee_id,))[0] or 0
            activity_count = db.fetch_one("SELECT COUNT(*) FROM committee_activities WHERE committee_id=?", (self.committee_id,))[0] or 0
            total_budget = db.fetch_one("SELECT SUM(budget) FROM committee_activities WHERE committee_id=?", (self.committee_id,))[0] or 0
            total_expenses = db.fetch_one("""
                SELECT SUM(e.amount) FROM committee_expenses e
                JOIN committee_activities a ON e.activity_id = a.id
                WHERE a.committee_id = ?
            """, (self.committee_id,))[0] or 0

            summary_data = [
                ["Total Members", str(member_count)],
                ["Total Activities", str(activity_count)],
                ["Total Budget", f"GHS {total_budget:,.2f}"],
                ["Total Expenses", f"GHS {total_expenses:,.2f}"],
                ["Balance", f"GHS {total_budget - total_expenses:,.2f}"]
            ]
            summary_table = Table(summary_data)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLORS["accent"])),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 10*mm))

            # Members
            elements.append(Paragraph("Members", styles['Heading2']))
            members_data = [["Member ID", "Full Name", "Role", "Joined"]]
            for row in self.members_tree.get_children():
                values = self.members_tree.item(row)['values'][1:-1]
                members_data.append(values)
            members_table = Table(members_data, repeatRows=1)
            members_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLORS["accent"])),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(members_table)
            elements.append(Spacer(1, 5*mm))

            # Meetings
            elements.append(Paragraph("Meetings", styles['Heading2']))
            meetings_data = [["Date", "Agenda", "Location"]]
            for row in self.meetings_tree.get_children():
                values = self.meetings_tree.item(row)['values'][1:]
                meetings_data.append(values)
            meetings_table = Table(meetings_data, repeatRows=1)
            meetings_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLORS["accent"])),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(meetings_table)
            elements.append(Spacer(1, 5*mm))

            # Activities
            elements.append(Paragraph("Activities", styles['Heading2']))
            activities_data = [["Name", "Start", "End", "Budget", "Status"]]
            for row in self.activities_tree.get_children():
                values = self.activities_tree.item(row)['values'][1:-1]
                activities_data.append(values)
            activities_table = Table(activities_data, repeatRows=1)
            activities_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLORS["accent"])),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(activities_table)
            elements.append(Spacer(1, 5*mm))

            # Expenses
            elements.append(Paragraph("Expenses", styles['Heading2']))
            expenses_data = [["Date", "Amount", "Description", "Activity"]]
            for row in self.expenses_tree.get_children():
                values = self.expenses_tree.item(row)['values'][1:]
                expenses_data.append(values)
            expenses_table = Table(expenses_data, repeatRows=1)
            expenses_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(COLORS["accent"])),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            elements.append(expenses_table)

            doc.build(elements)
            show_toast(self.win, "PDF report generated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {e}")
    pass


# ================== MANAGE ROLES DIALOG ==================
class ManageRolesDialog:
    def __init__(self, parent, committee_id):
        self.win = tk.Toplevel(parent)
        self.win.title("Manage Committee Roles")
        self.win.geometry("600x450")
        self.win.minsize(500, 400)
        self.win.configure(bg=COLORS["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        self.committee_id = committee_id

        # Title
        title_frame = tk.Frame(self.win, bg=COLORS["accent"], height=40)
        title_frame.pack(fill="x")
        tk.Label(title_frame, text="Committee Roles", font=("Helvetica", 14, "bold"),
                 bg=COLORS["accent"], fg="white").pack(pady=8)

        # Toolbar
        toolbar = tk.Frame(self.win, bg=COLORS["bg"])
        toolbar.pack(fill="x", padx=PAD, pady=SMALL_PAD)

        add_btn = tk.Button(toolbar, text="➕ Add Role", bg=COLORS["accent"], fg="white",
                            font=FONT_TEXT, command=self.add_role)
        add_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(add_btn, COLORS["accent"], COLORS["accent_light"])
        ToolTip(add_btn, "Add a new role to the list")

        edit_btn = tk.Button(toolbar, text="✏️ Edit Selected", bg=COLORS["accent"], fg="white",
                             font=FONT_TEXT, command=self.edit_role)
        edit_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(edit_btn, COLORS["accent"], COLORS["accent_light"])
        ToolTip(edit_btn, "Edit the selected role")

        delete_btn = tk.Button(toolbar, text="🗑️ Delete Selected", bg=COLORS["red"], fg="white",
                               font=FONT_TEXT, command=self.delete_role)
        delete_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(delete_btn, COLORS["red"], COLORS["red_light"])
        ToolTip(delete_btn, "Delete the selected role (existing members keep the role name)")

        # Treeview frame
        tree_frame = tk.Frame(self.win, bg=COLORS["bg"])
        tree_frame.pack(fill="both", expand=True, padx=PAD, pady=SMALL_PAD)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Role Name")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        self.tree.heading("ID", text="ID")
        self.tree.heading("Role Name", text="Role Name")
        self.tree.column("ID", width=50, stretch=False)
        self.tree.column("Role Name", width=400, stretch=True)

        self.tree.pack(fill="both", expand=True)

        # Close button at bottom
        close_btn = tk.Button(self.win, text="Close", bg=COLORS["gray"], fg="white",
                              font=FONT_TEXT, command=self.win.destroy)
        close_btn.pack(pady=PAD)
        self._add_hover(close_btn, COLORS["gray"], COLORS["gray_light"])

        self.load_roles()

    def _add_hover(self, button, normal_bg, hover_bg):
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=normal_bg))

    def load_roles(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        db = DatabaseManager()
        rows = db.fetch_all("SELECT id, name FROM committee_roles WHERE committee_id=? ORDER BY name", (self.committee_id,))
        if not rows:
            self.tree.insert("", tk.END, values=("", "No roles defined yet"))
            self.tree.item(self.tree.get_children()[0], tags=("placeholder",))
            self.tree.tag_configure("placeholder", foreground="gray")
        else:
            for r in rows:
                self.tree.insert("", tk.END, values=r)

    def add_role(self):
        self._role_form("Add Role")

    def edit_role(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a role to edit.")
            return
        item = self.tree.item(selected[0])
        role_id = item['values'][0]
        old_name = item['values'][1]
        if role_id == "":
            return
        self._role_form("Edit Role", role_id, old_name)

    def delete_role(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a role to delete.")
            return
        item = self.tree.item(selected[0])
        role_id = item['values'][0]
        if role_id == "":
            return
        if not messagebox.askyesno("Confirm", "Delete selected role? Existing members will keep the role name."):
            return
        db = DatabaseManager()
        db.execute_query("DELETE FROM committee_roles WHERE id=? AND committee_id=?", (role_id, self.committee_id))
        show_toast(self.win, "Role deleted")
        self.load_roles()

    def _role_form(self, title, role_id=None, old_name=""):
        dialog = tk.Toplevel(self.win)
        dialog.title(title)
        dialog.geometry("400x200")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.win)
        dialog.grab_set()
        dialog.resizable(False, False)

        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        card = tk.Frame(dialog, bg="white", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        tk.Label(card, text="Role Name:", bg="white", font=FONT_TEXT).pack(pady=(PAD, SMALL_PAD))
        entry = tk.Entry(card, font=FONT_TEXT, width=30, bg="#f9f9f9")
        entry.pack(pady=SMALL_PAD, padx=PAD)
        if old_name:
            entry.insert(0, old_name)

        def save():
            new_name = entry.get().strip()
            if not new_name:
                messagebox.showerror("Error", "Role name cannot be empty.")
                return
            db = DatabaseManager()
            if role_id:
                try:
                    db.execute_query(
                        "UPDATE committee_roles SET name=? WHERE id=? AND committee_id=?",
                        (new_name, role_id, self.committee_id)
                    )
                    show_toast(dialog, "Role updated")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not update: {e}")
                    return
            else:
                try:
                    db.execute_query(
                        "INSERT INTO committee_roles (committee_id, name) VALUES (?,?)",
                        (self.committee_id, new_name)
                    )
                    show_toast(dialog, "Role added")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not add: {e}")
                    return
            dialog.destroy()
            self.load_roles()

        btn_frame = tk.Frame(card, bg="white")
        btn_frame.pack(pady=PAD)
        tk.Button(btn_frame, text="Save", bg=COLORS["accent"], fg="white",
                  font=FONT_TEXT, width=10, command=save).pack(side="left", padx=SMALL_PAD)
        tk.Button(btn_frame, text="Cancel", bg=COLORS["gray"], fg="white",
                  font=FONT_TEXT, width=10, command=dialog.destroy).pack(side="left", padx=SMALL_PAD)

    pass


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1300x700")
    app = CommitteesModule(root)
    root.mainloop()