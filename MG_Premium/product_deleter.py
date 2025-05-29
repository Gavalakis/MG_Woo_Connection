# product_deleter.py - WooCommerce remover **or** sync-row reset by barcode
# ==============================================================================
#  What it does
#  ------------
#  • Always deletes the matching products / variations in WooCommerce **permanently**.
#  • Collects and **removes every linked image attachment** (skip with `--keep-images`).
#  • **Default DB behaviour:**
#       ▸ sets `<uploaded_past_col> = 1` (column name comes from *config.yaml*)
#       ▸ NULLs `external_id` + `parent_id` so the item can be re-exported.
#  • Add **`--purge-db`** to hard-delete rows from the sync table instead.
#
#  Configuration (config.yaml)
#  ---------------------------
#  delete_barcodes_file: delete_barcodes.txt   # default list path
#  uploaded_past_col   : uploaded_past         # << NEW - name of the flag column
#
#  Usage examples
#  --------------
#  $ python product_deleter.py                    # reset rows, remove images
#  $ python product_deleter.py --keep-images      # keep media attachments
#  $ python product_deleter.py --purge-db         # hard-delete rows
#  $ python product_deleter.py --file list.txt    # use custom list
#  $ python product_deleter.py --yes              # non-interactive run
#
#  Safety net
#  ----------
#  • Shows a reminder + preview, requires typing **YES** (skip with --yes).
#  • Renames the list to <file>.YYYYMMDD-HHMMSS.processed afterwards.
#
#  Note: The **main product table is never modified** unless a future flag is added.
# ------------------------------------------------------------------------------
from __future__ import annotations
import argparse, pathlib, sys, yaml, datetime, shutil
from collections import defaultdict
from typing import Iterable, List, Set
from dotenv import load_dotenv
from db import (
    DB, _q,
    MAIN_TABLE,
    SYNC_TABLE,
    MAIN_ID_COL,
    SYNC_REF_COL,
    SYNC_EXTERNAL_COL,
    SYNC_PARENT_COL,
    BARCODE_COL,
)
from woo_api import Woo

# ================================= helper ======================================

def _read_barcodes(path: pathlib.Path) -> Set[str]:
    if not path.exists():
        print(f"[ERROR] Barcode file '{path}' not found.")
        sys.exit(1)
    with path.open() as f:
        return {ln.strip() for ln in f if ln.strip()}


def _safety_check(path: pathlib.Path, barcodes: Set[str], *, mode: str, flag_col: str, auto_yes: bool):
    if auto_yes:
        return
    print(f"""\n*** SAFETY REMINDER ***
Open the list and double-check the SKUs!  This script PERMANENTLY removes each item from
WooCommerce and {{mode}} in the eshop sync table (column '{flag_col}').

File   : {path.name}
Count  : {len(barcodes)}
Preview: {', '.join(list(barcodes)[:10])}{'…' if len(barcodes) > 10 else ''}
""")
    if input("Type 'YES' to proceed: ").strip() != "YES":
        print("Aborted.")
        sys.exit(0)

# ---------------------- image deletion helpers --------------------------------

def _delete_media_ids(woo: Woo, media_ids: Iterable[int]) -> None:
    """Delete each WordPress media item via WP REST `/wp/v2/media/<id>?force=true`"""
    for mid in media_ids:
        try:
            woo.wc.delete(f"wp/v2/media/{mid}", params={"force": True})
        except Exception as ex:
            print(f"! Could not delete media {mid}: {ex}")


def _collect_image_ids(prod_json: dict) -> List[int]:
    ids: List[int] = [img.get("id") for img in prod_json.get("images", []) if img.get("id")]
    if prod_json.get("image") and prod_json["image"].get("id"):
        ids.append(prod_json["image"]["id"])
    return ids

# =========================== core implementation ==============================

def process_barcodes(*, barcodes: Set[str], flag_col: str, purge_db: bool, keep_images: bool, rename_file: pathlib.Path | None):
    load_dotenv(".env.dev" if pathlib.Path(".env.dev").exists() else ".env")
    db  = DB()
    woo = Woo(debug=False)

    # ---- fetch relevant sync rows -------------------------------------------------
    ph  = ", ".join(["?"] * len(barcodes))
    sql = (
        f"SELECT m.{_q(MAIN_ID_COL)}       AS ref_id,\n"
        f"       TRIM(m.{_q(BARCODE_COL)}) AS barcode,\n"
        f"       s.{_q(SYNC_EXTERNAL_COL)} AS woo_id,\n"
        f"       s.{_q(SYNC_PARENT_COL)}   AS parent_id\n"
        f"FROM {_q(MAIN_TABLE)} m\n"
        f"JOIN {_q(SYNC_TABLE)} s ON m.{_q(MAIN_ID_COL)} = s.{_q(SYNC_REF_COL)}\n"
        f"WHERE TRIM(m.{_q(BARCODE_COL)}) IN ({ph})"
    )
    cur = db.conn.cursor()
    cur.execute(sql, list(barcodes))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()

    if not rows:
        print("No matching barcodes found.")
        return

    # ---- delete on Woo ------------------------------------------------------------
    by_parent: dict[int | None, list[dict]] = defaultdict(list)
    for r in rows:
        by_parent[r["parent_id"]].append(r)

    ok = fail = 0
    for parent_id, children in by_parent.items():
        parent_json = None
        if parent_id and not keep_images:
            try:
                parent_json = woo.wc.get(f"products/{parent_id}").json()
            except Exception:
                parent_json = None
        for row in children:
            wid = row["woo_id"]
            if not wid:
                continue
            endpoint = f"products/{parent_id}/variations/{wid}" if parent_id else f"products/{wid}"
            image_ids: List[int] = []
            if not keep_images:
                try:
                    prod_json = woo.wc.get(endpoint).json()
                    image_ids.extend(_collect_image_ids(prod_json))
                except Exception:
                    pass
            try:
                resp = woo.wc.delete(endpoint, params={"force": True}).json()
                if resp.get("deleted"):
                    ok += 1
                    if not keep_images and image_ids:
                        _delete_media_ids(woo, image_ids)
                else:
                    fail += 1
            except Exception as ex:
                print(f"✗ {row['barcode']}: {ex}")
                fail += 1
        # delete parent
        if parent_id and all(r["woo_id"] for r in children):
            parent_imgs = _collect_image_ids(parent_json) if (parent_json and not keep_images) else []
            try:
                woo.wc.delete(f"products/{parent_id}", params={"force": True})
                if parent_imgs:
                    _delete_media_ids(woo, parent_imgs)
            except Exception as ex:
                print(f"! Could not delete parent {parent_id}: {ex}")

    # ---- update or purge sync table ----------------------------------------------
    ref_ids = [r["ref_id"] for r in rows]
    ph_ids  = ", ".join(["?"] * len(ref_ids))
    cur = db.conn.cursor()
    if purge_db:
        cur.execute(
            f"DELETE FROM {_q(SYNC_TABLE)} WHERE {_q(SYNC_REF_COL)} IN ({ph_ids})",
            ref_ids,
        )
        print(f"Purged {cur.rowcount} row(s) from {SYNC_TABLE}.")
    else:
        cur.execute(
            f"UPDATE {_q(SYNC_TABLE)}\n"
            f"   SET {_q(SYNC_EXTERNAL_COL)} = NULL,\n"
            f"       {_q(SYNC_PARENT_COL)}   = NULL,\n"
            f"       {_q(flag_col)}          = 1\n"
            f" WHERE {_q(SYNC_REF_COL)} IN ({ph_ids})",
            ref_ids,
        )
        print(f"Reset {cur.rowcount} row(s) in {SYNC_TABLE} ({flag_col} = 1).")
    db.conn.commit()
    cur.close()

    print(f"Woo deletions: OK={ok}, FAIL={fail}")

    # ---- archive list -------------------------------------------------------------
    if rename_file and rename_file.exists():
        ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        new_name = rename_file.with_suffix(rename_file.suffix + f".{ts}.processed")
        try:
            shutil.move(rename_file, new_name)
        except Exception:
            pass

# ================================= CLI =========================================

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Delete Woo products + reset/purge eshop sync rows by barcode list")
    p.add_argument("--file", "-f", type=pathlib.Path, help="Path to barcode list (default from config.yaml)")
    p.add_argument("--purge-db",    action="store_true", help="Actually DELETE rows from sync table (default is reset)")
    p.add_argument("--keep-images", action="store_true", help="Do NOT delete the media attachments of each product")
    p.add_argument("--yes",         action="store_true", help="Skip interactive YES prompt")
    args = p.parse_args()

    cfg_path = pathlib.Path("config.yaml")
    if not cfg_path.exists():
        print("[ERROR] config.yaml not found.")
        sys.exit(1)
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    default_file = cfg.get("delete_barcodes_file", "delete_barcodes.txt")
    flag_col     = cfg.get("uploaded_past_col", "uploaded_past")

    file_path = args.file or pathlib.Path(default_file)
    barcodes  = _read_barcodes(file_path)
    if not barcodes:
        print("[ERROR] No barcodes found.")
        sys.exit(1)

    mode = "PURGES rows" if args.purge_db else f"RESETS rows (sets {flag_col}=1)"
    _safety_check(file_path, barcodes, mode=mode, flag_col=flag_col, auto_yes=args.yes)

    process_barcodes(
        barcodes=barcodes,
        flag_col=flag_col,
        purge_db=args.purge_db,
        keep_images=args.keep_images,
        rename_file=file_path,
    )
