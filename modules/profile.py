import tkinter as tk
from tkinter import messagebox
from database import DatabaseManager, hash_password


# ──────────────────────────────────────────────
# Colour palette  (mirrors login.py)
# ──────────────────────────────────────────────
PRIMARY       = "#1f4fa3"
PRIMARY_DARK  = "#163a7a"
PRIMARY_LIGHT = "#3366cc"
DANGER        = "#d62828"
DANGER_DARK   = "#a01e1e"
SUCCESS       = "#1a7a3a"
WARN          = "#b36200"
BG            = "#e8f1ff"
CARD          = "#ffffff"
TEXT_DARK     = "#1a1a2e"
TEXT_MUTED    = "#666680"
BORDER        = "#c8d6f0"


# ──────────────────────────────────────────────
# Shared UI helpers
# ──────────────────────────────────────────────
def add_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    def on_enter(e):
        widget.config(bg=hover_bg, cursor="hand2")
        if hover_fg:
            widget.config(fg=hover_fg)

    def on_leave(e):
        widget.config(bg=normal_bg)
        if normal_fg:
            widget.config(fg=normal_fg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


class Tooltip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text   = text
        self.delay  = delay
        self._tip   = None
        self._job   = None
        widget.bind("<Enter>",       self._schedule)
        widget.bind("<Leave>",       self._hide)
        widget.bind("<ButtonPress>", self._hide)

    def _schedule(self, event=None):
        self._job = self.widget.after(self.delay, self._show)

    def _show(self):
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        frame = tk.Frame(tw, bg="#2b2b3b", padx=8, pady=4, relief="flat", bd=0)
        frame.pack()
        tk.Label(frame, text=self.text, bg="#2b2b3b", fg="#f0f4ff",
                 font=("Helvetica", 9), justify="left", wraplength=220).pack()

    def _hide(self, event=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self._tip:
            self._tip.destroy()
            self._tip = None


def styled_button(parent, text, command, bg=PRIMARY, fg="white",
                  hover_bg=PRIMARY_DARK, width=None, font=None, **kw):
    opts = dict(
        text=text, command=command,
        bg=bg, fg=fg,
        activebackground=hover_bg, activeforeground=fg,
        relief="flat", bd=0,
        padx=12, pady=8,
        font=font or ("Helvetica", 10, "bold"),
        cursor="hand2",
    )
    if width:
        opts["width"] = width
    btn = tk.Button(parent, **opts, **kw)
    add_hover(btn, bg, hover_bg)
    return btn


def pw_entry_row(parent, label_text, card_bg=CARD):
    """Password row with label, styled entry, and show/hide eye toggle."""
    tk.Label(parent, text=label_text, font=("Helvetica", 10, "bold"),
             bg=card_bg, fg=TEXT_DARK, anchor="w").pack(fill="x")

    row_outer = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    row_outer.pack(fill="x", pady=(3, 10))
    row_inner = tk.Frame(row_outer, bg="#f5f8ff")
    row_inner.pack(fill="x")

    entry = tk.Entry(row_inner, show="*", relief="flat", bd=4,
                     font=("Helvetica", 11), bg="#f5f8ff", width=26)
    entry.pack(side="left", fill="x", expand=True)

    eye_btn = tk.Button(row_inner, text="👁", relief="flat", bd=0,
                        bg="#f5f8ff", cursor="hand2", font=("Helvetica", 11),
                        command=lambda: entry.config(
                            show="" if entry.cget("show") == "*" else "*"
                        ))
    eye_btn.pack(side="right", padx=(0, 4))
    add_hover(eye_btn, "#f5f8ff", "#dce8ff")
    Tooltip(eye_btn, "Show / hide password")

    entry.bind("<FocusIn>",  lambda e: row_outer.config(bg=PRIMARY_LIGHT))
    entry.bind("<FocusOut>", lambda e: row_outer.config(bg=BORDER))

    return entry


# ──────────────────────────────────────────────
# Password strength meter
# ──────────────────────────────────────────────
def evaluate_strength(pw):
    score = 0
    if len(pw) >= 8:  score += 1
    if len(pw) >= 12: score += 1
    if any(c.isupper() for c in pw): score += 1
    if any(c.isdigit() for c in pw): score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in pw): score += 1

    if score <= 1:   return "Weak",   DANGER,  1
    elif score <= 3: return "Fair",   WARN,    2
    elif score == 4: return "Good",   PRIMARY, 3
    else:            return "Strong", SUCCESS, 4


class StrengthMeter(tk.Frame):
    """Four-segment bar showing password strength."""

    SEGMENTS = 4

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=CARD, **kw)
        self._bars  = []
        self._label = tk.Label(self, text="", font=("Helvetica", 8),
                               bg=CARD, fg=TEXT_MUTED, width=8, anchor="w")

        bar_frame = tk.Frame(self, bg=CARD)
        bar_frame.pack(side="left", fill="x", expand=True)
        for _ in range(self.SEGMENTS):
            b = tk.Frame(bar_frame, bg=BORDER, height=5, width=0)
            b.pack(side="left", fill="x", expand=True, padx=2)
            self._bars.append(b)

        self._label.pack(side="left", padx=(6, 0))

    def update(self, password):
        if not password:
            for b in self._bars:
                b.config(bg=BORDER)
            self._label.config(text="")
            return
        label, colour, filled = evaluate_strength(password)
        for i, b in enumerate(self._bars):
            b.config(bg=colour if i < filled else BORDER)
        self._label.config(text=label, fg=colour)


# ──────────────────────────────────────────────
# Profile / Change-Password Window
# ──────────────────────────────────────────────
class ProfileWindow:
    def __init__(self, parent, username):
        self.username = username

        self.win = tk.Toplevel(parent)
        self.win.title("User Profile")
        self.win.geometry("430x560")
        self.win.configure(bg=BG)
        self.win.resizable(False, False)
        self.win.grab_set()

        # ── Header banner ────────────────────────
        header = tk.Frame(self.win, bg=PRIMARY, pady=18)
        header.pack(fill="x")

        tk.Label(header, text="👤", font=("Helvetica", 30),
                 bg=PRIMARY, fg="white").pack()
        tk.Label(header, text=username,
                 font=("Helvetica", 14, "bold"),
                 bg=PRIMARY, fg="white").pack(pady=(3, 0))
        tk.Label(header, text="Manage your account",
                 font=("Helvetica", 9), bg=PRIMARY, fg="#c5d8ff").pack()

        # ── Card (fill="x" only — no expand, so button is never pushed off) ──
        card = tk.Frame(self.win, bg=CARD, padx=32, pady=20,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(pady=14, padx=22, fill="x")

        tk.Label(card, text="Change Password",
                 font=("Helvetica", 13, "bold"),
                 bg=CARD, fg=PRIMARY).pack(pady=(0, 12))

        # Three password rows with eye toggles
        self.old_pw     = pw_entry_row(card, "Current Password")
        self.old_pw.focus_set()

        self.new_pw     = pw_entry_row(card, "New Password")
        self.confirm_pw = pw_entry_row(card, "Confirm New Password")

        # Strength meter (live, updates as user types)
        tk.Label(card, text="Password strength:", font=("Helvetica", 9),
                 bg=CARD, fg=TEXT_MUTED, anchor="w").pack(fill="x")
        self.meter = StrengthMeter(card)
        self.meter.pack(fill="x", pady=(2, 14))
        self.new_pw.bind("<KeyRelease>",
                         lambda e: self.meter.update(self.new_pw.get()))

        # Divider
        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=(0, 14))

        # Change Password button — fill="x" so it always spans the card width
        save_btn = styled_button(card, "  Change Password  ",
                                 self.change_password,
                                 bg=PRIMARY, hover_bg=PRIMARY_DARK,
                                 font=("Helvetica", 10, "bold"))
        save_btn.pack(fill="x", ipady=2)
        Tooltip(save_btn, "Save your new password")

        # Cancel link
        cancel_btn = tk.Button(card, text="Cancel", bg=CARD, fg=TEXT_MUTED,
                               relief="flat", bd=0, cursor="hand2",
                               font=("Helvetica", 9, "underline"),
                               command=self.win.destroy)
        cancel_btn.pack(pady=(8, 0))
        add_hover(cancel_btn, CARD, "#f0f4ff", TEXT_MUTED, PRIMARY)
        Tooltip(cancel_btn, "Close without saving")

        # Enter key
        self.win.bind("<Return>", lambda e: self.change_password())

    # ── Logic ────────────────────────────────────

    def change_password(self):
        old     = self.old_pw.get()
        new     = self.new_pw.get()
        confirm = self.confirm_pw.get()

        if not old or not new or not confirm:
            messagebox.showerror("Error", "All fields are required.", parent=self.win)
            return
        if new == old:
            messagebox.showwarning("Warning",
                                   "New password must be different from the current one.",
                                   parent=self.win)
            return
        if new != confirm:
            messagebox.showerror("Error", "New passwords do not match.", parent=self.win)
            return

        label, _, _ = evaluate_strength(new)
        if label == "Weak":
            if not messagebox.askyesno(
                "Weak Password",
                "Your new password is weak. Are you sure you want to use it?",
                parent=self.win
            ):
                return

        db         = DatabaseManager()
        hashed_old = hash_password(old)
        user       = db.fetch_one(
            "SELECT id FROM users WHERE username = ? AND password = ?",
            (self.username, hashed_old)
        )
        if not user:
            messagebox.showerror("Error", "Current password is incorrect.", parent=self.win)
            return

        hashed_new = hash_password(new)
        if db.execute_query(
            "UPDATE users SET password = ? WHERE username = ?",
            (hashed_new, self.username)
        ):
            messagebox.showinfo("Success", "Password changed successfully.", parent=self.win)
            self.win.destroy()
        else:
            messagebox.showerror("Error", "Failed to update password.", parent=self.win)