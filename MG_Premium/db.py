# db.py
import os, yaml, pathlib, sys
#choose which connector to use
import pyod #for SQL SERVER
#import mysql.connector

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
SYNC_PARENT_COL      = _cfg["db"]["sync_parent_id_col"]
SYNC_UPLOADED_DATE    = _cfg["db"]["sync_uploaded_date_col"]
SYNC_UPDATED_DATE     = _cfg["db"]["sync_updated_date_col"]

STYLE_COL = _cfg.get("updater", {}).get("style_col", "J_Style")
SIZE_COL  = _cfg.get("updater", {}).get("size_col",  "b_Size")
STOCK_COLS = _cfg.get("stock_columns", [])

class DB:
    def __init__(self):
        try:
            conn_str = (
                f"DRIVER={{{os.getenv('ODBC_DRIVER', 'ODBC Driver 18 for SQL Server')}}};"
                f"SERVER={os.getenv('DB_HOST')},{os.getenv('DB_PORT', '1433')};"
                f"DATABASE={os.getenv('DB_NAME')};"
                f"UID={os.getenv('DB_USER')};"
                f"PWD={os.getenv('DB_PASS')};"
                f"TrustServerCertificate=yes;"
            )
            self.conn = pyodbc.connect(conn_str)
        except pyodbc.Error as err:
            print(f"[DB ERROR] Could not connect to the database.")
            print(f"  Host: {os.getenv('DB_HOST')}")
            print(f"  Port: {os.getenv('DB_PORT')}")
            print(f"  User: {os.getenv('DB_USER')}")
            print(f"  Database: {os.getenv('DB_NAME')}")
            print(f"  Error details: {err}")
            sys.exit(1)
        except Exception as ex:
            print(f"[DB ERROR] Unexpected error during DB connection: {ex}")
            sys.exit(1)

    def fetch_new_rows(self):
        """
        Return all rows from the main table where the sync table says uploaded=0.
        """
        try:
            cur = self.conn.cursor()
            sql = (
                f"SELECT m.* "
                f"FROM [{MAIN_TABLE}] AS m "
                f"JOIN [{SYNC_TABLE}] AS s "
                f"  ON m.[{MAIN_ID_COL}] = s.[{SYNC_REF_COL}] "
                f"WHERE s.[{SYNC_UPLOADED_COL}] = 0"
            )
            print(f"[DB] Executing: {sql}")
            cur.execute(sql)
            columns = [desc[0] for desc in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            cur.close()
            return rows
        except Exception as ex:
            print(f"[DB ERROR] Failed to fetch new rows: {ex}")
            return []

    def mark_uploaded(self, product_ref_id, parent_id=None, external_id=None):
        """
        Mark the sync row as uploaded, store variation id, parent id and set timestamps.
        """
        try:
            cur = self.conn.cursor()
            # base update
            sql = (
                f"UPDATE [{SYNC_TABLE}] SET "
                f"[{SYNC_UPLOADED_COL}] = 1, "
                f"[{SYNC_UPDATED_DATE}] = GETDATE()"
            )
            params = []

            if parent_id is not None:
                # set external_parent_id
                sql += f", [{SYNC_PARENT_COL}] = ?"
                params.append(parent_id)

            if external_id is not None:
                # set external_id and uploaded_date on first upload
                sql += (
                    f", [{SYNC_EXTERNAL_COL}] = ?, "
                    f"[{SYNC_UPLOADED_DATE}] = COALESCE([{SYNC_UPLOADED_DATE}], GETDATE())"
                )
                params.append(external_id)

            sql += f" WHERE [{SYNC_REF_COL}] = ?"
            params.append(product_ref_id)

            # print(f"[DB] Executing: {sql} with {params}")
            cur.execute(sql, params)
            self.conn.commit()
            cur.close()
        except Exception as ex:
            print(f"[DB ERROR] Failed to mark product as uploaded (product_ref_id={product_ref_id}): {ex}")

    def fetch_products_for_update(self):
        """
        Return everything the updater needs:
          Woo ID, price, style, size and ALL stock columns.
        """
        stock_select = ", ".join([f"m.[{c}]" for c in STOCK_COLS])
        # -----------------------------------------------------------------
        #  Always return id / woo_id / price.
        #  Only append j_style & size columns if STYLE_COL is configured.
        # -----------------------------------------------------------------
        select_parts = [
            f"m.[{MAIN_ID_COL}]       AS id",
            f"s.[{SYNC_EXTERNAL_COL}] AS woo_id",
            f"s.[{SYNC_PARENT_COL}]   AS parent_id",
            f"m.[RP]                  AS price",
        ]
        if STYLE_COL:
            select_parts.append(f"m.[{STYLE_COL}] AS j_style")
            select_parts.append(f"m.[{SIZE_COL}]  AS size")

        sql = "SELECT " + ", ".join(select_parts)
        if stock_select:
            sql += ", " + stock_select
        sql += (
            f" FROM [{MAIN_TABLE}] m"
            f" JOIN [{SYNC_TABLE}] s ON m.[{MAIN_ID_COL}] = s.[{SYNC_REF_COL}]"
            f" WHERE s.[{SYNC_UPLOADED_COL}] = 1"
            f"   AND s.[{SYNC_EXTERNAL_COL}] IS NOT NULL"
        )

        cur = self.conn.cursor()
        print("[DB] Executing:", sql)
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return rows

    def touch_updated(self, product_ref_id: int) -> None:
        """Just stamp updated_date = NOW() for one row in the sync table."""
        try:
            cur = self.conn.cursor()
            cur.execute(
                f"UPDATE [{SYNC_TABLE}] "
                f"SET [{SYNC_UPDATED_DATE}] = GETDATE() "
                f"WHERE [{SYNC_REF_COL}] = ?",
                (product_ref_id,)
            )
            self.conn.commit()
            cur.close()
        except Exception as ex:
            print(f"[DB ERROR] touch_updated({product_ref_id}) → {ex}")

    # ----------------------------------------------------------------------
    #  NEW: sum the stock of *every* row that matches a (J_Style , Size) pair
    # ----------------------------------------------------------------------
    def sum_stock_for_jstyle_size(self, style: str, size: str) -> int:
        """
        Aggregate stock across all rows that share the same (style, size).
        """
        sum_expr = " + ".join([f"COALESCE([{c}],0)" for c in STOCK_COLS]) or "0"
        sql = (
            f"SELECT SUM({sum_expr}) AS total "
            f"FROM [{MAIN_TABLE}] "
            f"WHERE [{STYLE_COL}] = ? AND [{SIZE_COL}] = ?"
        )
        cur = self.conn.cursor()
        cur.execute(sql, (style, size))
        result = cur.fetchone()
        cur.close()
        # result is a tuple like (value,)
        total = result[0] if result else 0
        return int(total or 0)


