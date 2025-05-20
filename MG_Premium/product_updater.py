import os
from dotenv import load_dotenv
import yaml, pathlib
from db import DB
from woo_api import Woo

def main():
    env_file = ".env.dev" if os.path.exists(".env.dev") else ".env"
    load_dotenv(env_file)
    print(f"Loaded secrets from {env_file}")

    # Load stock_columns from config.yaml
    _cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text())
    stock_columns = _cfg.get("stock_columns", [])

    db = DB()
    woo = Woo(debug=False)

    products = db.fetch_products_for_update()
    print(f"Found {len(products)} products to update.")

    updated, failed = 0, 0

    for row in products:
        woo_id = row["woo_id"]
        price = row["price"]

        # Sum all warehouse stock columns exactly as defined in YAML
        total_stock = 0
        for col in stock_columns:
            val = row.get(col)
            try:
                if val is not None and str(val).strip() != "":
                    total_stock += int(val)
            except Exception:
                print(f"  [WARN] Non-integer stock value for {col} in product {woo_id}: {val}")

        payload = {
            "regular_price": str(price) if price is not None else "",
            "manage_stock": True,
            "stock_quantity": total_stock
        }

        try:
            resp = woo.wc.put(f"products/{woo_id}", payload).json()
            if "id" in resp:
                updated += 1
                print(f"✔ Updated Woo ID {woo_id}: price={payload['regular_price']} stock={payload['stock_quantity']}")
            else:
                failed += 1
                print(f"✗ Failed update for Woo ID {woo_id}: {resp}")
        except Exception as ex:
            failed += 1
            print(f"Exception for Woo ID {woo_id}: {ex}")

    print(f"Done: {updated} updated, {failed} failed.")

if __name__ == "__main__":
    main()

