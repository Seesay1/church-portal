import csv
import os
import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://church_user:2311@localhost:5432/church_db"
input_dir = 'sqlite_export'

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# We'll import without disabling triggers – it may be slower but works.

for filename in os.listdir(input_dir):
    if not filename.endswith('.csv'):
        continue
    table_name = filename[:-4]
    filepath = os.path.join(input_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        columns = next(reader)  # header
        # Prepare INSERT statement
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
                # You can choose to continue or break
        print(f"Imported {row_count} rows into {table_name}")

conn.commit()
conn.close()
print("Import completed.")