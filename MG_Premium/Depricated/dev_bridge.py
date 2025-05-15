from dotenv import load_dotenv
import os, json, time
import mysql.connector
from woocommerce import API

# ------------------------------------------------------------------
# 0.  load secrets (.env.dev for sandbox, .env for prod later)
# ------------------------------------------------------------------
load_dotenv(".env.dev")                 # change to ".env" in production

# --- DB connection -------------------------------------------------
DB = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    port=int(os.getenv("DB_PORT")),
    database=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
)
cur = DB.cursor(dictionary=True)

# --- WooCommerce REST client --------------------------------------
wc = API(
    url="https://magnolia-grace.gr",    # <— dev store URL
    consumer_key=os.getenv("WOO_CK"),
    consumer_secret=os.getenv("WOO_CS"),
    version="wc/v3",
)

# ------------------------------------------------------------------
# 1.  fetch rows that still need uploading
# ------------------------------------------------------------------
cur.execute("SELECT * FROM products WHERE uploaded = 0")
rows = cur.fetchall()
if not rows:
    print("Nothing to upload.")
    exit()

# group rows by parent_key (= style–colour)
parents = {}
for r in rows:
    parents.setdefault(r["parent_key"], []).append(r)

# ------------------------------------------------------------------
# 2.  loop each parent group
# ------------------------------------------------------------------
for key, children in parents.items():
    parent_row = children[0]

    parent_payload = {
        "name":        parent_row["title"],
        "type":        "variable",
        "sku":         key,                                   # e.g. 37777-7314
        "description": parent_row["description"],
        "attributes": [{
            "name":      "Size",
            "variation": True,
            "visible":   True,
            "options":   sorted({c["size"] for c in children})
        }]
    }

    # -- attempt to create the parent ------------------------------
    resp = wc.post("products", data=parent_payload)
    print("\nPOST parent:", json.dumps(parent_payload))
    print("  → status", resp.status_code)
    print("  → body  ", resp.text[:200], "...")              # first 200 chars

    data = resp.json()

    # handle duplicate-SKU gracefully
    if resp.status_code == 400 and data.get("code") == "woocommerce_rest_duplicate_sku":
        # look up the existing product by SKU
        existing = wc.get("products", params={"sku": key}).json()
        parent_id = existing[0]["id"]
        print(f"  ✓ parent SKU exists, re-using id {parent_id}")
    elif "id" in data:
        parent_id = data["id"]
        print(f"  ✓ parent created id {parent_id}")
    else:
        print("  ✗ parent create failed, skipping this group.")
        continue

    # -- 3. create / update each variation -------------------------
    for c in children:
        child_payload = {
            "sku":            c["sku"],                      # e.g. 37777-7314-S
            "regular_price":  str(c["price"]),
            "manage_stock":   True,
            "stock_quantity": int(c["stock"]),
            "attributes": [{ "name": "Size", "option": c["size"] }],
            "meta_data": [{ "key": "_barcode", "value": c["barcode"] }],
        }
        print("    ↳ POST variation:", json.dumps(child_payload))
        v_resp = wc.post(f"products/{parent_id}/variations", data=child_payload)
        print("       → status", v_resp.status_code)
        print("       → body  ", v_resp.text[:160], "...")

        v_data = v_resp.json()

        if v_resp.status_code == 400 and v_data.get("code") == "product_invalid_sku":
            # variation already exists – look it up and reuse its id
            existing_var = wc.get(f"products/{parent_id}/variations",
                                params={"sku": c["sku"]}).json()
            if existing_var:
                child_id = existing_var[0]["id"]
                print(f"       ✓ SKU exists, re-using id {child_id}")
            else:
                print("       ✗ duplicate SKU but couldn’t fetch it; skipping")
                continue
        elif "id" in v_data:
            child_id = v_data["id"]
            print(f"       ✓ variation created id {child_id}")
        else:
            print("       ✗ variation failed (not marking uploaded)")
            continue

        # mark DB row uploaded
        cur.execute("UPDATE products SET uploaded = 1, woo_id = %s WHERE id = %s",
                    (child_id, c["id"]))
        DB.commit()

        time.sleep(0.3)      # small pause to be polite to Woo API

print("\nAll done.")
