# db.py
import os, yaml, pathlib, sys
import mysql.connector
from dotenv import load_dotenv

load_dotenv()
_cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text())

# Main table config
MAIN_TABLE    = _cfg["db"]["table"]
MAIN_ID_COL   = _cfg["db"]["id_col"]

# Sync table config
SYNC_TABLE            = _cfg["db"]["sync_table"]
SYNC_REF_COL          = _cfg["db"]["sync_product_ref_col"]
SYNC_UPLOADED_COL     = _cfg["db"]["sync_uploaded_col"]
SYNC_EXTERNAL_COL     = _cfg["db"]["sync_external_id_col"]
SYNC_UPLOADED_DATE    = _cfg["db"]["sync_uploaded_date_col"]
SYNC_UPDATED_DATE     = _cfg["db"]["sync_updated_date_col"]

class DB:
    def __init__(self):
        try:
            self.conn = mysql.connector.connect(
                host     = os.getenv("DB_HOST"),
                port     = int(os.getenv("DB_PORT", 3306)),
                user     = os.getenv("DB_USER"),
                password = os.getenv("DB_PASS"),
                database = os.getenv("DB_NAME")
            )
        except mysql.connector.Error as err:
            print(f"[DB ERROR] Could not connect to the database.")
            print(f"  Host: {os.getenv('DB_HOST')}")
            print(f"  Port: {os.getenv('DB_PORT')}")
            print(f"  User: {os.getenv('DB_USER')}")
            print(f"  Database: {os.getenv('DB_NAME')}")
            print(f"  Error details: {err}")
            sys.exit(1)  # or raise, depending on desired behavior

        except Exception as ex:
            print(f"[DB ERROR] Unexpected error during DB connection: {ex}")
            sys.exit(1)  # or raise

    def fetch_new_rows(self):
        """
        Return all rows from the main table where the sync table says uploaded=0.
        """
        try:
            cur = self.conn.cursor(dictionary=True)
            sql = (
                f"SELECT m.* "
                f"FROM `{MAIN_TABLE}` AS m "
                f"JOIN `{SYNC_TABLE}` AS s "
                f"  ON m.`{MAIN_ID_COL}` = s.`{SYNC_REF_COL}` "
                f"WHERE s.`{SYNC_UPLOADED_COL}` = 0"
            )
            print(f"[DB] Executing: {sql}")
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as ex:
            print(f"[DB ERROR] Failed to fetch new rows: {ex}")
            return []

    def mark_uploaded(self, product_ref_id, external_id=None):
        """
        Mark the sync row as uploaded, store external_id, and set timestamps.
        """
        try:
            cur = self.conn.cursor()
            # base update
            sql = (
                f"UPDATE `{SYNC_TABLE}` SET "
                f"`{SYNC_UPLOADED_COL}` = 1, "
                f"`{SYNC_UPDATED_DATE}` = NOW()"
            )
            params = []

            if external_id is not None:
                # set external_id and uploaded_date on first upload
                sql += (
                    f", `{SYNC_EXTERNAL_COL}` = %s, "
                    f"`{SYNC_UPLOADED_DATE}` = COALESCE(`{SYNC_UPLOADED_DATE}`, NOW())"
                )
                params.append(external_id)

            sql += f" WHERE `{SYNC_REF_COL}` = %s"
            params.append(product_ref_id)

            print(f"[DB] Executing: {sql} with {params}")
            cur.execute(sql, params)
            self.conn.commit()
            cur.close()
        except Exception as ex:
            print(f"[DB ERROR] Failed to mark product as uploaded (product_ref_id={product_ref_id}): {ex}")

    #-----------------------   Updater Script Part   ---------------------------

    def fetch_products_for_update(self):
        """
        Fetch products already uploaded to Woo (uploaded=1), including Woo external ID,
        all warehouse stock columns, and RP price.
        """
        try:
            stock_columns = _cfg.get("stock_columns", [])
            stock_select_sql = ", ".join([f"m.`{col}`" for col in stock_columns])
            cur = self.conn.cursor(dictionary=True)
            sql = (
                f"SELECT "
                f"m.`{MAIN_ID_COL}` as id, "
                f"s.`{SYNC_EXTERNAL_COL}` as woo_id, "
                f"m.`RP` as price"
            )
            if stock_select_sql:
                sql += ", " + stock_select_sql + " "
            sql += (
                f"FROM `{MAIN_TABLE}` m "
                f"JOIN `{SYNC_TABLE}` s ON m.`{MAIN_ID_COL}` = s.`{SYNC_REF_COL}` "
                f"WHERE s.`{SYNC_UPLOADED_COL}` = 1 AND s.`{SYNC_EXTERNAL_COL}` IS NOT NULL"
            )
            print(f"[DB] Executing: {sql}")
            cur.execute(sql)
            rows = cur.fetchall()
            cur.close()
            return rows
        except Exception as ex:
            print(f"[DB ERROR] Failed to fetch products for update: {ex}")
            return []

