"""
main.py  –  Orchestrates:  DB  ➜  Transform  ➜  WooCommerce  ➜  DB

Run it with:
    python main.py                # uses .env.dev by default
Switch to production by:
    cp .env.prod .env             # or export WOO_CK / WOO_CS vars
"""

import json, os, time, traceback
from dotenv import load_dotenv
from db import DB
from woo_api import Woo
from transform import group_rows, build_parent_and_children

def main():
    env_file = ".env.dev" if os.path.exists(".env.dev") else ".env"
    load_dotenv(env_file)
    print(f"Loaded secrets from {env_file}")

    # 1) Initialization
    print("🔄 Starting sync…")
    db  = DB()
    woo = Woo(debug=False)

    # 2) Fetch rows needing upload
    rows = db.fetch_new_rows()
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
                db.mark_uploaded(row_id, var_id)  # <-- Use the correct row ID!
            else:
                msg = v_resp.get("message", json.dumps(v_resp))
                print(f"   ✗ Variation {var_sku} failed: {msg}")

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