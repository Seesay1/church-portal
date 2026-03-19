import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager, hash_password

class UsersModule:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")

        toolbar = tk.Frame(root, bg="#e8f1ff")
        toolbar.pack(side="top", fill="x", padx=10, pady=10)

        tk.Button(toolbar, text="➕ Add User", bg="#d62828", fg="#fff",
                  font=("Helvetica", 10), command=self.add_user_window).pack(side="left", padx=5)
        tk.Button(toolbar, text="✏️ Edit Selected", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 10), command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(toolbar, text="🗑️ Delete Selected", bg="#333", fg="#fff",
                  font=("Helvetica", 10), command=self.delete_selected).pack(side="left", padx=5)

        tree_frame = tk.Frame(root, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("Username", "Role")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("Username", text="Username")
        self.tree.heading("Role", text="Role")
        self.tree.column("Username", width=150)
        self.tree.column("Role", width=100)
        self.tree.pack(fill="both", expand=True)

        self.load_users()

    def load_users(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        db = DatabaseManager()
        rows = db.fetch_all("SELECT username, role FROM users ORDER BY username")
        for r in rows:
            self.tree.insert("", tk.END, values=(r[0], r[1]))

    def add_user_window(self):
        self._user_form("Add User")

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a user to edit.")
            return
        username = self.tree.item(selected[0])['values'][0]
        self._user_form("Edit User", username)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a user to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Delete selected user(s)?"):
            return
        db = DatabaseManager()
        for item in selected:
            username = self.tree.item(item)['values'][0]
            db.execute_query("DELETE FROM users WHERE username = ?", (username,))
        self.load_users()

    def _user_form(self, title, username=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("300x250")
        win.configure(bg="#e8f1ff")
        win.resizable(False, False)

        tk.Label(win, text="Username:", bg="#e8f1ff").pack(pady=5)
        entry_user = tk.Entry(win)
        entry_user.pack(pady=5)

        tk.Label(win, text="Password:", bg="#e8f1ff").pack(pady=5)
        entry_pass = tk.Entry(win, show="*")
        entry_pass.pack(pady=5)

        tk.Label(win, text="Role:", bg="#e8f1ff").pack(pady=5)
        role_combo = ttk.Combobox(win, values=["Admin", "User"], state="readonly")
        role_combo.pack(pady=5)

        if username:
            db = DatabaseManager()
            user = db.fetch_one("SELECT username, role FROM users WHERE username=?", (username,))
            if user:
                entry_user.insert(0, user[0])
                entry_user.config(state="readonly")
                role_combo.set(user[1])

        def save():
            u_name = entry_user.get().strip()
            pwd = entry_pass.get().strip()
            role = role_combo.get().strip()
            if not u_name or not role:
                messagebox.showerror("Error", "Username and role are required.")
                return
            if not username and not pwd:
                messagebox.showerror("Error", "Password is required for new users.")
                return

            db = DatabaseManager()
            if username:
                if pwd:
                    hashed = hash_password(pwd)
                    db.execute_query("UPDATE users SET password=? WHERE username=?", (hashed, username))
                db.execute_query("UPDATE users SET role=? WHERE username=?", (role, username))
                messagebox.showinfo("Success", "User updated.")
            else:
                hashed = hash_password(pwd)
                db.execute_query("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                                 (u_name, hashed, role))
                messagebox.showinfo("Success", "User added.")
            win.destroy()
            self.load_users()

        tk.Button(win, text="Save", bg="#d62828", fg="#fff", command=save).pack(pady=20)