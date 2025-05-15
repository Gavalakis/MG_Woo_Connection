# woo_api.py
import os
from woocommerce import API

class Woo:
    def __init__(self, debug=False):
        # 1) Read your keys from ENV
        self.wc = API(
            url         = os.getenv("WOO_SITE_URL"),
            consumer_key= os.getenv("WOO_CK"),
            consumer_secret=os.getenv("WOO_CS"),
            version     = "wc/v3",
            timeout     = 20
        )
        self.debug = debug

    def post_product(self, data):
        """
        Create or update a product.
        If SKU already exists, attempt to update instead.
        Returns the JSON response dict.
        """
        if self.debug:
            print("[Woo] POST /products payload:", data)

        # try create
        def _create_or_update(payload):
            """Helper: try create, then on SKU conflict update."""
            r = self.wc.post("products", payload).json()
            if r.get("code") in ("product_invalid_sku", "woocommerce_rest_product_not_created"):
                # Attempt to find existing product by SKU
                existing = self.wc.get("products", params={"sku": payload["sku"]}).json()
                if existing:
                    prod_id = existing[0]["id"]
                    if self.debug:
                        print(f"[Woo] SKU exists, updating product {prod_id}")
                    r = self.wc.put(f"products/{prod_id}", payload).json()
                else:
                    # No existing product found—log and return original error
                    print(f"[Woo] Warning: SKU conflict for '{payload['sku']}' but no existing product found.")
            return r

        # 1) Try full payload
        resp = _create_or_update(data)

        # 2) If image fetch error, retry without images (and handle SKU conflict again)
        if resp.get("code") == "woocommerce_product_image_upload_error":
            print(f"[Woo] Warning: image upload failed for SKU {data.get('sku')}, retrying without images…")
            data_no_images = {k: v for k, v in data.items() if k != "images"}
            resp = _create_or_update(data_no_images)
        return resp


    def post_variation(self, parent_id, data):
        """
        Create or update a variation under parent_id.
        Handles SKU conflicts similarly.
        """
        if self.debug:
            print(f"[Woo] POST /products/{parent_id}/variations payload:", data)

        resp = self.wc.post(f"products/{parent_id}/variations", data).json()
        # if SKU conflict, Woo returns product_invalid_sku
        if resp.get("code") == "product_invalid_sku":
            # you could implement an update-on-conflict here if desired
            raise Exception(f"Variation SKU conflict: {resp}")
        return resp