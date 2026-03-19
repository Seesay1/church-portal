# families.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from database import create_connection
from config import FONT_TEXT

class FamiliesModule:
    def __init__(self, root):
        self.root = root
        self.root.configure(bg="#e8f1ff")
        
        # ---------- Top Frame ----------
        self.top_frame = tk.Frame(root, bg="#e8f1ff", height=100)
        self.top_frame.pack(side="top", fill="x")
        tk.Button(self.top_frame, text="Add Family", width=15, bg="#d62828", fg="#fff",
                  font=FONT_TEXT, command=self.add_family).pack(side="left", padx=10, pady=20)
        tk.Button(self.top_frame, text="Add Member to Family", width=20, bg="#1f4fa3", fg="#fff",
                  font=FONT_TEXT, command=self.add_member_to_family).pack(side="left", padx=10)
        
        # ---------- Bottom Frame ----------
        self.bottom_frame = tk.Frame(root, bg="#e8f1ff")
        self.bottom_frame.pack(fill="both", expand=True)
        
        # ---------- Treeview ----------
        columns = ("Family Name", "Head of Family", "Members Count")
        self.tree = ttk.Treeview(self.bottom_frame, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200)
        self.tree.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.load_families()
    
    # ---------- Load Families ----------
    def load_families(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, family_name, head_of_family FROM families")
        rows = cursor.fetchall()
        for r in rows:
            cursor.execute("SELECT COUNT(*) FROM family_members WHERE family_id=?", (r[0],))
            count = cursor.fetchone()[0]
            self.tree.insert("", tk.END, values=(r[1], r[2], count))
        conn.close()
    
    # ---------- Add Family ----------
    def add_family(self):
        family_name = simpledialog.askstring("Add Family", "Enter family name:")
        if not family_name:
            return
        head_of_family = simpledialog.askstring("Add Family", "Enter head of family:")
        if not head_of_family:
            return
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO families (family_name, head_of_family) VALUES (?,?)", (family_name, head_of_family))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Family '{family_name}' added.")
        self.load_families()
    
    # ---------- Add Member to Family ----------
    def add_member_to_family(self):
        # Select family
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Select Family", "Please select a family first")
            return
        family_id = self.get_family_id(selected[0])
        
        # Enter member ID (existing member in members table)
        member_id = simpledialog.askstring("Add Member", "Enter member ID to add to family:")
        if not member_id:
            return
        
        # Insert into family_members
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM members WHERE member_id=?", (member_id,))
        member = cursor.fetchone()
        if not member:
            messagebox.showerror("Error", "Member ID not found!")
            conn.close()
            return
        cursor.execute("INSERT INTO family_members (family_id, member_id, relation) VALUES (?,?,?)",
                       (family_id, member[0], "Member"))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", f"Member '{member_id}' added to family.")
        self.load_families()
    
    def get_family_id(self, item):
        values = self.tree.item(item, "values")
        family_name = values[0]
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM families WHERE family_name=?", (family_name,))
        family_id = cursor.fetchone()[0]
        conn.close()
        return family_id

# ---------- Run Module ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = FamiliesModule(root)
    root.mainloop()