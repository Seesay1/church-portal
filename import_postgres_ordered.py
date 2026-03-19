import csv
import os
import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://church_user:2311@localhost:5432/church_db"
input_dir = 'sqlite_export'

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Define tables in correct order (dependencies first)
tables_order = [
    'branches',
    'groups',
    'departments',
    'members',
    'users',
    'events',
    'attendance',
    'financial_records',
    'event_registrations',
    'sms_logs',
    'settings',
    'audit_log',
    'member_portal',
    'user_widgets',
    'certificates',
    'id_cards',
    'certificate_requests',
    'prayer_requests',
    'family_links',
    'family_link_requests',
    'committees',
    'committee_members',
    'committee_meetings',
    'committee_activities',
    'committee_expenses',
    'committee_roles',
    'notification_history',
    'resources',
    'blog_posts',
    'volunteer_opportunities',
    'volunteer_signups',
    # Add any other tables that might exist
]

for table_name in tables_order:
    filepath = os.path.join(input_dir, f"{table_name}.csv")
    if not os.path.exists(filepath):
        print(f"CSV for {table_name} not found, skipping.")
        continue

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        columns = next(reader)  # header
        placeholders = ','.join(['%s'] * len(columns))
        insert_sql = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table_name),
            sql.SQL(',').join(map(sql.Identifier, columns)),
            sql.SQL(placeholders)
        )
        row_count = 0
        for row in reader:
            # Convert empty strings to None (NULL)
            row = [None if val == '' else val for val in row]
            try:
                cursor.execute(insert_sql, row)
                row_count += 1
            except Exception as e:
                print(f"Error inserting into {table_name}: {e}")
                print("Row:", row)
                conn.rollback()   # abort this table's transaction
                break
        else:
            conn.commit()
            print(f"Imported {row_count} rows into {table_name}")
            continue
        # If we broke out due to error, we already rolled back, continue with next table
        print(f"Skipping remaining rows in {table_name} due to error.")

conn.close()
print("Import completed.")