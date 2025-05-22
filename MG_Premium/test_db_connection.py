import os
from dotenv import load_dotenv
import pyodbc

# Load environment variables from .env
env_file = ".env.dev" if os.path.exists(".env.dev") else ".env"
load_dotenv(env_file)
print(f"Loaded environment variables from {env_file}")

# Gather DB connection info from env
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DRIVER = os.getenv("ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

# Build connection string
conn_str = (
    f"DRIVER={{{DRIVER}}};"
    f"SERVER={DB_HOST},{DB_PORT};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASS};"
)

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    print("✅ Connection successful! Test query result:", result[0])
    cursor.close()
    conn.close()
except Exception as e:
    print("❌ Failed to connect to the database.")
    print("Error:", e)
