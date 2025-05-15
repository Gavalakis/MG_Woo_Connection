"""
main.py  –  Orchestrates:  DB  ➜  Transform  ➜  WooCommerce  ➜  DB

Run it with:
    python main.py                # uses .env.dev by default
Switch to production by:
    cp .env.prod .env             # or export WOO_CK / WOO_CS vars
"""

from dotenv import load_dotenv
import os, time, traceback
from db import DB
from transform import group_rows, build_parent_and_children
from woo_api import Woo

# -----------------------------------------------------------
# 0.  Choose environment: .env.dev for sandbox
# -----------------------------------------------------------
env_file = ".env.dev" if os.path.exists(".env.dev") else ".env"
load_dotenv(env_file)
print(f"Loaded secrets from {env_file}")

# -----------------------------------------------------------
# 1.  Initialise helpers
# -----------------------------------------------------------
db  = DB()            # reads table name & cols from config.yaml
woo = Woo(debug=False)           # wrapper around woocommerce.API

# -----------------------------------------------------------
# 2.  Fetch rows that still need uploading
# -----------------------------------------------------------
rows = db.fetch_new_rows()
print(f"Rows fetched from DB: {len(rows)}")
if not rows:
    print("Nothing to sync. Exiting.")
    raise SystemExit

# -----------------------------------------------------------
# 3.  Bucket rows by parent_key (style-colour)
# -----------------------------------------------------------
for parent_key, bucket in group_rows(rows).items():
    
    #POST FUNCTION 
    print("\n=== Processing parent group:", parent_key, "===")

    try:
        # Build parent + variation payloads (None means “skip”)
        res = build_parent_and_children(bucket)
        if res[0] is None:
            print(f"Skipping {parent_key}: filtered by brand/season")
            continue
        parent_json, children_json = res

        #print("DEBUG parent.meta_data:", json.dumps(parent_json["meta_data"], indent=2))     DEFINE JSON


        # 3-B ─ Parent: POST (or reuse if duplicate SKU)
        p_resp = woo.post_product(parent_json)
        # if Woo returned an error, it won’t have "id"
        if "id" not in p_resp:
            print(f"✗ Failed to create/update parent {parent_json['sku']}: {p_resp}")
            # skip this group so we don’t crash on variations
            continue
        parent_id = p_resp["id"]
        print(f"✓ Parent {parent_json['sku']} id {parent_id}")

        # 3-C ─ Variations
        for child_json, db_row in zip(children_json, bucket):
            c_resp = woo.post_variation(parent_id, child_json)
            child_id = c_resp["id"]
            print(f"  ↳ Variation {child_json['sku']} id {child_id}")

            # mark the source row as uploaded
            db.mark_uploaded(db_row["id"], child_id)
            time.sleep(0.3)              # be polite to Woo API

    except Exception as exc:
        print("✗ ERROR while processing", parent_key)
        traceback.print_exc()
        # you might log exc to a file here and continue next group
        continue

print("\nSync complete.")