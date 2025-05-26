"""
main.py  –  Orchestrates:  DB  ➜  Transform  ➜  WooCommerce  ➜  DB

Run it with:
    python main.py                # uses .env.dev by default
Switch to production by:
    cp .env.prod .env             # or export WOO_CK / WOO_CS vars
"""

import json, os, time, traceback, yaml, pathlib
from dotenv import load_dotenv
from db import DB
from woo_api import Woo
from transform import group_rows, build_parent_and_children
from pathlib import Path

def main():
    env_file = ".env.dev" if os.path.exists(".env.dev") else ".env"
    load_dotenv(env_file)
    print(f"Loaded secrets from {env_file}")
    

    # ------- Read optional barcode list ------------------------------
    cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text(encoding="utf-8"))
    col_name = cfg.get("barcode_column", "b_Barcode")

    # Gather barcodes from config and file, stripping ALL whitespace
    barcodes_cfg = {str(b).strip() for b in cfg.get("force_barcodes", [])}

    file_path = cfg.get("force_barcodes_file")
    if file_path and pathlib.Path(file_path).exists():
        with open(file_path, encoding="utf-8") as f:
            for ln in f:
                ln_clean = ln.strip()
                if ln_clean:
                    barcodes_cfg.add(ln_clean)

    # Clean the set: remove blanks and ensure everything is a string with no whitespace
    FORCE_BARCODES = {str(b).strip() for b in barcodes_cfg if str(b).strip()}

    if FORCE_BARCODES:
        os.environ["FORCE_UPLOAD"] = "1"          # let transform.py know
        print(f"📌  Force-upload mode – {len(FORCE_BARCODES)} barcode(s) supplied")
    # ------------------------------------------------------------------

    # 1) Initialization
    print("🔄 Starting sync…")
    db  = DB()
    woo = Woo(debug=False)

    # 2) Fetch rows needing upload
    rows = db.fetch_new_rows(FORCE_BARCODES)
    if FORCE_BARCODES:                            
        rows = [r for r in rows
                if str(r.get(col_name, "")).strip() in FORCE_BARCODES]
        
    print(f"▶ Found {len(rows)} rows to sync.\n")

    # 3) Group rows by parent (style+color)
    buckets = group_rows(rows)
    for parent_sku, bucket in buckets.items():
        print(f"--- Syncing parent {parent_sku} ---")

        # 4) Build payloads
        parent_json, variations = build_parent_and_children(bucket)
        if not parent_json:
            print(f"⚠ Skipped {parent_sku} (filtered out)\n")
            continue

        # 5) POST parent
        p_resp = woo.post_product(parent_json)  
        if "id" not in p_resp:
            msg = p_resp.get("message", json.dumps(p_resp))
            print(f"✗ Parent {parent_sku} failed: {msg}\n")
            continue
        parent_id = p_resp["id"]
        print(f"✔ Parent uploaded: {parent_sku} → Woo ID {parent_id}")

        # 6) POST each variation
        for var, row_id in variations:
            var_sku = var["sku"]
            v_resp = woo.post_variation(parent_id, var)
            if "id" in v_resp:
                var_id = v_resp["id"]
                print(f"   ✔ Variation uploaded: {var_sku} → Woo ID {var_id}")
                db.mark_uploaded(product_ref_id=row_id, parent_id=parent_id, external_id=var_id)
            else:
                msg = v_resp.get("message", json.dumps(v_resp))
                print(f"   ✗ Variation {var_sku} failed: {msg}")
        time.sleep(1)
        print("")  # blank line between parents

    print("✅ Sync complete.")

if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print("[FATAL] Unhandled error in main():")
        import traceback
        traceback.print_exc()
        exit(1)