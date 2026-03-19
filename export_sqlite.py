# export_sqlite.py
import sqlite3
import csv
import os

sqlite_db = 'church_system.db'   # adjust if your file name differs
output_dir = 'sqlite_export'

os.makedirs(output_dir, exist_ok=True)

conn = sqlite3.connect(sqlite_db)
cursor = conn.cursor()

# Get all table names (excluding sqlite internal tables)
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    cursor.execute(f"SELECT * FROM {table}")
    rows = cursor.fetchall()
    if not rows:
        continue
    # Get column names
    col_names = [description[0] for description in cursor.description]
    csv_path = os.path.join(output_dir, f"{table}.csv")
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(col_names)
        writer.writerows(rows)
    print(f"Exported {table} ({len(rows)} rows) to {csv_path}")

conn.close()