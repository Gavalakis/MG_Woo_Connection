
# E‑shop Product Synchronization Tool

**Automate product uploads, updates, and stock management between your local database and WooCommerce.**

---

## 1. Introduction
This project is a collection of Python scripts that keep your WooCommerce shop in sync with your internal product database.

**Main goals**

1. *Upload* new products to WooCommerce automatically.  
2. *Update* prices, stock, and attributes of existing products.  
3. *Manually* push specific products by barcode when you need to.

Automation saves hours of manual data entry, eliminates human error, and keeps your online catalogue accurate.

---

## 2. Overview of the Process
1. **Fetch products** – read new or changed rows from your database.  
2. **Filter** – apply brand/season rules or an explicit barcode list.  
3. **Transform** – clean data and structure parents + variations.  
4. **Upload** – create or update items in WooCommerce via REST API.  
5. **Mark as synced** – flag rows in the database so they won't be duplicated next time.

---

## 3. Script Breakdown
| Script | Role | What it does |
| ------ | ---- | ------------ |
| `main.py` | **Coordinator** | Finds new rows, filters, and triggers uploads. |
| `transform.py` | **Data prep** | Cleans and formats product data for WooCommerce. |
| `product_updater.py` | **Updater** | Refreshes price, stock, and attributes for products that already exist online. |
| `woo_api.py` | **Connector** | Thin wrapper around the WooCommerce REST API. |
| `db.py` | **Database I/O** | Reads from / writes to your MySQL / MariaDB tables. |
| `config.yaml` | **Settings** | One-stop file to control all behaviour—no code edits required. |

---

## 4. How to Use

### 4.1 Prepare Your Workspace
1. Put **all scripts** plus your `.env`/`.env.dev`, `config.yaml`, and (**optional**) `barcodes.txt` in the **same folder**.
2. Open a terminal **in that folder**.  
   *Windows ▶* right‑click → “Open in Terminal”.  
   *macOS/Linux ▶* right‑click → “Open in Terminal”.

### 4.2 Install Python Libraries
```bash
pip install requests PyYAML python-dotenv mysql-connector-python woocomerce
```

### 4.3 Configure
* Edit `config.yaml` with your favourite text editor.  
* Fill in brands, seasons, stock columns, attribute mappings, etc.  
* Store WooCommerce keys and DB credentials in `.env` / `.env.dev`.

### 4.4 (Optional) Barcode Push
*List barcodes* in `config.yaml` → `force_barcodes:` **or** create a plain‑text `barcodes.txt` (one barcode per line).

### 4.5 Run!
```bash
# First‑time uploads
python main.py

# Routine stock / price updates
python product_updater.py
```

---

## 5. Configuration Guide

```yaml
# config.yaml (abridged)
allowed_brands:    # only these brands are synced
  - BrandA
  - BrandB

season_logic: #Season codes are calculated automatically based on current date and the following logic.
  summer_cutoff:
    month: 3   # March
    day: 1
  winter_cutoff:
    month: 9   # September
    day: 1
  num_recent: 2 #The number of seasons to be considered as recent.

stock_columns:     # warehouses to sum for total stock
  - MGP_HQ
  - WBM

# --- manual barcode mode ---------------------------------
force_barcodes: []           # inline list
force_barcodes_file: barcodes.txt

# --- updater grouping ------------------------------------
updater:
  style_col: J_Style         # group by style. leave empty to turn off.
  size_col:  b_Size          # & size for stock aggregation

# --- Woo attribute IDs -----------------------------------
woo_attributes:
  COLOR: {id: 3}
  SIZE:  {id: 2}

external_parent_id_column: woo_parent_id
```

### What the settings do
* **Brands/Seasons** – restrict uploads to the latest collections.  
* **Stock columns** – choose which warehouses count toward inventory.  
* **J‑Style grouping** – if several barcodes share a style, their stock is merged before pushing.  
* **Woo attribute IDs** – using numeric IDs is safer than names; they never change.  
* **Parent ID column** – keeps variations attached to the right parent.

---

## 6. Special Features & Safeguards
- **Manual barcode uploads** – instant override without touching filters.  
- **Smart filtering** – skip unwanted brands/seasons automatically.  
- **Multi‑warehouse aggregation** – sums stock across any columns you list.  
- **Attribute ID mapping** – avoids “attribute not found” errors if names change.  
- **Clear logging** – every skip or failure is printed with a human‑friendly reason.  
- **Reliable variation handling** – parents and kids stay linked.  
- **Idempotent sync** – already‑uploaded rows are ignored, so reruns are safe.  
- **Fallbacks everywhere** – missing columns/config just trigger warnings, not crashes.

---

## 7. Troubleshooting & FAQs
<details>
<summary>Nothing uploaded, what’s wrong?</summary>

*Check your filters:* does the product’s brand + season pass `config.yaml` rules?  
*Using barcode mode?* Make sure the barcode is in `barcodes.txt` **and** the column name in the DB matches `barcode_column`.
</details>

<details>
<summary>“Missing API credentials” error</summary>

Double‑check `.env` / `.env.dev` for `WC_API_KEY` and `WC_API_SECRET`.
</details>

<details>
<summary>Products not updating</summary>

Run `product_updater.py` **after** changing stock/price in the DB.  
Confirm WooCommerce user has `read/write` REST permissions.
</details>

---

## 8. Technical Requirements
| Requirement | Version / Notes |
| ----------- | --------------- |
| Python | 3.0 + |
| WooCommerce | REST API enabled |
| Database | MySQL / MariaDB |
| Python libs | `requests`, `pyyaml`, `python-dotenv`, `mysql-connector-python`, `woocommerce` |

---

## 9. Contact & Contributions
* **Email:** nickgaval13+github@gmail.com.

Contributions are welcome! Fork → create a branch → PR.

---

**Happy syncing!** 🎉
