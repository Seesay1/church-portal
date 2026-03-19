import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from datetime import datetime
import csv
import os
import subprocess
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

class ToolTip:
    """Simple tooltip class."""
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

class ReportsModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")

        # Default column widths (standard and compact)
        self.column_widths_standard = {
            "Members": [100, 180, 60, 100, 180, 120, 120, 120],
            "Attendance": [100, 180, 120, 80],
            "Finance": [80, 100, 180, 100, 100, 100, 100],
            "Events": [150, 100, 80, 150, 120]
        }
        self.column_widths_compact = {
            "Members": [80, 140, 50, 80, 140, 100, 100, 100],
            "Attendance": [80, 140, 100, 70],
            "Finance": [70, 80, 140, 80, 80, 80, 80],
            "Events": [120, 80, 70, 120, 100]
        }
        self.current_width_mode = "standard"

        # Create Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Generate Report
        self.generate_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.generate_frame, text="📊 Generate Report")

        # Tab 2: Saved Reports
        self.saved_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.saved_frame, text="📁 Saved Reports")

        self.setup_generate_tab()
        self.setup_saved_tab()

        self.load_filters()
        self.load_saved_reports()

    # ================== GENERATE TAB ==================
    def setup_generate_tab(self):
        # Top toolbar
        toolbar = tk.Frame(self.generate_frame, bg="#e8f1ff")
        toolbar.pack(side="top", fill="x", padx=10, pady=5)

        # Row 1: Report type, Branch, Group
        row1 = tk.Frame(toolbar, bg="#e8f1ff")
        row1.pack(fill="x", pady=2)

        tk.Label(row1, text="Report Type:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.report_type = ttk.Combobox(row1, values=["Members", "Attendance", "Finance", "Events"],
                                        font=FONT_TEXT, state="readonly", width=15)
        self.report_type.pack(side="left", padx=5)
        self.report_type.bind("<<ComboboxSelected>>", self.on_report_type_change)

        tk.Label(row1, text="Branch:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=10)
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(row1, textvariable=self.branch_var,
                                        values=["All"], state="readonly", width=15)
        self.branch_combo.pack(side="left", padx=5)

        tk.Label(row1, text="Group:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=10)
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(row1, textvariable=self.group_var,
                                        values=["All"], state="readonly", width=15)
        self.group_combo.pack(side="left", padx=5)

        # Row 2: Date range and all action buttons (packed left)
        row2 = tk.Frame(toolbar, bg="#e8f1ff")
        row2.pack(fill="x", pady=5)

        tk.Label(row2, text="From:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.date_from = DateEntry(row2, width=10, background='blue', foreground='white',
                                   borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.date_from.pack(side="left", padx=2)
        self.date_from.set_date(datetime.now().replace(day=1))

        tk.Label(row2, text="To:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.date_to = DateEntry(row2, width=10, background='blue', foreground='white',
                                 borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.date_to.pack(side="left", padx=2)
        self.date_to.set_date(datetime.now())

        # Buttons (all left-aligned)
        self.gen_btn = tk.Button(row2, text="📄 Generate", bg="#1f4fa3", fg="#fff",
                                 font=("Helvetica", 11, "bold"), width=12, command=self.generate_report)
        self.gen_btn.pack(side="left", padx=5)
        ToolTip(self.gen_btn, "Generate report with current filters")

        self.csv_btn = tk.Button(row2, text="💾 CSV", bg="#1f4fa3", fg="#fff",
                                 font=FONT_TEXT, width=8, command=self.export_csv)
        self.csv_btn.pack(side="left", padx=2)
        ToolTip(self.csv_btn, "Export to CSV file")

        self.pdf_btn = tk.Button(row2, text="📑 PDF", bg="#d62828", fg="#fff",
                                 font=FONT_TEXT, width=8, command=self.export_pdf)
        self.pdf_btn.pack(side="left", padx=2)
        ToolTip(self.pdf_btn, "Export to PDF file")

        self.compact_btn = tk.Button(row2, text="🔍 Compact", bg="#1f4fa3", fg="#fff",
                                     font=FONT_TEXT, width=10, command=self.toggle_compact_view)
        self.compact_btn.pack(side="left", padx=2)
        ToolTip(self.compact_btn, "Switch between standard and compact column widths")

        self.reset_cols_btn = tk.Button(row2, text="↺ Reset", bg="#d62828", fg="#fff",
                                        font=FONT_TEXT, width=8, command=self.reset_column_widths)
        self.reset_cols_btn.pack(side="left", padx=2)
        ToolTip(self.reset_cols_btn, "Restore default column widths")

        self.clear_btn = tk.Button(row2, text="🗑️ Clear", bg="#333", fg="#fff",
                                   font=FONT_TEXT, width=10, command=self.clear_table)
        self.clear_btn.pack(side="left", padx=2)
        ToolTip(self.clear_btn, "Clear current table data")

        # Summary label (below toolbar)
        self.summary_label = tk.Label(self.generate_frame, text="", bg="#e8f1ff",
                                      font=("Helvetica", 10, "bold"), fg="#1f4fa3")
        self.summary_label.pack(pady=5)

        # Treeview frame with scrollbars
        tree_frame = tk.Frame(self.generate_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        self.tree = ttk.Treeview(tree_frame, show="headings",
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)
        self.tree.pack(fill="both", expand=True)

        # Bind mousewheel only to treeview to prevent scrolling the whole window
        def _on_tree_mousewheel(event):
            self.tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"  # stop event propagation
        self.tree.bind("<MouseWheel>", _on_tree_mousewheel)

        self.current_data = []
        self.current_report_type = None

    def clear_table(self):
        """Clear all rows from the treeview and reset summary."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.current_data = []
        self.summary_label.config(text="")

    def toggle_compact_view(self):
        if not self.current_report_type:
            return
        if self.current_width_mode == "standard":
            widths = self.column_widths_compact.get(self.current_report_type, [])
            self.current_width_mode = "compact"
            self.compact_btn.config(text="🔍 Standard")
        else:
            widths = self.column_widths_standard.get(self.current_report_type, [])
            self.current_width_mode = "standard"
            self.compact_btn.config(text="🔍 Compact")
        cols = self.tree["columns"]
        for i, col in enumerate(cols):
            if i < len(widths):
                self.tree.column(col, width=widths[i])

    def reset_column_widths(self):
        if not self.current_report_type:
            return
        self.current_width_mode = "standard"
        self.compact_btn.config(text="🔍 Compact")
        widths = self.column_widths_standard.get(self.current_report_type, [])
        cols = self.tree["columns"]
        for i, col in enumerate(cols):
            if i < len(widths):
                self.tree.column(col, width=widths[i])

    def load_filters(self):
        db = DatabaseManager()
        branches = [r[0] for r in db.fetch_all("SELECT name FROM branches ORDER BY name")]
        groups = [r[0] for r in db.fetch_all("SELECT name FROM groups ORDER BY name")]
        self.branch_combo['values'] = ["All"] + branches
        self.group_combo['values'] = ["All"] + groups
        self.branch_var.set("All")
        self.group_var.set("All")

    def on_report_type_change(self, event=None):
        rt = self.report_type.get()
        # Enable/disable filters based on report type
        if rt in ["Members", "Attendance", "Finance"]:
            self.branch_combo.config(state="readonly")
            self.group_combo.config(state="readonly")
        else:
            self.branch_combo.config(state="disabled")
            self.group_combo.config(state="disabled")

        if rt in ["Attendance", "Finance", "Events"]:
            self.date_from.config(state="normal")
            self.date_to.config(state="normal")
        else:
            self.date_from.config(state="disabled")
            self.date_to.config(state="disabled")

    def generate_report(self):
        rt = self.report_type.get()
        if not rt:
            messagebox.showerror("Error", "Please select a report type.")
            return

        branch = self.branch_var.get() if self.branch_var.get() != "All" else None
        group = self.group_var.get() if self.group_var.get() != "All" else None
        date_from = self.date_from.get_date().strftime("%Y-%m-%d") if self.date_from.cget('state') != 'disabled' else None
        date_to = self.date_to.get_date().strftime("%Y-%m-%d") if self.date_to.cget('state') != 'disabled' else None

        db = DatabaseManager()

        for row in self.tree.get_children():
            self.tree.delete(row)

        try:
            if rt == "Members":
                self.generate_members_report(db, branch, group)
            elif rt == "Attendance":
                self.generate_attendance_report(db, branch, group, date_from, date_to)
            elif rt == "Finance":
                self.generate_finance_report(db, branch, group, date_from, date_to)
            elif rt == "Events":
                self.generate_events_report(db, date_from, date_to)
            self.current_report_type = rt
            self.current_width_mode = "standard"
            self.compact_btn.config(text="🔍 Compact")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")

    def set_tree_columns(self, columns, widths):
        self.tree["columns"] = columns
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=w, stretch=False)

    def generate_members_report(self, db, branch, group):
        cols = ("Member ID", "Full Name", "Gender", "Phone", "Email", "Branch", "Group", "Department")
        widths = self.column_widths_standard["Members"]
        self.set_tree_columns(cols, widths)

        query = """
            SELECT m.member_id, m.full_name, m.gender, m.phone, m.email,
                   b.name, g.name, d.name
            FROM members m
            LEFT JOIN branches b ON m.branch_id = b.id
            LEFT JOIN groups g ON m.group_id = g.id
            LEFT JOIN departments d ON m.department_id = d.id
            WHERE 1=1
        """
        params = []
        if branch:
            query += " AND b.name = ?"
            params.append(branch)
        if group:
            query += " AND g.name = ?"
            params.append(group)
        query += " ORDER BY m.full_name"

        rows = db.fetch_all(query, params)
        self.current_data = [[str(x) if x is not None else "" for x in r] for r in rows]
        for r in rows:
            self.tree.insert("", tk.END, values=r)

        self.summary_label.config(text=f"Total Members: {len(rows)}")

    def generate_attendance_report(self, db, branch, group, date_from, date_to):
        cols = ("Member ID", "Full Name", "Date", "Present")
        widths = self.column_widths_standard["Attendance"]
        self.set_tree_columns(cols, widths)

        query = """
            SELECT m.member_id, m.full_name, a.date, a.present
            FROM attendance a
            LEFT JOIN members m ON a.member_id = m.id
            LEFT JOIN branches b ON a.branch_id = b.id
            LEFT JOIN groups g ON a.group_id = g.id
            WHERE 1=1
        """
        params = []
        if branch:
            query += " AND b.name = ?"
            params.append(branch)
        if group:
            query += " AND g.name = ?"
            params.append(group)
        if date_from and date_to:
            query += " AND a.date BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        query += " ORDER BY a.date DESC"

        rows = db.fetch_all(query, params)
        self.current_data = []
        for r in rows:
            status = "Yes" if r[3] == 1 else "No"
            self.tree.insert("", tk.END, values=(r[0], r[1], r[2], status))
            self.current_data.append([str(r[0]), str(r[1]), str(r[2]), status])

        present = sum(1 for r in rows if r[3] == 1)
        absent = len(rows) - present
        self.summary_label.config(text=f"Total Records: {len(rows)} | Present: {present} | Absent: {absent}")

    def generate_finance_report(self, db, branch, group, date_from, date_to):
        cols = ("Type", "Member ID", "Full Name", "Branch", "Group", "Amount", "Date")
        widths = self.column_widths_standard["Finance"]
        self.set_tree_columns(cols, widths)

        query = """
            SELECT f.type, m.member_id, m.full_name, b.name, g.name, f.amount, f.date
            FROM financial_records f
            LEFT JOIN members m ON f.member_id = m.id
            LEFT JOIN branches b ON f.branch_id = b.id
            LEFT JOIN groups g ON f.group_id = g.id
            WHERE 1=1
        """
        params = []
        if branch:
            query += " AND b.name = ?"
            params.append(branch)
        if group:
            query += " AND g.name = ?"
            params.append(group)
        if date_from and date_to:
            query += " AND f.date BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        query += " ORDER BY f.date DESC"

        rows = db.fetch_all(query, params)
        self.current_data = [[str(x) if x is not None else "" for x in r] for r in rows]
        for r in rows:
            self.tree.insert("", tk.END, values=r)

        total_income = sum(float(r[5]) for r in rows if r[0] in ["Tithe", "Offering", "Contribution"])
        total_expense = sum(float(r[5]) for r in rows if r[0] == "Expense")
        self.summary_label.config(text=f"Income: {total_income:.2f} | Expense: {total_expense:.2f} | Balance: {total_income - total_expense:.2f}")

    def generate_events_report(self, db, date_from, date_to):
        cols = ("Event Name", "Date", "Time", "Location", "Branch/Group")
        widths = self.column_widths_standard["Events"]
        self.set_tree_columns(cols, widths)

        query = "SELECT name, date, time, location, branch_group FROM events"
        params = []
        if date_from and date_to:
            query += " WHERE date BETWEEN ? AND ?"
            params.extend([date_from, date_to])
        query += " ORDER BY date ASC"

        rows = db.fetch_all(query, params)
        self.current_data = [[str(x) if x is not None else "" for x in r] for r in rows]
        for r in rows:
            self.tree.insert("", tk.END, values=r)

        self.summary_label.config(text=f"Total Events: {len(rows)}")

    # ---------- Export ----------
    def export_csv(self):
        if not self.current_data:
            messagebox.showwarning("No Data", "Generate a report first.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Report as CSV",
            initialfile=f"{self.report_type.get()}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if not file_path:
            return
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(self.tree["columns"])
                writer.writerows(self.current_data)
            self.save_to_database(os.path.basename(file_path), self.report_type.get(), file_path)
            messagebox.showinfo("Success", f"Report saved to {file_path}")
            self.load_saved_reports()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save CSV: {e}")

    def export_pdf(self):
        if not self.current_data:
            messagebox.showwarning("No Data", "Generate a report first.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save Report as PDF",
            initialfile=f"{self.report_type.get()}_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        if not file_path:
            return
        try:
            doc = SimpleDocTemplate(file_path, pagesize=landscape(A4),
                                    rightMargin=10*mm, leftMargin=10*mm,
                                    topMargin=15*mm, bottomMargin=10*mm)
            elements = []

            styles = getSampleStyleSheet()
            title = f"{self.report_type.get()} Report"
            if self.date_from.cget('state') != 'disabled':
                title += f" ({self.date_from.get_date()} to {self.date_to.get_date()})"
            elements.append(Paragraph(title, styles['Title']))
            elements.append(Spacer(1, 5*mm))

            table_data = [list(self.tree["columns"])] + self.current_data
            for i in range(len(table_data)):
                for j in range(len(table_data[i])):
                    if table_data[i][j] is None:
                        table_data[i][j] = ""
                    else:
                        table_data[i][j] = str(table_data[i][j])

            table = Table(table_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1f4fa3")),
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
            self.save_to_database(os.path.basename(file_path), self.report_type.get(), file_path)
            messagebox.showinfo("Success", f"Report saved to {file_path}")
            self.load_saved_reports()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save PDF: {e}")

    # ================== SAVED REPORTS TAB ==================
    def setup_saved_tab(self):
        # Toolbar
        toolbar = tk.Frame(self.saved_frame, bg="#e8f1ff")
        toolbar.pack(fill="x", padx=10, pady=10)

        tk.Button(toolbar, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.load_saved_reports).pack(side="left", padx=5)
        tk.Button(toolbar, text="🗑️ Delete Selected", bg="#333", fg="#fff",
                  font=FONT_TEXT, command=self.delete_saved_report).pack(side="left", padx=5)
        tk.Button(toolbar, text="📂 Open Folder", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.open_saved_folder).pack(side="left", padx=5)

        tk.Label(toolbar, text="Filter Type:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.saved_filter = ttk.Combobox(toolbar, values=["All", "Members", "Attendance", "Finance", "Events"],
                                          state="readonly", width=15)
        self.saved_filter.pack(side="left", padx=5)
        self.saved_filter.set("All")
        self.saved_filter.bind("<<ComboboxSelected>>", lambda e: self.filter_saved_reports())

        # Treeview frame
        tree_frame = tk.Frame(self.saved_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Report Name", "Type", "Date Generated", "File Path", "DB_ID")
        self.saved_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                        yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.saved_tree.yview)
        hsb.config(command=self.saved_tree.xview)

        widths = [50, 200, 100, 150, 300, 0]
        for col, w in zip(columns, widths):
            self.saved_tree.heading(col, text=col)
            self.saved_tree.column(col, width=w, minwidth=20 if w>0 else 0, stretch=False)

        self.saved_tree.pack(fill="both", expand=True)
        self.saved_tree.bind("<Double-1>", self.open_saved_report)

        # Bind mousewheel to saved treeview as well
        def _on_saved_mousewheel(event):
            self.saved_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        self.saved_tree.bind("<MouseWheel>", _on_saved_mousewheel)

        self.all_saved = []
        self.load_saved_reports()

    def load_saved_reports(self):
        db = DatabaseManager()
        db.execute_query("""
            CREATE TABLE IF NOT EXISTS saved_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_name TEXT,
                report_type TEXT,
                file_path TEXT,
                date_generated TEXT
            )
        """)

        for row in self.saved_tree.get_children():
            self.saved_tree.delete(row)
        self.all_saved.clear()

        rows = db.fetch_all("SELECT id, report_name, report_type, date_generated, file_path FROM saved_reports ORDER BY date_generated DESC")
        for r in rows:
            item_id = self.saved_tree.insert("", tk.END, values=(r[0], r[1], r[2], r[3], r[4], r[0]))
            self.all_saved.append((item_id, r[2]))

        self.filter_saved_reports()

    def filter_saved_reports(self):
        filter_type = self.saved_filter.get()
        for item_id, typ in self.all_saved:
            if filter_type != "All" and typ != filter_type:
                self.saved_tree.detach(item_id)
            else:
                self.saved_tree.reattach(item_id, "", "end")

    def delete_saved_report(self):
        selected = self.saved_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a saved report to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected saved report? (File will not be removed)"):
            return
        db = DatabaseManager()
        for item in selected:
            report_id = self.saved_tree.item(item)['values'][5]
            db.execute_query("DELETE FROM saved_reports WHERE id = ?", (report_id,))
        self.load_saved_reports()
        self.saved_tree.selection_remove(self.saved_tree.selection())
        messagebox.showinfo("Success", "Saved report entry deleted.")

    def open_saved_report(self, event):
        selected = self.saved_tree.selection()
        if not selected:
            return
        file_path = self.saved_tree.item(selected[0])['values'][4]
        if file_path and os.path.exists(file_path):
            os.startfile(file_path)
        else:
            messagebox.showerror("Error", "File not found.")

    def open_saved_folder(self):
        selected = self.saved_tree.selection()
        if selected:
            file_path = self.saved_tree.item(selected[0])['values'][4]
            folder = os.path.dirname(file_path) if file_path else os.path.dirname(os.path.abspath(__file__))
        else:
            folder = os.path.dirname(os.path.abspath(__file__))
        subprocess.Popen(f'explorer "{folder}"')

    def save_to_database(self, report_name, report_type, file_path):
        db = DatabaseManager()
        date_generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.execute_query(
            "INSERT INTO saved_reports (report_name, report_type, file_path, date_generated) VALUES (?,?,?,?)",
            (report_name, report_type, file_path, date_generated)
        )

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1400x700")
    root.minsize(1300, 600)
    app = ReportsModule(root)
    root.mainloop()