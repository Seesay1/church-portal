# database.py - PostgreSQL version for desktop app and web portal
import hashlib
import logging
import os
import re
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import psycopg2

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False
from werkzeug.security import check_password_hash, generate_password_hash

logger = logging.getLogger(__name__)

_LEGACY_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


def _build_database_url():
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "postgres")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    name = os.getenv("DB_NAME", "church_db")

    auth = quote_plus(user)
    if password:
        auth = f"{auth}:{quote_plus(password)}"
    return f"postgresql://{auth}@{host}:{port}/{name}"


DEFAULT_DB_URL = _build_database_url()
BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"
CORE_SCHEMA_FILE = MIGRATIONS_DIR / "core_schema.sql"
FEATURE_SCHEMA_FILES = (
    MIGRATIONS_DIR / "assets_service_tables.sql",
)
REQUIRED_TABLES = (
    "attendance",
    "audit_log",
    "blog_posts",
    "branches",
    "certificate_requests",
    "certificates",
    "committee_activities",
    "committee_expenses",
    "committee_meetings",
    "committee_members",
    "committee_roles",
    "committees",
    "departments",
    "event_registrations",
    "events",
    "families",
    "family_link_requests",
    "family_links",
    "family_members",
    "financial_records",
    "groups",
    "id_cards",
    "member_portal",
    "members",
    "notification_history",
    "prayer_requests",
    "resources",
    "saved_reports",
    "settings",
    "sms_logs",
    "user_widgets",
    "users",
    "volunteer_opportunities",
    "volunteer_signups",
    "asset_categories",
    "assets",
    "asset_maintenance",
    "asset_assignments",
    "service_types",
    "service_schedule",
    "service_items",
    "service_songs",
    "sermons",
    "service_teams",
)


def _legacy_sha256(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def is_legacy_hash(stored_hash):
    return bool(stored_hash and _LEGACY_SHA256_RE.fullmatch(stored_hash))


def hash_password(password):
    """Return a modern password hash for new or updated credentials."""
    return generate_password_hash(password, method="scrypt")


def verify_password(password, stored_hash):
    """Verify a password against either a legacy SHA-256 or modern Werkzeug hash."""
    if not stored_hash:
        return False
    if is_legacy_hash(stored_hash):
        return _legacy_sha256(password) == stored_hash
    try:
        return check_password_hash(stored_hash, password)
    except (ValueError, TypeError):
        return False


def password_needs_upgrade(stored_hash):
    return is_legacy_hash(stored_hash)


def create_connection():
    """Create and return a database connection (for compatibility)."""
    return psycopg2.connect(DEFAULT_DB_URL)


def get_postgres_connection_info(db_url=None):
    """Return parsed PostgreSQL connection details for tooling such as pg_dump/psql."""
    parsed = urlparse(db_url or DEFAULT_DB_URL)
    return {
        "dbname": parsed.path.lstrip("/"),
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": parsed.username or "",
        "password": parsed.password or "",
    }


class DatabaseManager:
    def __init__(self, db_url=None):
        self.db_url = db_url or DEFAULT_DB_URL
        self.conn = None

    def connect(self):
        """Establish a connection if not already open."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(self.db_url)
        return self.conn

    def _convert_query(self, query):
        """Replace SQLite ? placeholders with PostgreSQL %s placeholders."""
        return query.replace("?", "%s")

    def execute_query(self, query, params=None):
        """Execute an INSERT, UPDATE, or DELETE query."""
        conn = self.connect()
        query = self._convert_query(query)
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                conn.commit()
                return True
        except Exception:
            conn.rollback()
            raise

    def fetch_all(self, query, params=None):
        """Fetch all rows from a SELECT query."""
        conn = self.connect()
        query = self._convert_query(query)
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                return cur.fetchall()
        except Exception:
            conn.rollback()
            raise

    def fetch_one(self, query, params=None):
        """Fetch a single row from a SELECT query."""
        conn = self.connect()
        query = self._convert_query(query)
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                return cur.fetchone()
        except Exception:
            conn.rollback()
            raise

    def execute_returning_one(self, query, params=None):
        """Execute a write query with RETURNING and commit before returning one row."""
        conn = self.connect()
        query = self._convert_query(query)
        try:
            with conn.cursor() as cur:
                cur.execute(query, params or ())
                row = cur.fetchone()
                conn.commit()
                return row
        except Exception:
            conn.rollback()
            raise

    def close(self):
        """Close the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()


def execute_sql_file(file_path, db=None):
    """Execute an entire SQL file inside a single transaction."""
    sql_path = Path(file_path)
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    manager = db or DatabaseManager()
    conn = manager.connect()
    sql = sql_path.read_text(encoding="utf-8")

    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def get_missing_tables(required_tables=None, db=None):
    """Return a sorted list of required tables that are missing from the public schema."""
    manager = db or DatabaseManager()
    rows = manager.fetch_all(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        """
    )
    existing = {row[0] for row in rows}
    required = set(required_tables or REQUIRED_TABLES)
    return sorted(required - existing)


def setup_database():
    """
    Initialize PostgreSQL schema for both desktop and web app entry points.
    """
    db = DatabaseManager()
    try:
        if CORE_SCHEMA_FILE.exists():
            execute_sql_file(CORE_SCHEMA_FILE, db=db)

        for schema_file in FEATURE_SCHEMA_FILES:
            if schema_file.exists():
                execute_sql_file(schema_file, db=db)

        missing_tables = get_missing_tables(db=db)
        if missing_tables:
            missing_preview = ", ".join(missing_tables[:10])
            if len(missing_tables) > 10:
                missing_preview += ", ..."
            raise RuntimeError(
                "Database schema is incomplete. Missing tables: "
                f"{missing_preview}. Run the project migrations before starting the app."
            )

        logger.info("Database schema verified successfully")
    finally:
        db.close()


if __name__ == "__main__":
    db = DatabaseManager()
    try:
        result = db.fetch_one("SELECT COUNT(*) FROM volunteer_signups")
        logger.info("Connected! Total signups: %s", result[0])
    except Exception:
        logger.exception("Connection failed")
