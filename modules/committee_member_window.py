# modules/committee_member_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from database import DatabaseManager
from datetime import datetime
import re

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
    "sidebar": "#0b3d91"
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

# ================== COMMITTEE MEMBER WINDOW ==================
class CommitteeMemberWindow:
    def __init__(self, parent, member_internal_id, member_display_id, member_name):
        self.win = tk.Toplevel(parent)
        self.win.title(f"Committees for {member_name} ({member_display_id})")
        self.win.geometry("700x450")
        self.win.minsize(600, 400)
        self.win.configure(bg=COLORS["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        self.member_id = member_internal_id

        # Title
        tk.Label(self.win, text=f"Manage committees for {member_name}", font=("Helvetica", 12, "bold"),
                 bg=COLORS["bg"], fg=COLORS["accent"]).pack(pady=PAD)

        # Main content frame (expands)
        main_frame = tk.Frame(self.win, bg=COLORS["bg"])
        main_frame.pack(fill="both", expand=True, padx=PAD, pady=SMALL_PAD)

        # Left: Available committees
        left_frame = tk.Frame(main_frame, bg=COLORS["bg"])
        left_frame.pack(side="left", fill="both", expand=True, padx=SMALL_PAD)

        tk.Label(left_frame, text="Available Committees", bg=COLORS["bg"], font=FONT_TEXT).pack(anchor="w")
        self.avail_listbox = tk.Listbox(left_frame, height=10, font=FONT_TEXT, selectmode="single",
                                         bg="white", fg="black", relief="solid", bd=1)
        self.avail_listbox.pack(fill="both", expand=True, pady=SMALL_PAD)

        # Right: Member's committees
        right_frame = tk.Frame(main_frame, bg=COLORS["bg"])
        right_frame.pack(side="right", fill="both", expand=True, padx=SMALL_PAD)

        tk.Label(right_frame, text="Member's Committees", bg=COLORS["bg"], font=FONT_TEXT).pack(anchor="w")
        self.member_listbox = tk.Listbox(right_frame, height=10, font=FONT_TEXT, selectmode="single",
                                          bg="white", fg="black", relief="solid", bd=1)
        self.member_listbox.pack(fill="both", expand=True, pady=SMALL_PAD)

        # Button frame (fixed at bottom)
        btn_frame = tk.Frame(self.win, bg=COLORS["bg"])
        btn_frame.pack(fill="x", pady=PAD)

        self.add_btn = tk.Button(btn_frame, text="➕ Add to Committee", bg=COLORS["accent"], fg="white",
                                  font=FONT_TEXT, command=self.add_to_committee)
        self.add_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(self.add_btn, COLORS["accent"], COLORS["accent_light"])
        ToolTip(self.add_btn, "Add the selected committee to this member")

        self.remove_btn = tk.Button(btn_frame, text="➖ Remove from Committee", bg=COLORS["red"], fg="white",
                                     font=FONT_TEXT, command=self.remove_from_committee)
        self.remove_btn.pack(side="left", padx=SMALL_PAD)
        self._add_hover(self.remove_btn, COLORS["red"], COLORS["red_light"])
        ToolTip(self.remove_btn, "Remove the selected committee from this member")

        self.close_btn = tk.Button(btn_frame, text="Close", bg=COLORS["gray"], fg="white",
                                    font=FONT_TEXT, command=self.win.destroy)
        self.close_btn.pack(side="right", padx=SMALL_PAD)
        self._add_hover(self.close_btn, COLORS["gray"], COLORS["gray_light"])
        ToolTip(self.close_btn, "Close this window")

        self.load_data()

    def _add_hover(self, button, normal_bg, hover_bg):
        button.bind("<Enter>", lambda e: button.config(bg=hover_bg))
        button.bind("<Leave>", lambda e: button.config(bg=normal_bg))

    def load_data(self):
        db = DatabaseManager()
        # All committees
        all_committees = db.fetch_all("SELECT id, name FROM committees ORDER BY name")
        # Committees this member belongs to
        member_committees = db.fetch_all("""
            SELECT c.id, c.name
            FROM committee_members cm
            JOIN committees c ON cm.committee_id = c.id
            WHERE cm.member_id = ?
        """, (self.member_id,))

        self.avail_listbox.delete(0, tk.END)
        self.member_listbox.delete(0, tk.END)

        self.all_committees = all_committees
        self.member_committee_ids = [cid for cid, _ in member_committees]

        for cid, name in all_committees:
            if cid not in self.member_committee_ids:
                self.avail_listbox.insert(tk.END, f"{name} (ID:{cid})")
        for cid, name in member_committees:
            self.member_listbox.insert(tk.END, f"{name} (ID:{cid})")

    def add_to_committee(self):
        selection = self.avail_listbox.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Select a committee from the left list.")
            return
        line = self.avail_listbox.get(selection[0])
        match = re.search(r'\(ID:(\d+)\)', line)
        if not match:
            return
        committee_id = int(match.group(1))

        # Custom role selection dialog
        role = self._get_role_dialog()
        if role is None:  # cancelled
            return

        db = DatabaseManager()
        joined = datetime.now().strftime("%Y-%m-%d")
        try:
            db.execute_query(
                "INSERT INTO committee_members (committee_id, member_id, role, joined_date) VALUES (?,?,?,?)",
                (committee_id, self.member_id, role, joined)
            )
            show_toast(self.win, "Member added to committee")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Error", f"Could not add: {e}")

    def remove_from_committee(self):
        selection = self.member_listbox.curselection()
        if not selection:
            messagebox.showwarning("No selection", "Select a committee from the right list.")
            return
        line = self.member_listbox.get(selection[0])
        match = re.search(r'\(ID:(\d+)\)', line)
        if not match:
            return
        committee_id = int(match.group(1))

        if not messagebox.askyesno("Confirm", "Remove member from this committee?"):
            return

        db = DatabaseManager()
        db.execute_query(
            "DELETE FROM committee_members WHERE committee_id=? AND member_id=?",
            (committee_id, self.member_id)
        )
        show_toast(self.win, "Member removed from committee")
        self.load_data()

    def _get_role_dialog(self):
        """Create a custom dialog to select or type a role."""
        dialog = tk.Toplevel(self.win)
        dialog.title("Select Role")
        dialog.geometry("350x150")
        dialog.configure(bg=COLORS["bg"])
        dialog.transient(self.win)
        dialog.grab_set()
        dialog.resizable(False, False)

        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        tk.Label(dialog, text="Enter or select a role for this member:", bg=COLORS["bg"], font=("Helvetica", 10)).pack(pady=10)

        # Combobox with predefined roles – user can type as well
        predefined_roles = ["Member", "Secretary", "Treasurer", "Chairperson", "Vice Chair"]
        role_var = tk.StringVar()
        role_combo = ttk.Combobox(dialog, textvariable=role_var, values=predefined_roles, width=25)
        role_combo.pack(pady=5)
        role_combo.set("Member")

        result = None

        def on_ok():
            nonlocal result
            role = role_var.get().strip()
            if not role:
                messagebox.showerror("Error", "Role cannot be empty.")
                return
            result = role
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = tk.Frame(dialog, bg=COLORS["bg"])
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="OK", bg=COLORS["accent"], fg="white", width=10,
                  command=on_ok).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", bg=COLORS["gray"], fg="white", width=10,
                  command=on_cancel).pack(side="left", padx=5)

        dialog.wait_window()
        return result