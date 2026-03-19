import psycopg2
try:
    conn = psycopg2.connect("postgresql://church_user:2311@localhost:5432/church_db")
    print("SUCCESS: Connection established.")
    conn.close()
except Exception as e:
    print("ERROR:", e)