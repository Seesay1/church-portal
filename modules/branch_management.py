import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from database import DatabaseManager
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

FONT_TEXT = ("Helvetica", 10)

class BranchManagement:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")
        self.editing_id = None

        # Create Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Branches List
        self.list_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.list_frame, text="📋 Branches List")

        # Tab 2: Statistics
        self.stats_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        self.setup_list_tab()
        self.setup_stats_tab()

        self.load_branches()

    # ================== BRANCHES LIST TAB ==================
    def setup_list_tab(self):
        # ---------- Top Toolbar ----------
        toolbar = tk.Frame(self.list_frame, bg="#e8f1ff")
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        # Buttons on left
        btn_frame = tk.Frame(toolbar, bg="#e8f1ff")
        btn_frame.pack(side="left", fill="x", expand=True)

        tk.Button(btn_frame, text="➕ Add Branch", width=15, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.add_branch).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✏️ Edit Selected", width=15, bg="#d62828", fg="#fff",
                  font=FONT_TEXT, command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(btn_frame, text="🗑️ Delete Selected", width=18, bg="#333", fg="#fff",
                  font=FONT_TEXT, command=self.delete_selected).pack(side="left", padx=5) 
        tk.Button(btn_frame, text="📄 Export", width=10, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.export_data).pack(side="left", padx=5)

        # ---------- Filter Frame ----------
        filter_frame = tk.Frame(self.list_frame, bg="#e8f1ff")
        filter_frame.pack(fill="x", padx=10, pady=5)

        # Search
        tk.Label(filter_frame, text="🔍 Search:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda a,b,c: self.filter_branches())
        tk.Entry(filter_frame, textvariable=self.search_var, font=FONT_TEXT, width=25).pack(side="left", padx=5)

        # Clear filters button
        tk.Button(filter_frame, text="✖ Clear", bg="#e8f1ff", fg="#d62828",
                  font=FONT_TEXT, command=self.clear_filters).pack(side="left", padx=5)

        # ---------- Treeview with Scrollbars ----------
        tree_frame = tk.Frame(self.list_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("Branch ID", "Branch Name", "Location", "Contact", "DB_ID")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        widths = [80, 150, 150, 150, 0]  # last column hidden
        for col, w in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=20 if w>0 else 0, stretch=False)

        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_branch)

        # Store all branches for filtering
        self.all_branches = []

    def load_branches(self):
        """Load all branches from database."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.all_branches.clear()

        db = DatabaseManager()
        query = "SELECT id, name, address, phone FROM branches ORDER BY name"
        rows = db.fetch_all(query)

        for r in rows:
            values = [r[0], r[1] or "", r[2] or "", r[3] or "", r[0]]  # hidden DB_ID
            item_id = self.tree.insert("", tk.END, values=values)
            search_text = f"{r[1] or ''} {r[2] or ''} {r[3] or ''}".lower()
            self.all_branches.append((item_id, search_text))

        self.filter_branches()

    def filter_branches(self):
        """Apply search filter to the treeview."""
        search_term = self.search_var.get().strip().lower()
        for item_id, search_text in self.all_branches:
            if search_term and search_term not in search_text:
                self.tree.detach(item_id)
            else:
                self.tree.reattach(item_id, "", "end")

    def clear_filters(self):
        self.search_var.set("")
        self.filter_branches()

    # ---------- CRUD Operations ----------
    def add_branch(self):
        self._branch_form("Add Branch")

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a branch to edit.")
            return
        self._branch_form("Edit Branch", selected[0])

    def edit_branch(self, event):
        selected = self.tree.selection()
        if selected:
            self._branch_form("Edit Branch", selected[0])

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a branch to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Delete selected branch(es)?"):
            return

        db = DatabaseManager()
        for item in selected:
            branch_id = self.tree.item(item)['values'][4]  # hidden DB_ID
            try:
                db.execute_query("DELETE FROM branches WHERE id = ?", (branch_id,))
            except Exception as e:
                if "FOREIGN KEY constraint failed" in str(e):
                    messagebox.showerror("Error", "Cannot delete branch with members assigned. Reassign or delete members first.")
                else:
                    messagebox.showerror("Error", f"Database error: {e}")
                return

        self.load_branches()
        self.tree.selection_remove(self.tree.selection())
        messagebox.showinfo("Success", f"{len(selected)} branch(es) deleted.")

    # ---------- Branch Form (Add/Edit) ----------
    def _branch_form(self, title, item_id=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("400x300")
        win.configure(bg="#e8f1ff")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        win.lift()
        win.focus_force()

        # Branch Name
        tk.Label(win, text="Branch Name *", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.name_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.name_entry.pack(pady=5)

        # Location
        tk.Label(win, text="Location", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.location_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.location_entry.pack(pady=5)

        # Contact
        tk.Label(win, text="Contact Info", bg="#e8f1ff", font=FONT_TEXT).pack(pady=(10,0))
        self.contact_entry = tk.Entry(win, font=FONT_TEXT, width=35)
        self.contact_entry.pack(pady=5)

        # Load data if editing
        if item_id:
            values = self.tree.item(item_id, "values")
            self.name_entry.insert(0, values[1])
            self.location_entry.insert(0, values[2])
            self.contact_entry.insert(0, values[3])
            self.editing_id = values[4]  # hidden DB_ID
        else:
            self.editing_id = None

        # Buttons
        btn_frame = tk.Frame(win, bg="#e8f1ff")
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Cancel", bg="#888888", fg="#fff",
                  font=FONT_TEXT, width=10, command=win.destroy).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Save", bg="#d62828", fg="#fff",
                  font=FONT_TEXT, width=10, command=lambda: self.save_branch(win)).pack(side="left", padx=5)

        win.bind("<Return>", lambda e: self.save_branch(win))

    def save_branch(self, win):
        name = self.name_entry.get().strip()
        location = self.location_entry.get().strip()
        contact = self.contact_entry.get().strip()

        if not name:
            messagebox.showerror("Error", "Branch name is required!")
            return

        db = DatabaseManager()

        if self.editing_id:
            # Update
            query = "UPDATE branches SET name=?, address=?, phone=? WHERE id=?"
            success = db.execute_query(query, (name, location, contact, self.editing_id))
            if success:
                messagebox.showinfo("Success", f"Branch '{name}' updated.")
                win.destroy()
                self.load_branches()
            else:
                messagebox.showerror("Error", "Failed to update branch (maybe duplicate name).")
        else:
            # Insert
            query = "INSERT INTO branches (name, address, phone) VALUES (?,?,?)"
            success = db.execute_query(query, (name, location, contact))
            if success:
                messagebox.showinfo("Success", f"Branch '{name}' added.")
                win.destroy()
                self.load_branches()
            else:
                messagebox.showerror("Error", "Failed to add branch (maybe duplicate name).")

    # ---------- Export ----------
    def export_data(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Export Branches"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Branch ID", "Branch Name", "Location", "Contact"])
                for item in self.tree.get_children():
                    values = self.tree.item(item, "values")[:4]  # exclude hidden DB_ID
                    writer.writerow(values)
            messagebox.showinfo("Export Successful", f"Data exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", str(e))

    # ================== STATISTICS TAB ==================
    def setup_stats_tab(self):
        control_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="Branch Statistics", font=("Helvetica", 14, "bold"),
                 bg="#e8f1ff", fg="#1f4fa3").pack(side="left", padx=10)

        self.refresh_stats_btn = tk.Button(control_frame, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                                           font=FONT_TEXT, command=self.refresh_stats)
        self.refresh_stats_btn.pack(side="right", padx=5)

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

        self.draw_branch_count_card(left_frame)
        self.draw_members_per_branch_chart(right_frame)

    def draw_branch_count_card(self, parent):
        db = DatabaseManager()
        total = db.fetch_one("SELECT COUNT(*) FROM branches")[0] or 0

        card = tk.Frame(parent, bg="white", bd=1, relief="solid")
        card.pack(fill="x", pady=10, padx=5, ipadx=10, ipady=20)
        tk.Label(card, text="🏢 Total Branches", font=("Helvetica", 14),
                 bg="white", fg="#1f4fa3").pack()
        tk.Label(card, text=str(total), font=("Helvetica", 32, "bold"),
                 bg="white", fg="#d62828").pack()

    def draw_members_per_branch_chart(self, parent):
        db = DatabaseManager()
        data = db.fetch_all("""
            SELECT b.name, COUNT(m.id) 
            FROM branches b
            LEFT JOIN members m ON b.id = m.branch_id
            GROUP BY b.id
            ORDER BY COUNT(m.id) DESC
        """)
        if not data:
            fig = Figure(figsize=(5,4), dpi=100)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No branch data", ha='center', va='center')
            ax.axis('off')
        else:
            branches = [r[0] for r in data]
            counts = [r[1] for r in data]
            fig = Figure(figsize=(5,4), dpi=100)
            ax = fig.add_subplot(111)
            ax.bar(branches, counts, color="#2a9df4")
            ax.set_title("Members per Branch")
            ax.set_xlabel("Branch")
            ax.set_ylabel("Members")
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x600")
    BranchManagement(root)
    root.mainloop()