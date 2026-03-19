import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkcalendar import DateEntry
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os
from database import DatabaseManager

try:
    from config import FONT_TEXT, LOGO_PATH, CHURCH_NAME
except ImportError:
    FONT_TEXT = ("Helvetica", 10)
    LOGO_PATH = "logo.png"
    CHURCH_NAME = "PCG Mt. Zion Congregation"

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

class CertificatesModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")
        self.user_id = user_id
        self.branch_id = branch_id

        # Create Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Generate Certificate
        self.generate_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.generate_frame, text="📜 Generate Certificate")

        # Tab 2: History
        self.history_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.history_frame, text="📋 History")

        # Tab 3: Statistics
        self.stats_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        # Tab 4: Requests
        self.requests_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.requests_frame, text="📋 Requests")

        self.setup_generate_tab()
        self.setup_history_tab()
        self.setup_stats_tab()
        self.setup_requests_tab()

        self.load_member_list()

    # ================== GENERATE TAB ==================
    def setup_generate_tab(self):
        # Top toolbar
        toolbar = tk.Frame(self.generate_frame, bg="#e8f1ff")
        toolbar.pack(side="top", fill="x", padx=10, pady=5)

        self.refresh_btn = tk.Button(toolbar, text="🔄 Refresh List", bg="#1f4fa3", fg="#fff",
                                     font=FONT_TEXT, command=self.load_member_list)
        self.refresh_btn.pack(side="left", padx=5)
        ToolTip(self.refresh_btn, "Refresh member list")

        self.clear_btn = tk.Button(toolbar, text="🗑️ Clear Form", bg="#333", fg="#fff",
                                   font=FONT_TEXT, command=self.clear_form)
        self.clear_btn.pack(side="left", padx=5)
        ToolTip(self.clear_btn, "Clear all fields")

        self.gen_btn = tk.Button(toolbar, text="📄 Generate Certificate", bg="#d62828", fg="#fff",
                                 font=("Helvetica", 11, "bold"), command=self.generate_certificate)
        self.gen_btn.pack(side="left", padx=5)
        ToolTip(self.gen_btn, "Generate PDF certificate")

        # Main content area with PanedWindow
        paned = ttk.PanedWindow(self.generate_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # Left pane (member selection and form)
        left_pane = tk.Frame(paned, bg="#e8f1ff")
        paned.add(left_pane, weight=1)

        # Member selection
        member_frame = tk.LabelFrame(left_pane, text="Member Information", bg="#e8f1ff", font=FONT_TEXT, padx=10, pady=10)
        member_frame.pack(fill="x", pady=5)

        tk.Label(member_frame, text="Select Member:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.member_var = tk.StringVar()
        self.member_combo = ttk.Combobox(member_frame, textvariable=self.member_var, width=35, font=FONT_TEXT)
        self.member_combo.grid(row=0, column=1, pady=5, padx=5, sticky="w")
        self.member_combo.bind("<<ComboboxSelected>>", self.update_preview)

        # Certificate type
        type_frame = tk.LabelFrame(left_pane, text="Certificate Details", bg="#e8f1ff", font=FONT_TEXT, padx=10, pady=10)
        type_frame.pack(fill="x", pady=5)

        tk.Label(type_frame, text="Certificate Type:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.cert_type_combo = ttk.Combobox(type_frame, values=["Baptism", "Confirmation", "Membership", "Promotion", "Dedication"],
                                            font=FONT_TEXT, width=25, state="readonly")
        self.cert_type_combo.grid(row=0, column=1, sticky="w", pady=5, padx=5)
        self.cert_type_combo.bind("<<ComboboxSelected>>", self.on_cert_type_change)

        # Dynamic fields frame (inside type_frame)
        self.dynamic_frame = tk.Frame(type_frame, bg="#e8f1ff")
        self.dynamic_frame.grid(row=1, column=0, columnspan=2, pady=5, sticky="ew")

        # Default verse field
        tk.Label(self.dynamic_frame, text="Bible Verse:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=2)
        self.verse_entry = tk.Entry(self.dynamic_frame, font=FONT_TEXT, width=35)
        self.verse_entry.grid(row=0, column=1, pady=2, padx=5, sticky="w")

        # Right pane (preview)
        right_pane = tk.Frame(paned, bg="#e8f1ff")
        paned.add(right_pane, weight=1)

        # Preview Frame
        preview_frame = tk.LabelFrame(right_pane, text="Member Details Preview", bg="white", padx=10, pady=10)
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.preview_text = tk.Text(preview_frame, height=10, width=50, font=("Helvetica", 10), wrap="word")
        self.preview_text.pack(fill="both", expand=True)
        self.preview_text.config(state="disabled")

    def on_cert_type_change(self, event=None):
        """Show/hide extra fields based on certificate type."""
        # Clear dynamic frame (except verse row)
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()

        cert_type = self.cert_type_combo.get()

        # Verse field (always present)
        tk.Label(self.dynamic_frame, text="Bible Verse:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=2)
        self.verse_entry = tk.Entry(self.dynamic_frame, font=FONT_TEXT, width=35)
        self.verse_entry.grid(row=0, column=1, pady=2, padx=5, sticky="w")

        if cert_type == "Promotion":
            tk.Label(self.dynamic_frame, text="From Group:", bg="#e8f1ff", font=FONT_TEXT).grid(row=1, column=0, sticky="w", pady=2)
            self.from_group_entry = tk.Entry(self.dynamic_frame, font=FONT_TEXT, width=30)
            self.from_group_entry.grid(row=1, column=1, pady=2, padx=5, sticky="w")

            tk.Label(self.dynamic_frame, text="To Group:", bg="#e8f1ff", font=FONT_TEXT).grid(row=2, column=0, sticky="w", pady=2)
            self.to_group_entry = tk.Entry(self.dynamic_frame, font=FONT_TEXT, width=30)
            self.to_group_entry.grid(row=2, column=1, pady=2, padx=5, sticky="w")

            tk.Label(self.dynamic_frame, text="Promotion Date:", bg="#e8f1ff", font=FONT_TEXT).grid(row=3, column=0, sticky="w", pady=2)
            self.date_entry = DateEntry(self.dynamic_frame, width=15, background='blue', foreground='white',
                                        borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
            self.date_entry.grid(row=3, column=1, pady=2, padx=5, sticky="w")
            self.date_entry.set_date(datetime.now())

        elif cert_type == "Dedication":
            tk.Label(self.dynamic_frame, text="Dedication Date:", bg="#e8f1ff", font=FONT_TEXT).grid(row=1, column=0, sticky="w", pady=2)
            self.date_entry = DateEntry(self.dynamic_frame, width=15, background='blue', foreground='white',
                                        borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
            self.date_entry.grid(row=1, column=1, pady=2, padx=5, sticky="w")
            self.date_entry.set_date(datetime.now())

        # For other types, no extra fields

    def load_member_list(self):
        """Populate member combobox with full names and IDs."""
        db = DatabaseManager()
        members = db.fetch_all("SELECT member_id, full_name FROM members ORDER BY full_name")
        self.member_list = [f"{name} ({mid})" for mid, name in members if name and mid]
        self.member_combo['values'] = self.member_list
        if self.member_list:
            self.member_combo.set("")

    def update_preview(self, event=None):
        """Show member details in preview."""
        selection = self.member_var.get()
        if not selection:
            return
        member_id = selection.split('(')[-1].strip(')')
        db = DatabaseManager()
        member = db.fetch_one("""
            SELECT full_name, baptism_date, baptized_by, confirmation_date, confirmed_by 
            FROM members WHERE member_id=?
        """, (member_id,))
        if not member:
            return
        full_name, baptism_date, baptized_by, confirmation_date, confirmed_by = member
        details = f"Full Name: {full_name}\n"
        details += f"Baptism Date: {baptism_date or 'N/A'} by {baptized_by or 'N/A'}\n"
        details += f"Confirmation Date: {confirmation_date or 'N/A'} by {confirmed_by or 'N/A'}"
        self.preview_text.config(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.insert(1.0, details)
        self.preview_text.config(state="disabled")

    def clear_form(self):
        self.member_var.set("")
        self.cert_type_combo.set("")
        self.verse_entry.delete(0, tk.END)
        if hasattr(self, 'from_group_entry') and self.from_group_entry:
            self.from_group_entry.delete(0, tk.END)
        if hasattr(self, 'to_group_entry') and self.to_group_entry:
            self.to_group_entry.delete(0, tk.END)
        if hasattr(self, 'date_entry') and self.date_entry:
            self.date_entry.delete(0, tk.END)
        self.preview_text.config(state="normal")
        self.preview_text.delete(1.0, tk.END)
        self.preview_text.config(state="disabled")
        self.on_cert_type_change()  # reset dynamic fields

    def generate_certificate(self):
        selection = self.member_var.get()
        cert_type = self.cert_type_combo.get()
        verse = self.verse_entry.get().strip()

        if not selection or not cert_type:
            messagebox.showerror("Error", "Please select a member and certificate type.")
            return

        member_id = selection.split('(')[-1].strip(')')
        db = DatabaseManager()
        member = db.fetch_one("SELECT id, full_name, baptism_date, baptized_by, confirmation_date, confirmed_by FROM members WHERE member_id=?", (member_id,))
        if not member:
            messagebox.showerror("Error", "Member not found.")
            return

        mem_id, full_name, baptism_date, baptized_by, confirmation_date, confirmed_by = member

        extra_data = {}
        if cert_type == "Promotion":
            from_group = self.from_group_entry.get().strip() if hasattr(self, 'from_group_entry') else ""
            to_group = self.to_group_entry.get().strip() if hasattr(self, 'to_group_entry') else ""
            promo_date = self.date_entry.get_date().strftime("%Y-%m-%d") if hasattr(self, 'date_entry') else datetime.now().strftime("%Y-%m-%d")
            if not from_group or not to_group:
                messagebox.showerror("Error", "Please enter both From and To groups.")
                return
            extra_data = {"from_group": from_group, "to_group": to_group, "date": promo_date}
        elif cert_type == "Dedication":
            ded_date = self.date_entry.get_date().strftime("%Y-%m-%d") if hasattr(self, 'date_entry') else datetime.now().strftime("%Y-%m-%d")
            extra_data = {"date": ded_date}

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save Certificate As",
            initialfile=f"{cert_type}_{full_name}.pdf"
        )
        if not file_path:
            return

        try:
            c = canvas.Canvas(file_path, pagesize=landscape(A4))
            width, height = landscape(A4)

            # Define church colors
            blue = colors.HexColor("#1f4fa3")
            red = colors.HexColor("#d62828")
            gold = colors.HexColor("#D4AF37")
            dark_brown = colors.HexColor("#8B4513")

            # Draw background border
            c.setStrokeColor(blue)
            c.setLineWidth(5)
            c.rect(20, 20, width-40, height-40)
            c.setStrokeColor(red)
            c.setLineWidth(2)
            c.rect(30, 30, width-60, height-60)

            # Draw watermark (semi-transparent logo)
            if LOGO_PATH and os.path.exists(LOGO_PATH):
                try:
                    c.saveState()
                    c.setFillAlpha(0.2)
                    logo = ImageReader(LOGO_PATH)
                    c.drawImage(logo, width/2 - 150, height/2 - 150, width=300, height=300, preserveAspectRatio=True, mask='auto')
                    c.restoreState()
                except:
                    pass

            # Church Logo (top left)
            if LOGO_PATH and os.path.exists(LOGO_PATH):
                try:
                    logo = ImageReader(LOGO_PATH)
                    c.drawImage(logo, 50, height-130, width=80, height=80, preserveAspectRatio=True, mask='auto')
                except:
                    pass

            # Church Name
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(blue)
            c.drawCentredString(width/2, height-120, CHURCH_NAME)

            # Certificate Title
            c.setFont("Helvetica-BoldOblique", 32)
            c.setFillColor(red)
            c.drawCentredString(width/2, height-180, f"{cert_type.upper()} CERTIFICATE")

            # Decorative line above name
            c.setStrokeColor(gold)
            c.setLineWidth(2)
            c.line(200, height-240, width-200, height-240)

            # "This is to certify that"
            c.setFont("Helvetica", 16)
            c.setFillColor(colors.black)
            c.drawCentredString(width/2, height-280, "This is to certify that")

            # Member Name
            c.setFont("Helvetica-Bold", 40)
            c.setFillColor(dark_brown)
            c.drawCentredString(width/2, height-340, full_name)

            # Decorative line below name
            c.setStrokeColor(gold)
            c.setLineWidth(2)
            c.line(200, height-380, width-200, height-380)

            # Details
            c.setFont("Helvetica", 14)
            c.setFillColor(colors.black)
            y = height-420
            if cert_type == "Baptism":
                details = f"was baptized on {baptism_date or 'N/A'} by {baptized_by or 'N/A'}"
            elif cert_type == "Confirmation":
                details = f"was confirmed on {confirmation_date or 'N/A'} by {confirmed_by or 'N/A'}"
            elif cert_type == "Membership":
                details = "has become a full member of this congregation"
            elif cert_type == "Promotion":
                details = f"has been promoted from {extra_data['from_group']} to {extra_data['to_group']} on {extra_data['date']}"
            elif cert_type == "Dedication":
                details = f"was dedicated on {extra_data['date']}"
            else:
                details = ""
            c.drawCentredString(width/2, y, details)

            # Bible Verse
            if verse:
                c.setFont("Helvetica-Oblique", 12)
                c.setFillColor(colors.grey)
                c.drawCentredString(width/2, y-30, f"\"{verse}\"")

            # Signature lines
            c.setStrokeColor(blue)
            c.setLineWidth(1.5)
            c.line(100, 150, 300, 150)
            c.setFont("Helvetica", 12)
            c.setFillColor(blue)
            c.drawString(100, 130, "Pastor")
            c.line(width-300, 150, width-100, 150)
            c.drawString(width-300, 130, "Catechist")

            # Issue date
            issue_date = datetime.now().strftime("%B %d, %Y")
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(red)
            c.drawCentredString(width/2, 100, f"Issued on {issue_date}")

            # Church location
            c.setFont("Helvetica", 10)
            c.setFillColor(blue)
            c.drawCentredString(width/2, 60, "Sampa, Bono Region")

            c.save()

            # Record in history
            generated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.execute_query(
                "INSERT INTO certificates (member_id, certificate_type, verse, generated_date) VALUES (?,?,?,?)",
                (mem_id, cert_type, verse, generated_date)
            )

            messagebox.showinfo("Success", f"Certificate generated for {full_name} at:\n{file_path}")
            self.load_history()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate PDF: {e}")

    # ================== HISTORY TAB ==================
    def setup_history_tab(self):
        toolbar = tk.Frame(self.history_frame, bg="#e8f1ff")
        toolbar.pack(fill="x", padx=10, pady=10)

        self.refresh_hist_btn = tk.Button(toolbar, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                                          font=FONT_TEXT, command=self.load_history)
        self.refresh_hist_btn.pack(side="left", padx=5)
        ToolTip(self.refresh_hist_btn, "Refresh history list")

        self.delete_hist_btn = tk.Button(toolbar, text="🗑️ Delete Selected", bg="#333", fg="#fff",
                                         font=FONT_TEXT, width=15, command=self.delete_history)
        self.delete_hist_btn.pack(side="left", padx=5)
        ToolTip(self.delete_hist_btn, "Delete selected entries (file not removed)")

        tk.Label(toolbar, text="Filter Type:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.history_type_var = tk.StringVar()
        self.history_type_combo = ttk.Combobox(toolbar, textvariable=self.history_type_var,
                                                values=["All", "Baptism", "Confirmation", "Membership", "Promotion", "Dedication"],
                                                state="readonly", width=12)
        self.history_type_combo.pack(side="left", padx=5)
        self.history_type_combo.set("All")
        self.history_type_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_history())

        tk.Label(toolbar, text="Search:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.history_search_var = tk.StringVar()
        self.history_search_var.trace("w", lambda a,b,c: self.filter_history())
        tk.Entry(toolbar, textvariable=self.history_search_var, font=FONT_TEXT, width=20).pack(side="left", padx=5)

        tree_frame = tk.Frame(self.history_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Member Name", "Certificate Type", "Verse", "Generated Date", "DB_ID")
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                          yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.history_tree.yview)
        hsb.config(command=self.history_tree.xview)

        widths = [50, 200, 120, 200, 150, 0]
        for col, w in zip(columns, widths):
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=w, minwidth=20 if w>0 else 0, stretch=False)

        self.history_tree.pack(fill="both", expand=True)

        # Bind mousewheel
        def _on_mousewheel(event):
            self.history_tree.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"
        self.history_tree.bind("<MouseWheel>", _on_mousewheel)

        self.all_history = []
        self.load_history()

    def load_history(self):
        for row in self.history_tree.get_children():
            self.history_tree.delete(row)
        self.all_history.clear()

        db = DatabaseManager()
        query = """
            SELECT c.id, m.full_name, c.certificate_type, c.verse, c.generated_date, c.id
            FROM certificates c
            LEFT JOIN members m ON c.member_id = m.id
            ORDER BY c.generated_date DESC
        """
        rows = db.fetch_all(query)

        for r in rows:
            item_id = self.history_tree.insert("", tk.END, values=r)
            self.all_history.append((item_id, r[1] or "", r[2], r[4]))

        self.filter_history()

    def filter_history(self):
        type_filter = self.history_type_var.get()
        search_term = self.history_search_var.get().strip().lower()
        for item_id, member_name, cert_type, date_str in self.all_history:
            if type_filter != "All" and cert_type != type_filter:
                self.history_tree.detach(item_id)
                continue
            if search_term and search_term not in member_name.lower():
                self.history_tree.detach(item_id)
                continue
            self.history_tree.reattach(item_id, "", "end")

    def delete_history(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a history entry to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected history entries?"):
            return
        db = DatabaseManager()
        for item in selected:
            cert_id = self.history_tree.item(item)['values'][5]
            db.execute_query("DELETE FROM certificates WHERE id = ?", (cert_id,))
        self.load_history()
        self.history_tree.selection_remove(self.history_tree.selection())
        messagebox.showinfo("Success", f"{len(selected)} history entries deleted.")

    # ================== STATISTICS TAB ==================
    def setup_stats_tab(self):
        control_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="Certificate Statistics", font=("Helvetica", 14, "bold"),
                 bg="#e8f1ff", fg="#1f4fa3").pack(side="left", padx=10)

        self.refresh_stats_btn = tk.Button(control_frame, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                                           font=FONT_TEXT, command=self.refresh_stats)
        self.refresh_stats_btn.pack(side="right", padx=5)
        ToolTip(self.refresh_stats_btn, "Refresh statistics")

        self.stats_charts_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        self.stats_charts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        if self.notebook.index("current") == 2:
            self.refresh_stats()

    def refresh_stats(self):
        for widget in self.stats_charts_frame.winfo_children():
            widget.destroy()

        db = DatabaseManager()
        total = db.fetch_one("SELECT COUNT(*) FROM certificates")[0] or 0
        data = db.fetch_all("SELECT certificate_type, COUNT(*) FROM certificates GROUP BY certificate_type")

        # Left: summary card
        left_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        left_frame.pack(side="left", fill="both", expand=True, padx=5)
        card = tk.Frame(left_frame, bg="white", bd=1, relief="solid", padx=20, pady=20)
        card.pack(expand=True)
        tk.Label(card, text="Total Certificates", font=("Helvetica", 14), bg="white").pack()
        tk.Label(card, text=str(total), font=("Helvetica", 28, "bold"), fg="#1f4fa3", bg="white").pack()

        # Right: pie chart
        right_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        right_frame.pack(side="right", fill="both", expand=True, padx=5)

        if data:
            types = [r[0] for r in data]
            counts = [r[1] for r in data]
            fig = Figure(figsize=(6,4), dpi=100)
            ax = fig.add_subplot(111)
            ax.pie(counts, labels=types, autopct='%1.1f%%', startangle=90)
            ax.set_title("Certificates by Type")
        else:
            fig = Figure(figsize=(6,4), dpi=100)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data available", ha='center', va='center')
            ax.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=right_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True)

    # ================== REQUESTS TAB ==================
    def setup_requests_tab(self):
        # Toolbar
        toolbar = tk.Frame(self.requests_frame, bg="#e8f1ff")
        toolbar.pack(fill="x", padx=10, pady=10)

        self.refresh_req_btn = tk.Button(toolbar, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                                         font=FONT_TEXT, command=self.load_requests)
        self.refresh_req_btn.pack(side="left", padx=5)
        ToolTip(self.refresh_req_btn, "Refresh request list")

        self.approve_btn = tk.Button(toolbar, text="✅ Approve Selected", bg="#1f4fa3", fg="#fff",
                                     font=FONT_TEXT, command=self.approve_requests)
        self.approve_btn.pack(side="left", padx=5)
        ToolTip(self.approve_btn, "Mark selected requests as approved")

        self.reject_btn = tk.Button(toolbar, text="❌ Reject Selected", bg="#333", fg="#fff",
                                    font=FONT_TEXT, command=self.reject_requests)
        self.reject_btn.pack(side="left", padx=5)
        ToolTip(self.reject_btn, "Mark selected requests as rejected")

        # Generate from selected request button
        self.generate_from_req_btn = tk.Button(toolbar, text="📄 Generate from Selected", bg="#d62828", fg="#fff",
                                                font=FONT_TEXT, command=self.generate_from_request)
        self.generate_from_req_btn.pack(side="left", padx=5)
        ToolTip(self.generate_from_req_btn, "Pre-fill Generate tab with selected request and switch to it")

        # Treeview frame
        tree_frame = tk.Frame(self.requests_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Member Name", "Certificate Type", "Request Date", "Status", "DB_ID")
        self.requests_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.requests_tree.yview)
        hsb.config(command=self.requests_tree.xview)

        widths = [50, 200, 120, 150, 100, 0]
        for col, w in zip(columns, widths):
            self.requests_tree.heading(col, text=col)
            self.requests_tree.column(col, width=w, minwidth=20 if w>0 else 0, stretch=False)

        self.requests_tree.pack(fill="both", expand=True)
        self.load_requests()

    def load_requests(self):
        for row in self.requests_tree.get_children():
            self.requests_tree.delete(row)
        db = DatabaseManager()
        rows = db.fetch_all("""
            SELECT r.id, m.full_name, r.certificate_type, r.request_date, r.status, r.id
            FROM certificate_requests r
            LEFT JOIN members m ON r.member_id = m.id
            ORDER BY r.request_date DESC
        """)
        for r in rows:
            self.requests_tree.insert("", tk.END, values=r)

    def approve_requests(self):
        selected = self.requests_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select requests to approve.")
            return
        db = DatabaseManager()
        for item in selected:
            req_id = self.requests_tree.item(item)['values'][5]
            db.execute_query("UPDATE certificate_requests SET status='approved' WHERE id=?", (req_id,))
        self.load_requests()
        messagebox.showinfo("Success", f"{len(selected)} request(s) approved.")

    def reject_requests(self):
        selected = self.requests_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select requests to reject.")
            return
        db = DatabaseManager()
        for item in selected:
            req_id = self.requests_tree.item(item)['values'][5]
            db.execute_query("UPDATE certificate_requests SET status='rejected' WHERE id=?", (req_id,))
        self.load_requests()
        messagebox.showinfo("Success", f"{len(selected)} request(s) rejected.")

    def generate_from_request(self):
        """Pre-fill the Generate tab with the selected request's member and certificate type."""
        selected = self.requests_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select a request to generate from.")
            return
        # Get the request ID from the first selected item (hidden DB_ID column)
        req_id = self.requests_tree.item(selected[0], "values")[5]
        db = DatabaseManager()
        request = db.fetch_one("""
            SELECT r.member_id, r.certificate_type, m.full_name, m.member_id
            FROM certificate_requests r
            LEFT JOIN members m ON r.member_id = m.id
            WHERE r.id = ?
        """, (req_id,))
        if not request:
            messagebox.showerror("Error", "Request not found.")
            return
        member_db_id, cert_type, full_name, member_id_str = request
        if not full_name or not member_id_str:
            messagebox.showerror("Error", "Member information missing.")
            return

        # Construct the display string as it appears in the combobox
        display = f"{full_name} ({member_id_str})"

        # Set the generate tab comboboxes
        self.member_var.set(display)
        self.cert_type_combo.set(cert_type)
        # Trigger the certificate type change to show any extra fields
        self.on_cert_type_change()
        # Update preview
        self.update_preview()

        # Switch to the generate tab (index 0)
        self.notebook.select(0)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x700")
    app = CertificatesModule(root)
    root.mainloop()