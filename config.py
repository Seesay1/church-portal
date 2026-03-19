# config.py

# ---------- Church Info ----------
CHURCH_NAME = "PCG Mt. Zion Congregation – Sampa"
CHURCH_LOGO = "assets/logo.png"  # Path to church logo image

# FIX: Map LOGO_PATH so the modules can find the logo
LOGO_PATH = CHURCH_LOGO

# ---------- Color Theme ----------
SIDEBAR_BG = "#162f65"        # Dark Blue
SIDEBAR_FG = "#ffffff"        # White text
SIDEBAR_ACTIVE_BG = "#d62828" # Red highlight
MAIN_BG = "#e8f1ff"           # Light Blue background
CARD_BG = "#ffffff"           # White cards
CARD_TITLE_COLOR = "#1f4fa3"  # Blue titles
BUTTON_BG = "#d62828"         # Red buttons
BUTTON_FG = "#ffffff"         # White button text

# ---------- Default Admin Login ----------
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"  # You can later hash this for security

# ---------- Branch Codes for Member IDs ----------
# Format: "PCG-MZ" → used for automatic member IDs
BRANCH_CODES = {
    "Mt. Zion": "PCG-MZ",
    # Add other branches here
    # "Grace": "PCG-GC",
    # "Ebenezer": "PCG-EB",
}

# ---------- SMS Settings ----------
SMS_API_ENABLED = False         # Set True when integrating online SMS API
SMS_API_KEY = ""                # API Key for online SMS (e.g., Twilio/Hubtel)
SMS_API_URL = ""                # API endpoint
GSM_MODEM_ENABLED = True        # Allow GSM modem if available

# ---------- Other Settings ----------
EXPORTS_PATH = "exports"       # Path for certificates, ID cards, reports
PHOTOS_PATH = "photos"         # Path for member photos

# ---------- Fonts ----------
FONT_TITLE = ("Segoe UI", 20, "bold")
FONT_SUBTITLE = ("Segoe UI", 14)
FONT_TEXT = ("Segoe UI", 12)