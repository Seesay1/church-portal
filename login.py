import tkinter as tk
from tkinter import messagebox, ttk
import os
import sys
from PIL import Image, ImageTk
from database import DatabaseManager, hash_password

try:
    from dashboard_ui import DashboardUI
except ImportError:
    from dashboard import DashboardUI


# ──────────────────────────────────────────────
# Colour palette
# ──────────────────────────────────────────────
PRIMARY      = "#1f4fa3"
PRIMARY_DARK = "#163a7a"
PRIMARY_LIGHT= "#3366cc"
DANGER       = "#d62828"
DANGER_DARK  = "#a01e1e"
BG           = "#e8f1ff"
CARD         = "#ffffff"
TEXT_DARK    = "#1a1a2e"
TEXT_MUTED   = "#666680"
BORDER       = "#c8d6f0"


# ──────────────────────────────────────────────
# Reusable hover / tooltip helpers
# ──────────────────────────────────────────────
def add_hover(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    """Add smooth colour-swap hover to any Button or Label."""
    def on_enter(e):
        widget.config(bg=hover_bg)
        if hover_fg:
            widget.config(fg=hover_fg)
        widget.config(cursor="hand2")

    def on_leave(e):
        widget.config(bg=normal_bg)
        if normal_fg:
            widget.config(fg=normal_fg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


class Tooltip:
    """Small floating tooltip that appears near the cursor."""

    def __init__(self, widget, text, delay=500):
        self.widget  = widget
        self.text    = text
        self.delay   = delay
        self._tip    = None
        self._job    = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
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

        frame = tk.Frame(tw, bg="#2b2b3b", padx=8, pady=4,
                         relief="flat", bd=0)
        frame.pack()
        tk.Label(frame, text=self.text, bg="#2b2b3b", fg="#f0f4ff",
                 font=("Helvetica", 9), justify="left",
                 wraplength=220).pack()

    def _hide(self, event=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self._tip:
            self._tip.destroy()
            self._tip = None


def styled_button(parent, text, command, bg=PRIMARY, fg="white",
                  hover_bg=PRIMARY_DARK, width=None, font=None, **kw):
    """Factory for a consistently styled button with hover + cursor."""
    opts = dict(
        text=text, command=command,
        bg=bg, fg=fg,
        activebackground=hover_bg, activeforeground=fg,
        relief="flat", bd=0,
        padx=12, pady=7,
        font=font or ("Helvetica", 10, "bold"),
        cursor="hand2",
    )
    if width:
        opts["width"] = width
    btn = tk.Button(parent, **opts, **kw)
    add_hover(btn, bg, hover_bg)
    return btn


def styled_entry(parent, width=30, show=None):
    """Entry with a visible border frame."""
    frame = tk.Frame(parent, bg=BORDER, padx=1, pady=1)
    opts  = dict(width=width, relief="flat", bd=4,
                 font=("Helvetica", 11), bg="#f5f8ff")
    if show:
        opts["show"] = show
    entry = tk.Entry(frame, **opts)
    entry.pack(fill="x")

    def on_focus_in(e):
        frame.config(bg=PRIMARY_LIGHT)
    def on_focus_out(e):
        frame.config(bg=BORDER)

    entry.bind("<FocusIn>",  on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)
    return frame, entry


# ──────────────────────────────────────────────
# Main Login UI
# ──────────────────────────────────────────────
class LoginUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PCG Mt. Zion - Login")
        self.root.geometry("480x620")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        # ── Logo ────────────────────────────────
        self.logo = None
        possible_names = ["logo.png", "logo.jpg", "logo.jpeg", "logo.gif"]
        search_paths = [
            os.path.dirname(__file__),
            os.path.join(os.path.dirname(__file__), "images"),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        ]
        found_path = None
        for folder in search_paths:
            for name in possible_names:
                full = os.path.join(folder, name)
                if os.path.isfile(full):
                    found_path = full
                    break
            if found_path:
                break

        if found_path:
            try:
                img = Image.open(found_path)
                img.thumbnail((120, 120), Image.Resampling.LANCZOS)
                self.logo = ImageTk.PhotoImage(img)
                tk.Label(root, image=self.logo, bg=BG).pack(pady=(24, 8))
            except Exception as e:
                print(f"Error loading logo: {e}")
                tk.Label(root, text="🏛️", font=("Helvetica", 56), bg=BG).pack(pady=(20, 6))
        else:
            tk.Label(root, text="🏛️", font=("Helvetica", 56), bg=BG).pack(pady=(20, 6))

        # ── Card ────────────────────────────────
        card = tk.Frame(root, bg=CARD, padx=36, pady=28,
                        relief="flat", bd=0,
                        highlightbackground=BORDER, highlightthickness=1)
        card.pack(pady=6, padx=28, fill="both", expand=True)

        tk.Label(card, text="PCG Mt. Zion System",
                 font=("Helvetica", 17, "bold"),
                 bg=CARD, fg=PRIMARY).pack(pady=(0, 4))
        tk.Label(card, text="Sign in to your account",
                 font=("Helvetica", 10), bg=CARD, fg=TEXT_MUTED).pack(pady=(0, 16))

        # Username
        tk.Label(card, text="Username", font=("Helvetica", 10, "bold"),
                 bg=CARD, fg=TEXT_DARK, anchor="w").pack(fill="x")
        u_frame, self.username = styled_entry(card, width=34)
        u_frame.pack(fill="x", pady=(3, 12))
        self.username.focus_set()

        # Password
        tk.Label(card, text="Password", font=("Helvetica", 10, "bold"),
                 bg=CARD, fg=TEXT_DARK, anchor="w").pack(fill="x")

        pw_outer = tk.Frame(card, bg=BORDER, padx=1, pady=1)
        pw_outer.pack(fill="x", pady=(3, 4))
        pw_inner = tk.Frame(pw_outer, bg="#f5f8ff")
        pw_inner.pack(fill="x")

        self.password = tk.Entry(pw_inner, show="*", relief="flat", bd=4,
                                 font=("Helvetica", 11), bg="#f5f8ff", width=27)
        self.password.pack(side="left", fill="x", expand=True)

        self.show_btn = tk.Button(pw_inner, text="👁", relief="flat", bd=0,
                                  bg="#f5f8ff", cursor="hand2",
                                  font=("Helvetica", 12),
                                  command=self.toggle_password)
        self.show_btn.pack(side="right", padx=(0, 4))
        add_hover(self.show_btn, "#f5f8ff", "#dce8ff")
        Tooltip(self.show_btn, "Show / hide password")

        def pw_focus_in(e):
            pw_outer.config(bg=PRIMARY_LIGHT)
        def pw_focus_out(e):
            pw_outer.config(bg=BORDER)
        self.password.bind("<FocusIn>",  pw_focus_in)
        self.password.bind("<FocusOut>", pw_focus_out)

        # ── Login button ─────────────────────────
        login_btn = styled_button(card, "Login", self.login,
                                  bg=PRIMARY, hover_bg=PRIMARY_DARK,
                                  width=28, font=("Helvetica", 11, "bold"))
        login_btn.pack(pady=(18, 6))
        Tooltip(login_btn, "Sign in with your credentials")

        # ── Divider ───────────────────────────────
        sep = tk.Frame(card, bg=BORDER, height=1)
        sep.pack(fill="x", pady=10)

        # ── Secondary buttons ─────────────────────
        btn_row = tk.Frame(card, bg=CARD)
        btn_row.pack()

        forgot_btn = tk.Button(btn_row, text="Forgot Password",
                               bg=CARD, fg=DANGER, relief="flat", bd=0,
                               font=("Helvetica", 9, "underline"),
                               cursor="hand2", command=self.forgot_password)
        forgot_btn.pack(side="left", padx=6)
        add_hover(forgot_btn, CARD, "#fff0f0", DANGER, DANGER_DARK)
        Tooltip(forgot_btn, "Reset your password using your security question")

        create_btn = tk.Button(btn_row, text="Create New User",
                               bg=CARD, fg=PRIMARY, relief="flat", bd=0,
                               font=("Helvetica", 9, "underline"),
                               cursor="hand2", command=self.create_user)
        create_btn.pack(side="left", padx=6)
        add_hover(create_btn, CARD, "#f0f4ff", PRIMARY, PRIMARY_DARK)
        Tooltip(create_btn, "Register a new system user account")

        # ── Member Portal button ──────────────────
        portal_row = tk.Frame(card, bg=CARD)
        portal_row.pack(pady=(10, 0))

        self.portal_btn = styled_button(portal_row, "Member Portal",
                                        self.open_member_portal,
                                        bg=PRIMARY, hover_bg=PRIMARY_DARK,
                                        font=("Helvetica", 10, "bold"))
        self.portal_btn.pack()
        Tooltip(self.portal_btn, "Open the self-service member portal")

        # Enter key
        self.root.bind("<Return>", lambda e: self.login())

    # ── Helpers ──────────────────────────────────

    def toggle_password(self):
        self.password.config(
            show="" if self.password.cget("show") == "*" else "*"
        )

    def login(self):
        username = self.username.get().strip()
        password = self.password.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return

        db   = DatabaseManager()
        user = db.fetch_one(
            "SELECT id, username, password, role, branch_id FROM users WHERE username = ?",
            (username,)
        )
        if user and hash_password(password) == user[2]:
            messagebox.showinfo("Success", "Login Successful")
            self.root.destroy()
            dashboard_root = tk.Tk()
            DashboardUI(
                dashboard_root,
                username=username,
                role=user[3],
                user_id=user[0],
                branch_id=user[4]
            )
            dashboard_root.mainloop()
        else:
            messagebox.showerror("Error", "Invalid Username or Password")

    # ── Forgot Password window ────────────────────

    def forgot_password(self):
        win = tk.Toplevel(self.root)
        win.title("Reset Password")
        win.geometry("420x340")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Forgot Password",
                 font=("Helvetica", 14, "bold"), bg=BG, fg=PRIMARY).pack(pady=(20, 4))
        tk.Label(win, text="Enter your username to continue",
                 font=("Helvetica", 9), bg=BG, fg=TEXT_MUTED).pack()

        frm = tk.Frame(win, bg=BG, padx=30, pady=10)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="Username:", bg=BG, fg=TEXT_DARK,
                 font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        uf, username_entry = styled_entry(frm, width=32)
        uf.pack(fill="x", pady=(3, 12))
        username_entry.focus_set()

        def check_username():
            uname = username_entry.get().strip()
            if not uname:
                messagebox.showerror("Error", "Please enter your username", parent=win)
                return
            db   = DatabaseManager()
            user = db.fetch_one(
                "SELECT security_question, security_answer FROM users WHERE username = ?",
                (uname,)
            )
            if not user:
                messagebox.showerror("Error", "Username not found", parent=win)
                return
            question, answer_hash = user
            if not question or not answer_hash:
                messagebox.showerror("Error", "No security question set. Contact admin.", parent=win)
                return

            for w in win.winfo_children():
                w.destroy()

            win.geometry("420x400")
            inner = tk.Frame(win, bg=BG, padx=30, pady=16)
            inner.pack(fill="both", expand=True)

            tk.Label(inner, text="Security Question:",
                     font=("Helvetica", 10, "bold"), bg=BG, fg=TEXT_DARK).pack(anchor="w")
            tk.Label(inner, text=question, bg=BG, fg=PRIMARY,
                     wraplength=360, justify="left",
                     font=("Helvetica", 10, "italic")).pack(anchor="w", pady=(2, 10))

            tk.Label(inner, text="Your Answer:", bg=BG, fg=TEXT_DARK,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
            af, answer_entry = styled_entry(inner, width=32)
            af.pack(fill="x", pady=(3, 10))

            tk.Label(inner, text="New Password:", bg=BG, fg=TEXT_DARK,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
            nf, new_pw = styled_entry(inner, width=32, show="*")
            nf.pack(fill="x", pady=(3, 10))

            tk.Label(inner, text="Confirm Password:", bg=BG, fg=TEXT_DARK,
                     font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
            cf, confirm_pw = styled_entry(inner, width=32, show="*")
            cf.pack(fill="x", pady=(3, 14))
            answer_entry.focus_set()

            def reset():
                ans     = answer_entry.get().strip().lower()
                new     = new_pw.get()
                confirm = confirm_pw.get()
                if not ans:
                    messagebox.showerror("Error", "Please answer the security question", parent=win)
                    return
                if hash_password(ans) != answer_hash:
                    messagebox.showerror("Error", "Incorrect answer", parent=win)
                    return
                if not new:
                    messagebox.showerror("Error", "Enter a new password", parent=win)
                    return
                if new != confirm:
                    messagebox.showerror("Error", "Passwords do not match", parent=win)
                    return
                db.execute_query("UPDATE users SET password = ? WHERE username = ?",
                                 (hash_password(new), uname))
                messagebox.showinfo("Success", "Password reset. You can now log in.", parent=win)
                win.destroy()

            reset_btn = styled_button(inner, "Reset Password", reset,
                                      bg=DANGER, hover_bg=DANGER_DARK,
                                      font=("Helvetica", 10, "bold"))
            reset_btn.pack()
            Tooltip(reset_btn, "Save your new password")
            win.bind("<Return>", lambda e: reset())

        next_btn = styled_button(frm, "Next →", check_username,
                                 font=("Helvetica", 10, "bold"))
        next_btn.pack()
        Tooltip(next_btn, "Verify your username")
        win.bind("<Return>", lambda e: check_username())

    # ── Create User window ────────────────────────

    def create_user(self):
        win = tk.Toplevel(self.root)
        win.title("Create New User")
        win.geometry("440x520")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Create New User",
                 font=("Helvetica", 14, "bold"), bg=BG, fg=PRIMARY).pack(pady=(20, 2))
        tk.Label(win, text="Fill in all fields to register an account",
                 font=("Helvetica", 9), bg=BG, fg=TEXT_MUTED).pack()

        frm = tk.Frame(win, bg=BG, padx=30, pady=12)
        frm.pack(fill="both", expand=True)

        tk.Label(frm, text="Username:", bg=BG, fg=TEXT_DARK,
                 font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        uf, u_entry = styled_entry(frm, width=32)
        uf.pack(fill="x", pady=(3, 10))

        tk.Label(frm, text="Password:", bg=BG, fg=TEXT_DARK,
                 font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        pf, p_entry = styled_entry(frm, width=32, show="*")
        pf.pack(fill="x", pady=(3, 10))

        tk.Label(frm, text="Role:", bg=BG, fg=TEXT_DARK,
                 font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        role_combo = ttk.Combobox(frm, values=["Admin", "User"],
                                  state="readonly", width=31)
        role_combo.pack(pady=(3, 10), anchor="w")
        role_combo.set("User")

        tk.Label(frm, text="Security Question:", bg=BG, fg=TEXT_DARK,
                 font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        q_combo = ttk.Combobox(frm, values=[
            "What is your mother's maiden name?",
            "What was your first pet's name?",
            "What is your favorite book?",
            "What city were you born in?",
            "What is your favorite food?"
        ], width=42, state="readonly")
        q_combo.pack(pady=(3, 10), anchor="w")

        tk.Label(frm, text="Answer:", bg=BG, fg=TEXT_DARK,
                 font=("Helvetica", 10, "bold"), anchor="w").pack(fill="x")
        af, answer_entry = styled_entry(frm, width=32)
        af.pack(fill="x", pady=(3, 14))
        u_entry.focus_set()

        def save():
            u_name   = u_entry.get().strip()
            p_word   = p_entry.get().strip()
            u_role   = role_combo.get().strip()
            question = q_combo.get().strip()
            answer   = answer_entry.get().strip().lower()

            if not all([u_name, p_word, u_role, question, answer]):
                messagebox.showerror("Error", "All fields are required", parent=win)
                return

            db = DatabaseManager()
            try:
                success = db.execute_query(
                    "INSERT INTO users (username, password, role, security_question, security_answer) "
                    "VALUES (?,?,?,?,?)",
                    (u_name, hash_password(p_word), u_role, question, hash_password(answer))
                )
                if success:
                    messagebox.showinfo("Success", "User created successfully", parent=win)
                    win.destroy()
                else:
                    messagebox.showerror("Error", "Username already exists", parent=win)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        save_btn = styled_button(frm, "Save User", save,
                                 font=("Helvetica", 10, "bold"), width=20)
        save_btn.pack()
        Tooltip(save_btn, "Save and create the new user account")
        win.bind("<Return>", lambda e: save())

    # ── Member Portal ─────────────────────────────

    def open_member_portal(self):
        from modules.member_portal import MemberPortalLogin
        MemberPortalLogin(self.root)


if __name__ == "__main__":
    root = tk.Tk()
    LoginUI(root)
    root.mainloop()