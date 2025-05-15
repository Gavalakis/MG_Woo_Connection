# db.py
import os
import yaml
import pathlib
import mysql.connector
from dotenv import load_dotenv

# ───────────────────────────────────────────────────────────────
# 1) Load environment variables and YAML config
# ───────────────────────────────────────────────────────────────
load_dotenv()   # reads .env or .env.dev per main.py

_cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text())
TABLE        = _cfg["db"]["table"]
ID_COL       = _cfg["db"]["id_col"]
UPLOADED_COL = _cfg["db"]["uploaded_col"]

class DB:
    def __init__(self):
        # 2) Connect to MySQL
        self.conn = mysql.connector.connect(
            host     = os.getenv("DB_HOST"),
            port     = int(os.getenv("DB_PORT", 3306)),
            user     = os.getenv("DB_USER"),
            password = os.getenv("DB_PASS"),
            database = os.getenv("DB_NAME")
        )
    def fetch_new_rows(self):
        """
        Return all rows where UPLOADED_COL = 0
        as a list of dicts (column name → value).
        """
        cur = self.conn.cursor(dictionary=True)
        sql = f"SELECT * FROM `{TABLE}` WHERE `{UPLOADED_COL}` = 0"
        print(f"[DB] Executing: {sql}")                # debug
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        return rows

    def mark_uploaded(self, row_id, external_id=None):
        """
        Set UPLOADED_COL = 1 for the given row_id.
        If external_id is provided, also store it in an 'external_id' column (if you have one).
        """
        cur = self.conn.cursor()
        if external_id is not None:
            sql = (
                f"UPDATE `{TABLE}` "
                f"SET `{UPLOADED_COL}`=1, `external_id`=%s "
                f"WHERE `{ID_COL}`=%s"
            )
            params = (external_id, row_id)
        else:
            sql = (
                f"UPDATE `{TABLE}` "
                f"SET `{UPLOADED_COL}`=1 "
                f"WHERE `{ID_COL}`=%s"
            )
            params = (row_id,)

        print(f"[DB] Executing: {sql} with {params}")  # debug
        cur.execute(sql, params)
        self.conn.commit()
        cur.close()