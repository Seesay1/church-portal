# config.py
import os

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def _get_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# ---------- Church Info ----------
CHURCH_NAME = os.getenv("CHURCH_NAME", "PCG Mt. Zion Congregation - Sampa")
CHURCH_LOGO = os.getenv("CHURCH_LOGO", "assets/logo.png")
LOGO_PATH = CHURCH_LOGO

# ---------- Color Theme ----------
SIDEBAR_BG = "#162f65"
SIDEBAR_FG = "#ffffff"
SIDEBAR_ACTIVE_BG = "#d62828"
MAIN_BG = "#e8f1ff"
CARD_BG = "#ffffff"
CARD_TITLE_COLOR = "#1f4fa3"
BUTTON_BG = "#d62828"
BUTTON_FG = "#ffffff"

# ---------- Default Admin Login ----------
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "")

# ---------- Branch Codes for Member IDs ----------
BRANCH_CODES = {
    "Mt. Zion": "PCG-MZ",
}

# ---------- SMS Settings ----------
SMS_API_ENABLED = _get_bool("SMS_API_ENABLED", False)
SMS_API_KEY = os.getenv("SMS_API_KEY", "")
SMS_API_URL = os.getenv("SMS_API_URL", "")
GSM_MODEM_ENABLED = _get_bool("GSM_MODEM_ENABLED", True)

# ---------- Other Settings ----------
EXPORTS_PATH = os.getenv("EXPORTS_PATH", "exports")
PHOTOS_PATH = os.getenv("PHOTOS_PATH", "photos")

# ---------- Fonts ----------
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SUBTITLE = ("Segoe UI", 14)
FONT_TEXT = ("Segoe UI", 12)

# ---------- Flask / Session Settings ----------
SECRET_KEY = os.getenv("SECRET_KEY", "")
SESSION_COOKIE_SECURE = _get_bool("SESSION_COOKIE_SECURE", True)
SESSION_COOKIE_HTTPONLY = _get_bool("SESSION_COOKIE_HTTPONLY", True)
SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_LIFETIME_MINUTES = _get_int("SESSION_LIFETIME_MINUTES", 120)

# ---------- Email Settings (SMTP) ----------
CONTACT_FORM_ENABLED = _get_bool("CONTACT_FORM_ENABLED", False)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = _get_int("SMTP_PORT", 587)
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = _get_bool("SMTP_USE_TLS", True)
CONTACT_FORM_RECIPIENT = os.getenv("CONTACT_FORM_RECIPIENT", "")
CONTACT_FORM_SUBJECT = os.getenv("CONTACT_FORM_SUBJECT", "New Contact Form Submission - PCG Mt. Zion")
