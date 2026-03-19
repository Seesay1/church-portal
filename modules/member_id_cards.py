import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os
import qrcode
import io
from database import DatabaseManager

try:
    from config import FONT_TEXT, LOGO_PATH, CHURCH_NAME, PHOTOS_PATH
except ImportError:
    FONT_TEXT = ("Helvetica", 10)
    LOGO_PATH = "logo.png"
    CHURCH_NAME = "PCG Mt. Zion Congregation"
    PHOTOS_PATH = "photos"

# Card dimensions (credit card size)
CARD_WIDTH = 86 * mm
CARD_HEIGHT = 54 * mm

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

class MemberIDCards:
    def __init__(self, root, user_id=None, branch_id=None):
        self.root = root
        self.root.configure(bg="#e8f1ff")
        self.user_id = user_id
        self.branch_id = branch_id

        # Create Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Generate ID Cards
        self.generate_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.generate_frame, text="🆔 Generate ID Cards")

        # Tab 2: History
        self.history_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.history_frame, text="📋 History")

        # Tab 3: Statistics
        self.stats_frame = tk.Frame(self.notebook, bg="#e8f1ff")
        self.notebook.add(self.stats_frame, text="📊 Statistics")

        self.setup_generate_tab()
        self.setup_history_tab()
        self.setup_stats_tab()

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

        self.clear_btn = tk.Button(toolbar, text="🗑️ Clear Selection", bg="#333", fg="#fff",
                                   font=FONT_TEXT, command=self.clear_selection)
        self.clear_btn.pack(side="left", padx=5)
        ToolTip(self.clear_btn, "Clear selected members")

        self.gen_btn = tk.Button(toolbar, text="🖨️ Generate Cards", bg="#d62828", fg="#fff",
                                 font=("Helvetica", 11, "bold"), command=self.generate_cards)
        self.gen_btn.pack(side="left", padx=5)
        ToolTip(self.gen_btn, "Generate ID cards for selected members")

        # Main content area with PanedWindow
        paned = ttk.PanedWindow(self.generate_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # Left pane (member selection and options)
        left_pane = tk.Frame(paned, bg="#e8f1ff")
        paned.add(left_pane, weight=1)

        # Search box
        search_frame = tk.Frame(left_pane, bg="#e8f1ff")
        search_frame.pack(fill="x", pady=5)
        tk.Label(search_frame, text="Search:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda a,b,c: self.filter_member_list())
        tk.Entry(search_frame, textvariable=self.search_var, font=FONT_TEXT, width=25).pack(side="left", padx=5)
        tk.Button(search_frame, text="✖", bg="#e8f1ff", fg="#333", font=("Helvetica", 10),
                  bd=0, command=self.clear_search).pack(side="left", padx=2)

        # Listbox with scrollbar
        listbox_frame = tk.Frame(left_pane, bg="#e8f1ff")
        listbox_frame.pack(fill="both", expand=True, pady=5)
        self.member_listbox = tk.Listbox(listbox_frame, selectmode="multiple", height=12, font=FONT_TEXT)
        self.member_listbox.pack(side="left", fill="both", expand=True)
        self.member_listbox.bind("<<ListboxSelect>>", self.update_preview)

        # --- Mouse wheel and focus bindings to prevent whole window scrolling ---
        def _on_listbox_enter(event):
            self.member_listbox.focus_set()

        def _on_listbox_mousewheel(event):
            self.member_listbox.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"

        self.member_listbox.bind("<Enter>", _on_listbox_enter)
        self.member_listbox.bind("<MouseWheel>", _on_listbox_mousewheel)
        # ------------------------------------------------------------------------

        scrollbar = tk.Scrollbar(listbox_frame, orient="vertical", command=self.member_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.member_listbox.config(yscrollcommand=scrollbar.set)

        # Card design options
        options_frame = tk.LabelFrame(left_pane, text="Card Options", bg="#e8f1ff", font=FONT_TEXT, padx=10, pady=10)
        options_frame.pack(fill="x", pady=10)

        # Design type
        tk.Label(options_frame, text="Design:", bg="#e8f1ff", font=FONT_TEXT).grid(row=0, column=0, sticky="w", pady=5)
        self.design_var = tk.StringVar(value="Standard")
        design_combo = ttk.Combobox(options_frame, textvariable=self.design_var,
                                     values=["Standard", "With Barcode", "With QR Code"],
                                     state="readonly", width=15)
        design_combo.grid(row=0, column=1, sticky="w", pady=5, padx=10)

        # Output format
        tk.Label(options_frame, text="Format:", bg="#e8f1ff", font=FONT_TEXT).grid(row=1, column=0, sticky="w", pady=5)
        self.format_var = tk.StringVar(value="PDF (Single per page)")
        format_combo = ttk.Combobox(options_frame, textvariable=self.format_var,
                                     values=["PDF (Single per page)", "PDF (4 per page)"],
                                     state="readonly", width=20)
        format_combo.grid(row=1, column=1, sticky="w", pady=5, padx=10)

        # Right pane (preview)
        right_pane = tk.Frame(paned, bg="#e8f1ff")
        paned.add(right_pane, weight=1)

        # Preview Frame
        preview_frame = tk.LabelFrame(right_pane, text="Preview (First Selected Member)", bg="white", padx=10, pady=10)
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.preview_canvas = tk.Canvas(preview_frame, width=400, height=250, bg="white", highlightthickness=1)
        self.preview_canvas.pack(expand=True)

        # Store all members for filtering
        self.all_members = []  # list of (display_text, member_id, full_name)

    def filter_member_list(self):
        """Filter members based on search text."""
        search_term = self.search_var.get().strip().lower()
        self.member_listbox.delete(0, tk.END)
        for display, mid, name in self.all_members:
            if search_term in display.lower():
                self.member_listbox.insert(tk.END, display)

    def clear_search(self):
        self.search_var.set("")
        self.filter_member_list()

    def load_member_list(self):
        """Populate listbox with members."""
        self.member_listbox.delete(0, tk.END)
        self.all_members.clear()
        db = DatabaseManager()
        members = db.fetch_all("SELECT member_id, full_name FROM members ORDER BY full_name")
        self.member_items = []  # store (member_id, full_name) for selected indices
        for mid, name in members:
            if name and mid:
                display = f"{name} ({mid})"
                self.member_listbox.insert(tk.END, display)
                self.all_members.append((display, mid, name))
                self.member_items.append((mid, name))
        self.member_listbox.selection_clear(0, tk.END)

    def update_preview(self, event=None):
        """Draw a mockup of the first selected member's card."""
        self.preview_canvas.delete("all")
        selected = self.member_listbox.curselection()
        if not selected:
            return
        idx = selected[0]
        # Get actual member from all_members using listbox text
        display_text = self.member_listbox.get(idx)
        for disp, mid, name in self.all_members:
            if disp == display_text:
                member_id = mid
                full_name = name
                break
        else:
            return

        # Draw a simple card preview
        self.preview_canvas.create_rectangle(10, 10, 390, 240, outline="blue", width=2)
        self.preview_canvas.create_text(200, 40, text=CHURCH_NAME, font=("Helvetica", 12, "bold"), fill="#1f4fa3")
        self.preview_canvas.create_text(200, 80, text=full_name, font=("Helvetica", 14, "bold"))
        self.preview_canvas.create_text(200, 120, text=f"ID: {member_id}", font=("Helvetica", 11))
        self.preview_canvas.create_text(200, 160, text="Photo placeholder", font=("Helvetica", 9), fill="gray")

    def clear_selection(self):
        self.member_listbox.selection_clear(0, tk.END)
        self.preview_canvas.delete("all")

    def generate_cards(self):
        """Generate ID cards for selected members."""
        selected = self.member_listbox.curselection()
        if not selected:
            messagebox.showerror("Error", "Please select at least one member.")
            return

        design = self.design_var.get()
        output_format = self.format_var.get()

        # Gather member data from selected indices (mapping to actual member_items)
        members_data = []
        db = DatabaseManager()
        for sel_idx in selected:
            display_text = self.member_listbox.get(sel_idx)
            # Find corresponding member in all_members
            for disp, member_id, full_name in self.all_members:
                if disp == display_text:
                    break
            else:
                continue

            member = db.fetch_one("""
                SELECT id, branch_id, group_id, phone, email, photo
                FROM members WHERE member_id=?
            """, (member_id,))
            if not member:
                continue
            mid, branch_id, group_id, phone, email, photo = member

            # Safely get branch name
            branch_name = "N/A"
            if branch_id:
                res = db.fetch_one("SELECT name FROM branches WHERE id=?", (branch_id,))
                if res and res[0]:
                    branch_name = res[0]

            # Safely get group name
            group_name = "N/A"
            if group_id:
                res = db.fetch_one("SELECT name FROM groups WHERE id=?", (group_id,))
                if res and res[0]:
                    group_name = res[0]

            # Photo path
            photo_path = None
            if photo and os.path.exists(photo):
                photo_path = photo

            members_data.append({
                "id": member_id,
                "full_name": full_name,
                "branch": branch_name,
                "group": group_name,
                "phone": phone or "",
                "email": email or "",
                "photo": photo_path,
                "db_id": mid
            })

        if not members_data:
            messagebox.showerror("Error", "No valid member data found.")
            return

        # Output file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save ID Cards As",
            initialfile=f"ID_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        if not file_path:
            return

        try:
            self.generate_pdf(file_path, members_data, design, output_format)

            # Record in history
            generated_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for m in members_data:
                db.execute_query(
                    "INSERT INTO id_cards (member_id, generated_date) VALUES (?,?)",
                    (m["db_id"], generated_date)
                )

            messagebox.showinfo("Success", f"ID cards generated for {len(members_data)} member(s).")
            self.load_history()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to generate:\n{str(e)}\n\nCheck console for details.")

    def generate_pdf(self, file_path, members_data, design, output_format):
        """Generate PDF with professional ID cards using a direct canvas approach."""
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm

        cards_per_page = 4 if "4 per page" in output_format else 1

        # Page dimensions
        page_width, page_height = A4

        # Margins
        left_margin = 10*mm
        right_margin = 10*mm
        top_margin = 15*mm
        bottom_margin = 10*mm

        # Card dimensions
        card_width = CARD_WIDTH
        card_height = CARD_HEIGHT

        # Calculate positions for 2x2 grid (if 4 per page)
        if cards_per_page == 4:
            # Two columns, two rows
            gap_x = (page_width - left_margin - right_margin - 2*card_width) / 3
            gap_y = (page_height - top_margin - bottom_margin - 2*card_height) / 3
        else:
            gap_x = 0
            gap_y = 0

        c = canvas.Canvas(file_path, pagesize=A4)

        for idx, member in enumerate(members_data):
            # Determine position on page
            page_idx = idx % cards_per_page
            if cards_per_page == 4:
                col = page_idx % 2
                row = page_idx // 2
                x = left_margin + col * (card_width + gap_x)
                y = page_height - top_margin - (row+1)*card_height - row*gap_y
            else:
                x = left_margin
                y = page_height - top_margin - card_height

            # Draw the card at (x, y)
            self.draw_card(c, member, design, x, y, card_width, card_height)

            # If we've reached the last card on the page, start a new page
            if (idx + 1) % cards_per_page == 0 and idx < len(members_data) - 1:
                c.showPage()

        c.save()

    def draw_card(self, c, member, design, x, y, card_width, card_height):
        """Draw a single ID card at position (x, y) with given dimensions."""
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        import os
        import qrcode
        import io

        # Background
        c.setFillColor(colors.HexColor("#f0f8ff"))  # light blue
        c.rect(x, y, card_width, card_height, fill=1, stroke=0)

        # Blue border
        c.setStrokeColor(colors.HexColor("#1f4fa3"))
        c.setLineWidth(2)
        c.rect(x+2, y+2, card_width-4, card_height-4, stroke=1, fill=0)

        # Red stripe at bottom
        c.setFillColor(colors.HexColor("#d62828"))
        c.rect(x, y, card_width, 5*mm, fill=1, stroke=0)

        # ----- Logo -----
        if LOGO_PATH and os.path.exists(LOGO_PATH):
            try:
                c.drawImage(LOGO_PATH, x+5*mm, y+card_height-15*mm, width=10*mm, height=10*mm, preserveAspectRatio=True, mask='auto')
            except:
                pass

        # ----- Church Name -----
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#1f4fa3"))
        c.drawString(x+18*mm, y+card_height-11*mm, CHURCH_NAME[:20])

        # ----- Photo -----
        photo_x = x + 5*mm
        photo_y = y + card_height - 40*mm
        photo_w = 20*mm
        photo_h = 25*mm

        if member["photo"] and os.path.exists(member["photo"]):
            try:
                # Draw photo with blue border
                c.setStrokeColor(colors.HexColor("#1f4fa3"))
                c.setLineWidth(0.5)
                c.rect(photo_x-1, photo_y-1, photo_w+2, photo_h+2, stroke=1, fill=0)
                c.drawImage(member["photo"], photo_x, photo_y, width=photo_w, height=photo_h, preserveAspectRatio=True, mask='auto')
            except:
                # Placeholder
                c.setFillColor(colors.lightgrey)
                c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 6)
                c.drawCentredString(photo_x+photo_w/2, photo_y+photo_h/2, "No Photo")
        else:
            # Placeholder
            c.setFillColor(colors.lightgrey)
            c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 6)
            c.drawCentredString(photo_x+photo_w/2, photo_y+photo_h/2, "No Photo")

        # ----- Member Details -----
        details_x = photo_x + photo_w + 5*mm
        details_y = y + card_height - 25*mm
        line_height = 4.5*mm

        # Name
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1f4fa3"))
        c.drawString(details_x, details_y, "Name:")
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(details_x + 15*mm, details_y, member['full_name'][:18])

        # ID
        details_y -= line_height
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1f4fa3"))
        c.drawString(details_x, details_y, "ID:")
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(details_x + 15*mm, details_y, member['id'])

        # Branch
        details_y -= line_height
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1f4fa3"))
        c.drawString(details_x, details_y, "Branch:")
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(details_x + 15*mm, details_y, member['branch'][:15])

        # Group
        details_y -= line_height
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1f4fa3"))
        c.drawString(details_x, details_y, "Group:")
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(details_x + 15*mm, details_y, member['group'][:15])

        # Phone
        details_y -= line_height
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#1f4fa3"))
        c.drawString(details_x, details_y, "Phone:")
        c.setFont("Helvetica", 9)
        c.setFillColor(colors.black)
        c.drawString(details_x + 15*mm, details_y, member['phone'][:12])

        # ----- QR Code (if selected) -----
        if "QR Code" in design:
            qr_x = x + card_width - 20*mm
            qr_y = y + 8*mm
            qr_size = 15*mm
            try:
                qr = qrcode.QRCode(box_size=2, border=1)
                qr.add_data(f"ID: {member['id']}\n{member['full_name']}\n{CHURCH_NAME}")
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="black", back_color="white")
                img_bytes = io.BytesIO()
                qr_img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                c.drawImage(ImageReader(img_bytes), qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')
            except Exception as e:
                print("QR error:", e)
                # Placeholder
                c.setFillColor(colors.lightgrey)
                c.rect(qr_x, qr_y, qr_size, qr_size, fill=1, stroke=0)
                c.setFillColor(colors.black)
                c.setFont("Helvetica", 5)
                c.drawCentredString(qr_x+qr_size/2, qr_y+qr_size/2, "QR\nError")

        # ----- Barcode placeholder -----
        if "Barcode" in design:
            c.setFont("Helvetica", 5)
            c.setFillColor(colors.grey)
            c.drawString(x+card_width-20*mm, y+5*mm, "Barcode")

        # ----- Footer -----
        c.setFont("Helvetica", 6)
        c.setFillColor(colors.grey)
        c.drawString(x+5*mm, y+3*mm, "Sampa, Bono Region")

    # ================== HISTORY TAB ==================
    def setup_history_tab(self):
        # Toolbar
        toolbar = tk.Frame(self.history_frame, bg="#e8f1ff")
        toolbar.pack(fill="x", padx=10, pady=10)

        self.refresh_hist_btn = tk.Button(toolbar, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                                          font=FONT_TEXT, command=self.load_history)
        self.refresh_hist_btn.pack(side="left", padx=5)
        ToolTip(self.refresh_hist_btn, "Refresh history list")

        self.delete_hist_btn = tk.Button(toolbar, text="🗑️ Delete Selected", bg="#333", fg="#fff",
                                         font=FONT_TEXT, width=20, command=self.delete_history)
        self.delete_hist_btn.pack(side="left", padx=5)
        ToolTip(self.delete_hist_btn, "Delete selected history entries")

        # Search by member name
        tk.Label(toolbar, text="Search:", bg="#e8f1ff", font=FONT_TEXT).pack(side="left", padx=5)
        self.history_search_var = tk.StringVar()
        self.history_search_var.trace("w", lambda a,b,c: self.filter_history())
        tk.Entry(toolbar, textvariable=self.history_search_var, font=FONT_TEXT, width=20).pack(side="left", padx=5)

        # Treeview with scrollbars
        tree_frame = tk.Frame(self.history_frame, bg="#e8f1ff")
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical")
        vsb.pack(side="right", fill="y")
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
        hsb.pack(side="bottom", fill="x")

        columns = ("ID", "Member Name", "Generated Date", "DB_ID")
        self.history_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                          yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.config(command=self.history_tree.yview)
        hsb.config(command=self.history_tree.xview)

        widths = [50, 200, 150, 0]
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
            SELECT c.id, m.full_name, c.generated_date, c.id
            FROM id_cards c
            LEFT JOIN members m ON c.member_id = m.id
            ORDER BY c.generated_date DESC
        """
        rows = db.fetch_all(query)

        for r in rows:
            item_id = self.history_tree.insert("", tk.END, values=r)
            self.all_history.append((item_id, r[1] or "", r[2]))

        self.filter_history()

    def filter_history(self):
        search_term = self.history_search_var.get().strip().lower()
        for item_id, member_name, date_str in self.all_history:
            if search_term and search_term not in member_name.lower():
                self.history_tree.detach(item_id)
            else:
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
            cert_id = self.history_tree.item(item)['values'][3]
            db.execute_query("DELETE FROM id_cards WHERE id = ?", (cert_id,))
        self.load_history()
        self.history_tree.selection_remove(self.history_tree.selection())
        messagebox.showinfo("Success", f"{len(selected)} history entries deleted.")

    # ================== STATISTICS TAB ==================
    def setup_stats_tab(self):
        control_frame = tk.Frame(self.stats_frame, bg="#e8f1ff")
        control_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(control_frame, text="ID Cards Statistics", font=("Helvetica", 14, "bold"),
                 bg="#e8f1ff", fg="#1f4fa3").pack(side="left", padx=10)

        self.refresh_stats_btn = tk.Button(control_frame, text="🔄 Refresh", bg="#1f4fa3", fg="#fff",
                                           font=FONT_TEXT, command=self.refresh_stats)
        self.refresh_stats_btn.pack(side="right", padx=5)
        ToolTip(self.refresh_stats_btn, "Refresh statistics")

        # Summary card
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
        # Total count
        total = db.fetch_one("SELECT COUNT(*) FROM id_cards")[0] or 0
        # Monthly data
        data = db.fetch_all("""
            SELECT strftime('%Y-%m', generated_date), COUNT(*)
            FROM id_cards
            WHERE generated_date IS NOT NULL
            GROUP BY strftime('%Y-%m', generated_date)
            ORDER BY 1
        """)

        # Create left frame for summary card, right for chart
        left_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        left_frame.pack(side="left", fill="both", expand=True, padx=5)
        right_frame = tk.Frame(self.stats_charts_frame, bg="#e8f1ff")
        right_frame.pack(side="right", fill="both", expand=True, padx=5)

        # Summary card
        card = tk.Frame(left_frame, bg="white", bd=1, relief="solid", padx=20, pady=20)
        card.pack(expand=True)
        tk.Label(card, text="Total Cards Generated", font=("Helvetica", 14), bg="white").pack()
        tk.Label(card, text=str(total), font=("Helvetica", 28, "bold"), fg="#1f4fa3", bg="white").pack()

        # Bar chart
        if data:
            months = [r[0] for r in data]
            counts = [r[1] for r in data]
            fig = Figure(figsize=(6,4), dpi=100)
            ax = fig.add_subplot(111)
            ax.bar(months, counts, color="#2a9df4")
            ax.set_title("ID Cards Generated per Month")
            ax.set_xlabel("Month")
            ax.set_ylabel("Count")
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            fig.tight_layout()
        else:
            fig = Figure(figsize=(6,4), dpi=100)
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data available", ha='center', va='center')
            ax.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=right_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1200x700")
    app = MemberIDCards(root)
    root.mainloop()