# modules/resources.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import shutil
from database import DatabaseManager
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog

class ResourcesModule:
    def __init__(self, parent, user_id=None, branch_id=None):
        self.parent = parent
        self.user_id = user_id
        self.db = DatabaseManager()
        
        # Main frame
        self.main_frame = tk.Frame(parent, bg="#e8f1ff")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Toolbar
        toolbar = tk.Frame(self.main_frame, bg="#e8f1ff")
        toolbar.pack(fill="x", pady=(0, 10))
        
        tk.Button(toolbar, text="📤 Upload Resource", bg="#d62828", fg="#fff",
                  font=("Helvetica", 10), command=self.upload_resource).pack(side="left", padx=5)
        tk.Button(toolbar, text="✏️ Edit Selected", bg="#1f4fa3", fg="#fff",
                  font=("Helvetica", 10), command=self.edit_selected).pack(side="left", padx=5)
        tk.Button(toolbar, text="🗑️ Delete Selected", bg="#333", fg="#fff",
                  font=("Helvetica", 10), command=self.delete_selected).pack(side="left", padx=5)
        
        # Search
        tk.Label(toolbar, text="Search:", bg="#e8f1ff").pack(side="left", padx=(20,5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda a,b,c: self.load_resources())
        tk.Entry(toolbar, textvariable=self.search_var, width=30).pack(side="left")
        
        # Treeview
        columns = ("ID", "Title", "Category", "Filename", "Downloads", "Uploaded", "Type")
        self.tree = ttk.Treeview(self.main_frame, columns=columns, show="headings")
        
        # Define headings
        self.tree.heading("ID", text="ID")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Category", text="Category")
        self.tree.heading("Filename", text="Filename")
        self.tree.heading("Downloads", text="Downloads")
        self.tree.heading("Uploaded", text="Upload Date")
        self.tree.heading("Type", text="Type")
        
        # Column widths
        self.tree.column("ID", width=50)
        self.tree.column("Title", width=200)
        self.tree.column("Category", width=100)
        self.tree.column("Filename", width=150)
        self.tree.column("Downloads", width=80)
        self.tree.column("Uploaded", width=100)
        self.tree.column("Type", width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.load_resources()
    
    def load_resources(self):
        """Load resources into treeview"""
        for row in self.tree.get_children():
            self.tree.delete(row)
        
        search = self.search_var.get().strip()
        query = "SELECT id, title, category, filename, download_count, created_at, file_type FROM resources"
        params = []
        
        if search:
            query += " WHERE title LIKE ? OR description LIKE ?"
            params.extend([f'%{search}%', f'%{search}%'])
        
        query += " ORDER BY created_at DESC"
        
        rows = self.db.fetch_all(query, params)
        
        for r in rows:
            self.tree.insert("", "end", values=r)
    
    def upload_resource(self):
        """Upload a new resource"""
        from tkinter import filedialog, messagebox, simpledialog
        import os
        import shutil
        from datetime import datetime

        # Select file
        filepath = filedialog.askopenfilename(
            title="Select Resource File",
            filetypes=[
                ("All Supported", "*.pdf *.docx *.mp3 *.mp4 *.jpg *.png *.pptx *.xlsx"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx"),
                ("Audio", "*.mp3"),
                ("Video", "*.mp4"),
                ("Images", "*.jpg *.png"),
                ("PowerPoint", "*.pptx"),
                ("Excel", "*.xlsx")
            ]
        )

        if not filepath:
            return  # user cancelled

        # Get file info
        filename = os.path.basename(filepath)
        file_size = os.path.getsize(filepath)
        file_type = filename.split('.')[-1].lower()

        # Create dialog for metadata
        dialog = tk.Toplevel(self.parent)
        dialog.title("Resource Details")
        dialog.geometry("400x350")
        dialog.transient(self.parent)
        dialog.grab_set()

        tk.Label(dialog, text="Title:").pack(pady=(10,0))
        title_entry = tk.Entry(dialog, width=40)
        title_entry.pack(pady=5)

        tk.Label(dialog, text="Description:").pack(pady=(10,0))
        desc_text = tk.Text(dialog, height=4, width=40)
        desc_text.pack(pady=5)

        tk.Label(dialog, text="Category:").pack(pady=(10,0))
        category_combo = ttk.Combobox(dialog, values=["Sermons", "Bible Studies", "Forms", "Music", "Videos", "Other"])
        category_combo.pack(pady=5)
        category_combo.set("Sermons")  # default

        def save():
            title = title_entry.get().strip()
            description = desc_text.get("1.0", "end-1c").strip()
            category = category_combo.get()

            if not title:
                messagebox.showerror("Error", "Title is required")
                return

            # Copy file to upload folder
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads/resources')
            os.makedirs(upload_dir, exist_ok=True)

            # Generate unique filename to avoid collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            dest_path = os.path.join(upload_dir, safe_filename)

            shutil.copy2(filepath, dest_path)

            # Insert into database
            db = DatabaseManager()
            db.execute_query("""
                INSERT INTO resources (title, description, category, filename, file_path, file_size, file_type, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, description, category, filename, safe_filename, file_size, file_type, self.user_id))

            dialog.destroy()
            self.load_resources()
            messagebox.showinfo("Success", "Resource uploaded successfully")

        tk.Button(dialog, text="Save", command=save, bg="#d62828", fg="white", width=10).pack(pady=10)
        tk.Button(dialog, text="Cancel", command=dialog.destroy, width=10).pack()
    
    def edit_selected(self):
        """Edit selected resource"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a resource to edit")
            return
        
        # Get resource ID
        resource_id = self.tree.item(selected[0])['values'][0]
        
        # Fetch current data
        resource = self.db.fetch_one("SELECT title, description, category FROM resources WHERE id=?", (resource_id,))
        
        if not resource:
            return
        
        # Edit dialog (similar to upload but with pre-filled values)
        dialog = tk.Toplevel(self.parent)
        dialog.title("Edit Resource")
        dialog.geometry("400x300")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        tk.Label(dialog, text="Title:").pack(pady=(10,0))
        title_entry = tk.Entry(dialog, width=40)
        title_entry.insert(0, resource[0])
        title_entry.pack(pady=5)
        
        tk.Label(dialog, text="Description:").pack(pady=(10,0))
        desc_text = tk.Text(dialog, height=4, width=40)
        desc_text.insert("1.0", resource[1] or "")
        desc_text.pack(pady=5)
        
        tk.Label(dialog, text="Category:").pack(pady=(10,0))
        category_combo = ttk.Combobox(dialog, values=["Sermons", "Bible Studies", "Forms", "Music", "Videos", "Other"])
        category_combo.set(resource[2] or "")
        category_combo.pack(pady=5)
        
        def save():
            title = title_entry.get().strip()
            description = desc_text.get("1.0", "end-1c").strip()
            category = category_combo.get()
            
            if not title:
                messagebox.showerror("Error", "Title is required")
                return
            
            self.db.execute_query("""
                UPDATE resources SET title=?, description=?, category=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (title, description, category, resource_id))
            
            dialog.destroy()
            self.load_resources()
            messagebox.showinfo("Success", "Resource updated successfully")
        
        tk.Button(dialog, text="Save", command=save, bg="#d62828", fg="#white").pack(pady=10)
        tk.Button(dialog, text="Cancel", command=dialog.destroy).pack()
    
    def delete_selected(self):
        """Delete selected resources"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Please select resources to delete")
            return
        
        if not messagebox.askyesno("Confirm Delete", "Delete selected resources?"):
            return
        
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads/resources')
        
        for item in selected:
            resource_id = self.tree.item(item)['values'][0]
            
            # Get file path before deleting
            file_info = self.db.fetch_one("SELECT file_path FROM resources WHERE id=?", (resource_id,))
            if file_info:
                filepath = os.path.join(upload_dir, file_info[0])
                if os.path.exists(filepath):
                    os.remove(filepath)
            
            self.db.execute_query("DELETE FROM resources WHERE id=?", (resource_id,))
        
        self.load_resources()
        messagebox.showinfo("Success", f"{len(selected)} resource(s) deleted")