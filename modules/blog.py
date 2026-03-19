import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager

# --- BLUE PROFESSIONAL PALETTE ---
COLOR_BG = "#eff6ff"          # Very Light Blue (Main Background)
COLOR_CARD = "#ffffff"        # White (Content Cards)
COLOR_HEADER = "#1e40af"      # Dark Blue (Treeview Header)
COLOR_PRIMARY = "#2563eb"     # Bright Blue (Primary Actions)
COLOR_PRIMARY_HOVER = "#1d4ed8" 
COLOR_DANGER = "#dc2626"      # Red (Delete)
COLOR_SUCCESS = "#059669"     # Green
COLOR_TEXT_MAIN = "#1e3a8a"   # Navy Blue Text
COLOR_TEXT_MUTED = "#64748b"  # Slate Text
BORDER_COLOR = "#bfdbfe"      # Light Blue Border

# --- FONTS ---
FONT_HEADER = ("Segoe UI", 11, "bold")
FONT_BODY = ("Segoe UI", 10)
FONT_READING = ("Georgia", 11)

class BlogModule:
    def __init__(self, parent, user_id=None, branch_id=None):
        self.parent = parent
        self.user_id = user_id
        self.branch_id = branch_id
        self.current_post_id = None
        
        self._setup_styles()
        
        # Main Container
        self.main_frame = tk.Frame(parent, bg=COLOR_BG)
        self.main_frame.pack(fill="both", expand=True, padx=25, pady=25)

        self.setup_ui()
        
        # Load posts AFTER UI is fully built
        self.load_posts()

        # --- SCROLL FIX PRIORITY 1: BIND TO TREEVIEW DIRECTLY ---
        self.tree.bind("<MouseWheel>", self._handle_scroll_tree)
        self.tree.bind("<Button-4>", self._handle_scroll_tree)
        self.tree.bind("<Button-5>", self._handle_scroll_tree)

        # --- SCROLL FIX PRIORITY 2: BIND TO PARENT (BACKUP) ---
        self.parent.bind("<MouseWheel>", self._handle_scroll_parent)
        self.parent.bind("<Button-4>", self._handle_scroll_parent)
        self.parent.bind("<Button-5>", self._handle_scroll_parent)

    def _setup_styles(self):
        """Configures the Blue Theme."""
        style = ttk.Style()
        style.theme_use('clam') 

        # Treeview
        style.configure("BlueTree.Treeview", 
                        background=COLOR_CARD, 
                        foreground=COLOR_TEXT_MAIN, 
                        rowheight=40, 
                        fieldbackground=COLOR_CARD,
                        borderwidth=0,
                        font=FONT_BODY)
        style.configure("BlueTree.Treeview.Heading", 
                        background=COLOR_HEADER, 
                        foreground="white", 
                        relief="flat", 
                        font=("Segoe UI", 10, "bold"))
        style.map("BlueTree.Treeview", 
                  background=[('selected', COLOR_PRIMARY)], 
                  foreground=[('selected', 'white')])

        # Buttons
        style.configure("Primary.TButton", 
                        background=COLOR_PRIMARY, 
                        foreground='white', 
                        borderwidth=0, 
                        focuscolor='none',
                        padding=(12, 8))
        style.map("Primary.TButton", background=[('active', COLOR_PRIMARY_HOVER)])

        style.configure("Danger.TButton", 
                        background=COLOR_DANGER, 
                        foreground='white', 
                        borderwidth=0, 
                        focuscolor='none',
                        padding=(12, 8))
        style.map("Danger.TButton", background=[('active', '#b91c1c')])

        style.configure("Secondary.TButton", 
                        background="white", 
                        foreground=COLOR_PRIMARY, 
                        borderwidth=1, 
                        bordercolor=COLOR_PRIMARY,
                        focuscolor='none',
                        padding=(12, 8))

    def setup_ui(self):
        # --- HEADER & TOOLBAR ---
        header_frame = tk.Frame(self.main_frame, bg=COLOR_BG)
        header_frame.pack(fill="x", pady=(0, 20))

        # Title
        tk.Label(header_frame, text="Blog Management", font=("Segoe UI", 22, "bold"), 
                 bg=COLOR_BG, fg=COLOR_HEADER).pack(side="left", pady=(0, 15))

        # Buttons
        btn_frame = tk.Frame(header_frame, bg=COLOR_BG)
        btn_frame.pack(side="left", padx=(20, 0), pady=(0, 15))

        ttk.Button(btn_frame, text="+ New Post", style="Primary.TButton", 
                   command=self.new_post).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Edit", style="Secondary.TButton", 
                   command=self.edit_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", style="Danger.TButton", 
                   command=self.delete_selected).pack(side="left", padx=5)

        # Right Side: Search & Filter
        right_frame = tk.Frame(header_frame, bg=COLOR_BG)
        right_frame.pack(side="right", fill="y", pady=(0, 15))

        # Filter Dropdown
        self.status_filter = tk.StringVar(value="All")
        filter_cb = ttk.Combobox(right_frame, textvariable=self.status_filter, 
                                 values=["All", "Published", "Draft"], state="readonly", width=10)
        filter_cb.pack(side="left", padx=(0, 10), ipady=2)
        filter_cb.bind("<<ComboboxSelected>>", lambda e: self.load_posts())

        # Search Bar
        search_frame = tk.Frame(right_frame, bg="white", highlightbackground=BORDER_COLOR, highlightthickness=1)
        search_frame.pack(side="right")
        
        self.search_var = tk.StringVar()
        # Bind trace AFTER UI setup
        self.search_var.trace_add("write", lambda *args: self.load_posts())
        
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=FONT_BODY, 
                                bg="white", fg=COLOR_TEXT_MAIN, bd=0, highlightthickness=0, width=20)
        search_entry.pack(side="left", padx=10, pady=6, ipady=2)
        search_entry.insert(0, "Search...")
        search_entry.bind('<FocusIn>', lambda e: search_entry.delete(0, 'end') if search_entry.get() == "Search..." else None)

        # --- TABLE CONTAINER ---
        table_card = tk.Frame(self.main_frame, bg=COLOR_CARD, highlightbackground=COLOR_PRIMARY, highlightthickness=1)
        table_card.pack(fill="both", expand=True)

        cols = ("ID", "Title", "Category", "Author", "Status")
        self.tree = ttk.Treeview(table_card, columns=cols, show="headings", selectmode="browse", style="BlueTree.Treeview")

        # Columns
        self.tree.heading("ID", text="ID")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.heading("Title", text="Post Title")
        self.tree.column("Title", width=300, anchor="w")
        self.tree.heading("Category", text="Category")
        self.tree.column("Category", width=120, anchor="center")
        self.tree.heading("Author", text="Author")
        self.tree.column("Author", width=120, anchor="center")
        self.tree.heading("Status", text="Status")
        self.tree.column("Status", width=120, anchor="center")

        # Scrollbar
        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_card.grid_rowconfigure(0, weight=1)
        table_card.grid_columnconfigure(0, weight=1)

        # Striped Rows
        self.tree.tag_configure('odd', background=COLOR_CARD)
        self.tree.tag_configure('even', background='#f0f9ff') 

        # --- DOUBLE CLICK TO EDIT ---
        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    # --- SCROLLING LOGIC ---
    def _handle_scroll_tree(self, event):
        """Direct handler on the tree. Stops event from bubbling up."""
        if event.delta:
            self.tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
        else:
            if event.num == 4: self.tree.yview_scroll(-1, "units")
            elif event.num == 5: self.tree.yview_scroll(1, "units")
        return "break"

    def _handle_scroll_parent(self, event):
        """Backup handler on parent. Checks if mouse is over tree."""
        x, y = event.x_root, event.y_root
        widget = self.parent.winfo_containing(x, y)
        
        is_over_tree = False
        if widget:
            check_widget = widget
            while check_widget:
                if check_widget == self.tree:
                    is_over_tree = True
                    break
                check_widget = check_widget.master
        
        if is_over_tree:
            if event.delta:
                self.tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                if event.num == 4: self.tree.yview_scroll(-1, "units")
                elif event.num == 5: self.tree.yview_scroll(1, "units")
            return "break"

    def load_posts(self):
        # SAFETY CHECK: Prevent crash if UI isn't fully built yet
        if not hasattr(self, 'tree'):
            return

        for row in self.tree.get_children():
            self.tree.delete(row)
        
        db = DatabaseManager()
        
        # --- FIX: Handle Placeholder Text ---
        raw_search = self.search_var.get().strip()
        # If the text is the placeholder, treat it as empty
        if raw_search == "Search...":
            raw_search = ""
            
        search_val = f"%{raw_search}%"
        
        filter_val = self.status_filter.get()
        
        # Dynamic Query based on Filter
        if filter_val == "Published":
            status_query = " AND is_published = 1"
        elif filter_val == "Draft":
            status_query = " AND is_published = 0"
        else:
            status_query = ""
        
        query = f"""
            SELECT id, title, category, author, is_published 
            FROM blog_posts 
            WHERE (title LIKE ? OR category LIKE ?) {status_query}
            ORDER BY id DESC
        """
        rows = db.fetch_all(query, (search_val, search_val))
        
        for index, r in enumerate(rows):
            status = "🟢 Published" if r[4] else "⚪ Draft"
            tag = 'even' if index % 2 == 0 else 'odd'
            self.tree.insert("", "end", values=(r[0], r[1], r[2], r[3], status), tags=(tag,))

    # --- PREVIEW LOGIC ---
    def preview_selected(self):
        selected = self.tree.selection()
        if not selected: return
        self._edit_window(self.tree.item(selected[0], "values")[0], read_only=True)

    def show_preview_window(self, data):
        pass

    # --- CRUD ACTIONS ---
    def new_post(self):
        self._edit_window()

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            return messagebox.showwarning("Selection", "Please select a post to edit.")
        self._edit_window(self.tree.item(selected[0], "values")[0])

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected: return
        if messagebox.askyesno("Confirm Delete", "Delete this post?"):
            post_id = self.tree.item(selected[0], "values")[0]
            db = DatabaseManager()
            db.execute_query("DELETE FROM blog_posts WHERE id=?", (post_id,))
            self.load_posts()

    def _edit_window(self, post_id=None, read_only=False):
        """Editor with Fixed Save Button Position and Fixed Scrolling."""
        self.current_post_id = post_id
        win = tk.Toplevel(self.parent)
        win_title = "Post Preview" if read_only else ("Edit Post" if post_id else "New Post")
        win.title(win_title)
        win.geometry("750x700") 
        win.configure(bg=COLOR_BG)
        win.grab_set()
        
        # Center
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (750 // 2)
        y = (win.winfo_screenheight() // 2) - (700 // 2)
        win.geometry(f"750x700+{x}+{y}")

        # Scrollable Container
        canvas = tk.Canvas(win, bg=COLOR_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(win, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=COLOR_BG)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=750)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Content
        main_container = tk.Frame(scrollable_frame, bg=COLOR_BG, padx=30, pady=30)
        main_container.pack(fill="x")

        # Title
        tk.Label(main_container, text="Post Title", bg=COLOR_BG, font=FONT_HEADER, fg=COLOR_TEXT_MAIN).pack(anchor="w")
        title_ent = tk.Entry(main_container, font=("Segoe UI", 12), bd=1, relief="solid", 
                             highlightbackground=COLOR_PRIMARY, highlightcolor=COLOR_PRIMARY, highlightthickness=1)
        title_ent.pack(fill="x", pady=(0, 15), ipady=6)
        self.title_ent = title_ent

        # Meta Grid
        meta_frame = tk.Frame(main_container, bg=COLOR_BG)
        meta_frame.pack(fill="x", pady=(0, 15))
        
        tk.Label(meta_frame, text="Author", bg=COLOR_BG, font=FONT_HEADER, fg=COLOR_TEXT_MAIN).grid(row=0, column=0, sticky="w")
        auth_ent = tk.Entry(meta_frame, font=FONT_BODY, bd=1, relief="solid", 
                            highlightbackground=COLOR_PRIMARY, highlightcolor=COLOR_PRIMARY, highlightthickness=1)
        auth_ent.grid(row=1, column=0, sticky="ew", padx=(0, 10), ipady=5)
        self.author_ent = auth_ent

        tk.Label(meta_frame, text="Category", bg=COLOR_BG, font=FONT_HEADER, fg=COLOR_TEXT_MAIN).grid(row=0, column=1, sticky="w")
        cat_ent = tk.Entry(meta_frame, font=FONT_BODY, bd=1, relief="solid", 
                           highlightbackground=COLOR_PRIMARY, highlightcolor=COLOR_PRIMARY, highlightthickness=1)
        cat_ent.grid(row=1, column=1, sticky="ew", ipady=5)
        self.cat_ent = cat_ent
        meta_frame.columnconfigure(0, weight=1)
        meta_frame.columnconfigure(1, weight=1)

        # Body Text
        tk.Label(main_container, text="Content", bg=COLOR_BG, font=FONT_HEADER, fg=COLOR_TEXT_MAIN).pack(anchor="w")
        
        text_container = tk.Frame(main_container, bg=COLOR_CARD, highlightbackground=COLOR_PRIMARY, highlightthickness=1)
        text_container.pack(fill="x", pady=(0, 20))
        
        self.body_txt = tk.Text(text_container, font=FONT_BODY, wrap="word", bd=0, highlightthickness=0, 
                                padx=10, pady=10, bg=COLOR_CARD, height=20)
        self.body_txt.pack(fill="both", expand=True)

        # Save Button
        if not read_only:
            btn = tk.Button(main_container, text="💾 Save Post", bg=COLOR_PRIMARY, fg="white", font=FONT_HEADER,
                            command=lambda: self.save_post(win), relief="flat", cursor="hand2", padx=30, pady=10)
            btn.pack(anchor="e")
        else:
            btn = tk.Button(main_container, text="Close", bg=COLOR_TEXT_MAIN, fg="white", font=FONT_HEADER,
                            command=win.destroy, relief="flat", cursor="hand2", padx=30, pady=10)
            btn.pack(anchor="e")

        # Fixed Scrolling (Bind to 'win' not 'bind_all')
        def _on_editor_scroll(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        win.bind("<MouseWheel>", _on_editor_scroll)
        win.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        win.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))

        # Load Data
        if post_id:
            db = DatabaseManager()
            data = db.fetch_one("SELECT title, content, author, category FROM blog_posts WHERE id=?", (post_id,))
            if data:
                self.title_ent.insert(0, data[0])
                self.body_txt.insert("1.0", data[1])
                self.author_ent.insert(0, data[2] if data[2] else "")
                self.cat_ent.insert(0, data[3] if data[3] else "")
            
            if read_only:
                title_ent.config(state="disabled")
                auth_ent.config(state="disabled")
                cat_ent.config(state="disabled")
                self.body_txt.config(state="disabled")

    def save_post(self, window):
        title = self.title_ent.get().strip()
        content = self.body_txt.get("1.0", "end-1c").strip()
        author = self.author_ent.get().strip()
        category = self.cat_ent.get().strip()
        
        if not title or not content:
            return messagebox.showerror("Error", "Title and Content are required.")

        db = DatabaseManager()
        if self.current_post_id:
            db.execute_query("UPDATE blog_posts SET title=?, content=?, author=?, category=? WHERE id=?", 
                             (title, content, author, category, self.current_post_id))
        else:
            db.execute_query("INSERT INTO blog_posts (title, content, author, category, is_published) VALUES (?, ?, ?, ?, 1)", 
                             (title, content, author, category))
        
        window.destroy()
        self.load_posts()