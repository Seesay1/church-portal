import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from database import DatabaseManager

FONT_TEXT = ("Helvetica", 10)

class FinancialManagement:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")
        self.editing_id = None

        # Create Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Transactions List
        self.list_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.list_frame, text="💰 Transactions")

        # Tab 2: Statistics
        self.stats_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        self.setup_list_tab()
        self.setup_stats_tab()

        # Load initial data
        self.load_filters()
        self.load_transactions()

    # ================== TRANSACTIONS LIST TAB ==================
    def setup_list_tab(self):
        # ---------- Top Toolbar ----------
        toolbar = tk.Frame(self.list_frame, bg="#e8f1ff")
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        # Buttons on left
        btn_frame = tk.Frame(toolbar, bg="#e8f1ff")
        btn_frame.pack(side="left", fill="x", expand=True)

        tk.Button(btn_frame, text="➕ Add Income", width=15, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=lambda: self.add_transaction("Contribution")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="➕ Add Expense", width=15, bg="#d62828", fg="#fff",
                  font=FONT_TEXT, command=lambda: self.add_transaction("Expense")).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✏️ Edit Selected", width=15, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete Selected", width=15, bg="#333", fg="#fff",
                  font=FONT_TEXT, command=self.delete_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="📄 Export", width=10, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.export_data).pack(side="left", padx=5)

        # ---------- Filter Frame ----------
        filter_frame = tk.Frame(self.list_frame, bg="#e8f1ff")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Type filter
        tk.Label(filter_frame, text="Type:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(filter_frame, textvariable=self.type_var,
                                       values=["All", "Contribution", "Expense"], state="readonly", width=12)
        self.type_combo.pack(side="left", padx=5)
        self.type_combo.set("All")
        self.type_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_transactions())

        # Branch filter
        tk.Label(filter_frame, text="Branch:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.branch_var = tk.StringVar()
        self.branch_combo = ttk.Combobox(filter_frame, textvariable=self.branch_var,
                                         values=["All"], state="readonly", width=15)
        self.branch_combo.pack(side="left", padx=5)
        self.branch_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_transactions())

        # Group filter
        tk.Label(filter_frame, text="Group:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.group_var = tk.StringVar()
        self.group_combo = ttk.Combobox(filter_frame, textvariable=self.group_var,
                                        values=["All"], state="readonly", width=15)
        self.group_combo.pack(side="left", padx=5)
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self.filter_transactions())

        # Date Range
        tk.Label(filter_frame, text="From:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.date_from = DateEntry(filter_frame, width=10, background='blue', foreground='white',
                                   borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.date_from.pack(side="left", padx=2)
        self.date_from.set_date(datetime.now() - timedelta(days=30))

        tk.Label(filter_frame, text="To:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.date_to = DateEntry(filter_frame, width=10, background='blue', foreground='white',
                                 borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.date_to.pack(side="left", padx=2)
        self.date_to.set_date(datetime.now() + timedelta(days=1))

        # Apply button
        tk.Button(filter_frame, text="Apply", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.filter_transactions).pack(side="left", padx=5)

        # Clear filters
        tk.Button(filter_frame, text="✖ Clear", bg="#e8f1ff", fg="#d62828",
                  font=FONT_TEXT, command=self.clear_filters).pack(side="left", padx=5)

        # ---------- Treeview with Scrollbars ----------
        tree_frame = tk.Frame(self.list_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Type", "Member ID", "Full Name", "Branch", "Group", "Amount", "Date", "DB_ID")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        widths = [50, 100, 100, 150, 100, 100, 100, 100, 0]  # last column hidden
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=20 if w>0 else 0, stretch=False)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_transaction)

        # Store all transactions for filtering
        self.all_transactions = []

    def load_filters(self):
        """Populate branch/group comboboxes from database."""
        db = DatabaseManager()
        branches = [r[0] for r in db.fetch_all("SELECT name FROM branches ORDER BY name")]
        groups = [r[0] for r in db.fetch_all("SELECT name FROM groups ORDER BY name")]
        self.branch_combo['values'] = ["All"] + branches
        self.group_combo['values'] = ["All"] + groups
        self.branch_var.set("All")
        self.group_var.set("All")

    def load_transactions(self):
        """Load all financial records from database."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.all_transactions.clear()

        db = DatabaseManager()
        query = """
            SELECT f.id, f.type, m.member_id, m.full_name, b.name, g.name, f.amount, f.date, f.id
            FROM financial_records f
            LEFT JOIN members m ON f.member_id = m.id
            LEFT JOIN branches b ON f.branch_id = b.id
            LEFT JOIN groups g ON f.group_id = g.id
            ORDER BY f.date DESC, f.id DESC
        """
        rows = db.fetch_all(query)

        for r in rows:
            item_id = self.tree.insert("", tk.END, values=r)
            # Store for filtering: (item_id, type, branch, group, date, search_text)
            search_text = f"{r[2] or ''} {r[3] or ''}".lower()
            self.all_transactions.append((item_id, r[1], r[4] or "", r[5] or "", r[7], search_text))

        self.filter_transactions()

    def filter_transactions(self):
        """Apply filters to the treeview."""
        type_filter = self.type_var.get()
        branch_filter = self.branch_var.get()
        group_filter = self.group_var.get()
        date_from = self.date_from.get_date()
        date_to = self.date_to.get_date()

        for item_id, typ, branch, group, date_str, search_text in self.all_transactions:
            # Type filter
            if type_filter != "All" and typ != type_filter:
                self.tree.detach(item_id)
                continue
            # Branch filter
            if branch_filter != "All" and branch != branch_filter:
                self.tree.detach(item_id)
                continue
            # Group filter
            if group_filter != "All" and group != group_filter:
                self.tree.detach(item_id)
                continue
            # Date filter
            trans_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            if trans_date and (trans_date < date_from or trans_date > date_to):
                self.tree.detach(item_id)
                continue

            self.tree.reattach(item_id, "", "end")

    def clear_filters(self):
        self.type_var.set("All")
        self.branch_var.set("All")
        self.group_var.set("All")
        self.date_from.set_date(datetime.now() - timedelta(days=30))
        self.date_to.set_date(datetime.now() + timedelta(days=1))
        self.filter_transactions()

    # ---------- CRUD Operations ----------
    def add_transaction(self, trans_type):
        self._transaction_form(f"Add {trans_type}", trans_type)

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a transaction to edit.")
            return
        self.editing_id = self.tree.item(selected[0])['values'][8]  # hidden DB_ID
        trans_type = self.tree.item(selected[0])['values'][1]
        self._transaction_form(f"Edit {trans_type}", trans_type, selected[0])

    def edit_transaction(self, event):
        selected = self.tree.selection()
        if selected:
            self.editing_id = self.tree.item(selected[0])['values'][8]
            trans_type = self.tree.item(selected[0])['values'][1]
            self._transaction_form(f"Edit {trans_type}", trans_type, selected[0])

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a transaction to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected transaction(s)?"):
            return
        db = DatabaseManager()
        for item in selected:
            trans_id = self.tree.item(item)['values'][8]  # hidden DB_ID
            db.execute_query("DELETE FROM financial_records WHERE id = ?", (trans_id,))
        self.load_transactions()
        self.tree.selection_remove(self.tree.selection())
        messagebox.showinfo("Success", f"{len(selected)} transaction(s) deleted.")

    # ---------- Transaction Form (Add/Edit) ----------
    def _transaction_form(self, title, trans_type, item_id=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("450x500")
        win.configure(bg="#e8f1ff")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        win.lift()
        win.focus_force()

        # Type (readonly if editing)
        tk.Label(win, text="Type:", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        type_label = tk.Label(win, text=trans_type, bg="#e8f1ff", font=("Helvetica", 10, "bold"))
        type_label.pack()

        # Member ID (optional)
        tk.Label(win, text="Member ID (optional for Expense):", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        member_frame = tk.Frame(win, bg="#e8f1ff")
        member_frame.pack()
        self.member_entry = tk.Entry(member_frame, font=FONT_TEXT, width=25)
        self.member_entry.pack(side="left", padx=5)
        tk.Button(member_frame, text="🔍 Lookup", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.lookup_member).pack(side="left")

        # Member name display (if found)
        self.member_name_label = tk.Label(win, text="", bg="#e8f1ff", font=FONT_TEXT, fg="#1f4fa3")
        self.member_name_label.pack()

        # Amount
        tk.Label(win, text="Amount *", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.amount_entry = tk.Entry(win, font=FONT_TEXT, width=30)
        self.amount_entry.pack(pady=5)

        # Date
        tk.Label(win, text="Date *", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.date_entry = DateEntry(win, width=20, background='blue', foreground='white',
                                    borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.date_entry.pack(pady=5)
        self.date_entry.set_date(datetime.now())

        # Branch and Group (auto-filled if member selected, editable for expenses)
        tk.Label(win, text="Branch (optional):", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.branch_combo_form = ttk.Combobox(win, values=self.get_branch_list(), state="normal", width=27)
        self.branch_combo_form.pack(pady=5)

        tk.Label(win, text="Group (optional):", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.group_combo_form = ttk.Combobox(win, values=self.get_group_list(), state="normal", width=27)
        self.group_combo_form.pack(pady=5)

        # If editing, load data
        if item_id:
            self._load_transaction_data(item_id)

        # Buttons
        btn_frame = tk.Frame(win, bg="#e8f1ff")
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Cancel", bg="#888888", fg="#fff",
                  font=FONT_TEXT, width=10, command=win.destroy).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save", bg="#d62828", fg="#fff",
                  font=FONT_TEXT, width=10, command=lambda: self.save_transaction(win, trans_type)).pack(side="left", padx=5)

        win.bind("<Return>", lambda e: self.save_transaction(win, trans_type))

    def get_branch_list(self):
        db = DatabaseManager()
        return [r[0] for r in db.fetch_all("SELECT name FROM branches ORDER BY name")]

    def get_group_list(self):
        db = DatabaseManager()
        return [r[0] for r in db.fetch_all("SELECT name FROM groups ORDER BY name")]

    def lookup_member(self):
        member_id = self.member_entry.get().strip()
        if not member_id:
            return
        db = DatabaseManager()
        member = db.fetch_one(
            "SELECT id, full_name, branch_id, group_id FROM members WHERE member_id = ?",
            (member_id,)
        )
        if member:
            self.member_name_label.config(text=f"Found: {member[1]}")
            # Auto-fill branch and group
            if member[2]:
                branch_name = db.fetch_one("SELECT name FROM branches WHERE id = ?", (member[2],))
                if branch_name:
                    self.branch_combo_form.set(branch_name[0])
            if member[3]:
                group_name = db.fetch_one("SELECT name FROM groups WHERE id = ?", (member[3],))
                if group_name:
                    self.group_combo_form.set(group_name[0])
        else:
            self.member_name_label.config(text="Member not found!", fg="#d62828")

    def _load_transaction_data(self, item_id):
        values = self.tree.item(item_id, "values")
        # values: (ID, Type, Member ID, Full Name, Branch, Group, Amount, Date, DB_ID)
        self.member_entry.insert(0, values[2] or "")
        self.amount_entry.insert(0, values[6])
        self.date_entry.set_date(values[7])
        self.branch_combo_form.set(values[4] or "")
        self.group_combo_form.set(values[5] or "")
        if values[2]:
            self.member_name_label.config(text=f"Member: {values[3]}")

    def save_transaction(self, win, trans_type):
        member_id_input = self.member_entry.get().strip()
        amount_str = self.amount_entry.get().strip()
        date_str = self.date_entry.get_date().strftime("%Y-%m-%d")
        branch_name = self.branch_combo_form.get().strip()
        group_name = self.group_combo_form.get().strip()

        if not amount_str:
            messagebox.showerror("Error", "Amount is required!")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "Amount must be a positive number!")
            return

        db = DatabaseManager()
        member_db_id = None
        branch_id = None
        group_id = None

        if member_id_input:
            member = db.fetch_one("SELECT id FROM members WHERE member_id = ?", (member_id_input,))
            if member:
                member_db_id = member[0]
            else:
                messagebox.showerror("Error", "Member ID not found!")
                return

        # Resolve branch and group IDs if provided
        if branch_name:
            branch = db.fetch_one("SELECT id FROM branches WHERE name = ?", (branch_name,))
            if branch:
                branch_id = branch[0]
            else:
                # Optionally create new branch?
                messagebox.showerror("Error", f"Branch '{branch_name}' not found!")
                return
        if group_name:
            group = db.fetch_one("SELECT id FROM groups WHERE name = ?", (group_name,))
            if group:
                group_id = group[0]
            else:
                messagebox.showerror("Error", f"Group '{group_name}' not found!")
                return

        if self.editing_id:
            # Update
            query = """
                UPDATE financial_records
                SET type=?, member_id=?, branch_id=?, group_id=?, amount=?, date=?
                WHERE id=?
            """
            params = (trans_type, member_db_id, branch_id, group_id, amount, date_str, self.editing_id)
            success = db.execute_query(query, params)
            if success:
                messagebox.showinfo("Success", "Transaction updated.")
                win.destroy()
                self.load_transactions()
            else:
                messagebox.showerror("Error", "Failed to update transaction.")
        else:
            # Insert
            query = """
                INSERT INTO financial_records (type, member_id, branch_id, group_id, amount, date)
                VALUES (?,?,?,?,?,?)
            """
            params = (trans_type, member_db_id, branch_id, group_id, amount, date_str)
            success = db.execute_query(query, params)
            if success:
                messagebox.showinfo("Success", f"{trans_type} recorded.")
                win.destroy()
                self.load_transactions()
            else:
                messagebox.showerror("Error", "Failed to save transaction.")

    # ---------- Export ----------
    def export_data(self):
        from tkinter import filedialog
        import csv
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Transactions"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Type", "Member ID", "Full Name", "Branch", "Group", "Amount", "Date"])
                for item in self.tree.get_children():
                    values = self.tree.item(item, "values")[:-1]  # exclude hidden DB_ID
                    writer.writerow(values)
            messagebox.showinfo("Export Successful", f"Data exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ================== STATISTICS TAB ==================
    def setup_stats_tab(self):
        control_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="Financial Statistics", font=("Helvetica", 14, "bold"),
                 bg="#e8f1ff", fg="#1f4fa3").pack(side="left", padx=10)

        # Date range for stats
        tk.Label(control_frame, text="From:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.stats_from = DateEntry(control_frame, width=10, background='blue', foreground='white',
                                    borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.stats_from.pack(side="left", padx=2)
        self.stats_from.set_date(datetime.now() - timedelta(days=30))

        tk.Label(control_frame, text="To:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.stats_to = DateEntry(control_frame, width=10, background='blue', foreground='white',
                                  borderwidth=2, date_pattern='yyyy-mm-dd', font=FONT_TEXT)
        self.stats_to.pack(side="left", padx=2)
        self.stats_to.set_date(datetime.now())

        tk.Button(control_frame, text="Update Charts", bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.refresh_stats).pack(side="left", padx=5)

        # Frame for charts
        self.stats_charts_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        self.stats_charts_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        if self.notebook.index("current") == 1:  # Statistics tab
            self.refresh_stats()

    def refresh_stats(self):
        for widget in self.stats_charts_frame.winfo_children():
            widget.destroy()

        # Create two frames for charts
        left_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        left_frame.pack(side="left", fill="both", expand=True, padx=5)
        right_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        right_frame.pack(side="right", fill="both", expand=True, padx=5)

        self.draw_income_expense_pie(left_frame)
        self.draw_monthly_trend(right_frame)
        self.draw_totals_summary(left_frame)  # will be placed under pie

    def get_filtered_data(self):
        """Fetch financial data filtered by stats date range."""
        date_from = self.stats_from.get_date().strftime("%Y-%m-%d")
        date_to = self.stats_to.get_date().strftime("%Y-%m-%d")
        db = DatabaseManager()
        query = """
            SELECT type, SUM(amount) 
            FROM financial_records 
            WHERE date BETWEEN ? AND ?
            GROUP BY type
        """
        return db.fetch_all(query, (date_from, date_to))

    def draw_income_expense_pie(self, parent):
        data = self.get_filtered_data()
        income = 0
        expense = 0
        for typ, amt in data:
            if typ == "Contribution":
                income += amt
            elif typ == "Expense":
                expense += amt

        fig = Figure(figsize=(5,4), dpi=100)
        ax = fig.add_subplot(111)
        if income + expense == 0:
            ax.text(0.5, 0.5, "No data for selected period", ha='center', va='center')
            ax.axis('off')
        else:
            labels = ['Income', 'Expense']
            sizes = [income, expense]
            colors = ['#2a9df4', '#d62828']
            ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax.set_title('Income vs Expense')

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def draw_monthly_trend(self, parent):
        db = DatabaseManager()
        date_from = self.stats_from.get_date().strftime("%Y-%m-%d")
        date_to = self.stats_to.get_date().strftime("%Y-%m-%d")
        query = """
            SELECT strftime('%Y-%m', date), 
                   SUM(CASE WHEN type='Contribution' THEN amount ELSE 0 END) as income,
                   SUM(CASE WHEN type='Expense' THEN amount ELSE 0 END) as expense
            FROM financial_records
            WHERE date BETWEEN ? AND ?
            GROUP BY strftime('%Y-%m', date)
            ORDER BY 1
        """
        data = db.fetch_all(query, (date_from, date_to))

        fig = Figure(figsize=(6,3), dpi=100)
        ax = fig.add_subplot(111)
        if data:
            months = [row[0] for row in data]
            incomes = [row[1] for row in data]
            expenses = [row[2] for row in data]
            ax.plot(months, incomes, marker='o', label='Income', color="#2a9df4")
            ax.plot(months, expenses, marker='s', label='Expense', color="#d62828")
            ax.set_title("Monthly Trend")
            ax.set_xlabel("Month")
            ax.set_ylabel("Amount")
            ax.legend()
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        else:
            ax.text(0.5, 0.5, "No data for selected period", ha='center', va='center')
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    
    def draw_totals_summary(self, parent):
        data = self.get_filtered_data()
        total_income = 0
        total_expense = 0
        for typ, amt in data:
            if typ == "Contribution":
                total_income += amt
            elif typ == "Expense":
                total_expense += amt
        balance = total_income - total_expense

        card = tk.Frame(parent, bg="white", bd=1, relief="solid")
        card.pack(fill="x", pady=10, padx=5, ipadx=10, ipady=10)
        tk.Label(card, text="Summary", font=("Helvetica", 12, "bold"),
                bg="white", fg="#1f4fa3").pack()
        tk.Label(card, text=f"Total Income: ₵{total_income:,.2f}",
                bg="white", fg="#2a9df4", font=("Helvetica", 11)).pack()
        tk.Label(card, text=f"Total Expense: ₵{total_expense:,.2f}",
                bg="white", fg="#d62828", font=("Helvetica", 11)).pack()
        tk.Label(card, text=f"Net Balance: ₵{balance:,.2f}",
                bg="white", fg="#000" if balance>=0 else "#d62828",
                font=("Helvetica", 11, "bold")).pack()
    
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1300x700")
    FinancialManagement(root)
    root.mainloop()