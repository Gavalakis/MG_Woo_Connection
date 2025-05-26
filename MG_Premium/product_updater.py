import os, yaml, pathlib
from dotenv import load_dotenv
from db import DB
from woo_api import Woo

# ----- config that we need only once -----
_cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text(encoding="utf-8"))
STOCK_COLUMNS = _cfg.get("stock_columns", [])

# ----- NEW: guard against None -----
STYLE_COL = (_cfg.get("updater", {}).get("style_col") or "").strip()
SIZE_COL  = (_cfg.get("updater", {}).get("size_col")  or "").strip()
USE_STYLE = bool(STYLE_COL)  

def main() -> None:
    env_file = ".env.dev" if os.path.exists(".env.dev") else ".env"
    load_dotenv(env_file)
    print(f"Loaded secrets from {env_file}")

    db  = DB()
    woo = Woo(debug=False)

    products = db.fetch_products_for_update()
    print(f"Found {len(products)} products to update.")

    # 1) Duplicate detection only when we really care about J_Style
    dup_count = {}
    if USE_STYLE:
        for r in products:
            key = (r.get("j_style"), r.get("size"))
            dup_count[key] = dup_count.get(key, 0) + 1

    combined_cache = {}
    updated = failed = 0

    for row in products:
        woo_id  = row["woo_id"]
        price   = row["price"]
        # ---------- stock calculation ----------
        if USE_STYLE:
            key = (row.get("j_style"), row.get("size"))
            # aggregate only if this (style,size) appears >1 times **and**
            # the style field is non-empty
            if key[0] and dup_count.get(key, 0) > 1:
                if key not in combined_cache:
                    combined_cache[key] = db.sum_stock_for_jstyle_size(*key)
                total_stock = combined_cache[key]
            else:
                total_stock = sum(int(row.get(c) or 0) for c in STOCK_COLUMNS)
        else:
            # feature disabled → always use per-row stock
            total_stock = sum(int(row.get(c) or 0) for c in STOCK_COLUMNS)

        payload = {
            "regular_price": str(price) if price is not None else "",
            "manage_stock" : True,
            "stock_quantity": total_stock
        }

        try:
            parent_id = row.get("parent_id")
            if parent_id:                                 # variation
                endpoint = f"products/{parent_id}/variations/{woo_id}"
            else:                                         # simple product
                endpoint = f"products/{woo_id}"
            resp = woo.wc.put(endpoint, payload).json()
            if "id" in resp:
                updated += 1
                db.touch_updated(row["id"])
                print(f"✔ Woo variation ID {woo_id}: new price={payload['regular_price']} new stock={total_stock}")
            else:
                failed += 1
                print(f"✗ Woo variation ID {woo_id} failed: {resp}")
        except Exception as ex:
            failed += 1
            print(f"✗ Exception for Woo variation ID {woo_id}: {ex}")

    print(f"Done: {updated} updated, {failed} failed.")

if __name__ == "__main__":
    main()
