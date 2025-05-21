E-shop Product Synchronization Tool

------------------------------------------------------------------------------------------------------------------
1. Introduction
This set of scripts automates the process of synchronizing product information between a local database (such as your company's internal product system) and an online WooCommerce e-shop.

The main goal of these scripts is to:

1.Automatically upload new products to your online store.

2.Update existing product information like pricing and stock levels.

3.Provide an easy way to manually upload selected products based on barcodes.

By automating these tasks, the scripts save significant time, minimize human error, and ensure your online shop remains accurate and up-to-date.

------------------------------------------------------------------------------------------------------------------
2. Overview of the Process
Here’s a simple overview of how the synchronization happens:

1.Fetching Products:

	The script checks your local database for new or updated products.

2.Filtering:

	Normally, products are filtered by predefined conditions, such as their brand and season.

	You can optionally specify exact barcodes to force-upload specific products (useful for manual overrides).

3.Preparing Data:

	Product data is cleaned, formatted, and grouped logically.

	Variations (e.g., different sizes or colors) are organized properly.

4.Uploading to WooCommerce:

	Prepared products are sent to your WooCommerce store automatically.
	
	The script uploads both main product entries and their variations.

5.Updating the Database:

	After successful uploads, the script updates your local database to remember which products have been uploaded, avoiding duplicate uploads in the future.

------------------------------------------------------------------------------------------------------------------
3. Script Breakdown
This project consists of several scripts. Here's a clear, non-technical explanation of what each script does:

① main.py
Role:
The main controller that coordinates everything.

What it does:
Fetches new products from your database, applies filters based on the configuration, and initiates uploads to WooCommerce.

② transform.py
Role:
Prepares product data.

What it does:
Cleans, organizes, and structures product details (prices, descriptions, variations, etc.) into the format required by WooCommerce.

③ product_updater.py
Role:
Updates existing WooCommerce products.

What it does:
Checks for changes in product data (such as price or stock) and automatically updates the online store accordingly.

④ woo_api.py
Role:
Connects to WooCommerce.

What it does:
Provides the essential connection functions that let other scripts upload and update products on your WooCommerce website.

⑤ db.py
Role:
Communicates with your local database.

What it does:
Handles reading from and writing to your database to track product uploads and updates.

⑥ config.yaml
Role:
Easy-to-edit settings file.

What it does:
Lets you control script behavior without changing any actual programming code. It includes options like filtering products, barcode uploading, and handling specific product conditions.

------------------------------------------------------------------------------------------------------------------
4. How to Use
Here's how you get started using the scripts in a few clear steps:

Step-by-step Instructions:
① Set Up Environment
Create or edit a .env or .env.dev file to hold secure credentials (database passwords, WooCommerce API keys, etc.).

② Configure Settings
Edit config.yaml to adjust script behavior according to your needs. You can set brands, seasons, stock handling, and optional barcode uploads.

③ Barcode Upload (Optional)
To manually specify products, create a file named barcodes.txt with one barcode per line, or list barcodes directly inside config.yaml.

④ Running the Scripts
Run main.py in CMD to upload new products to WooCommerce:
python main.py

Run product_updater.py to refresh existing products' data:
python product_updater.py

Important Files Explained:
.env or .env.dev
Secure credentials: Database passwords, WooCommerce keys, etc.

config.yaml
Script behavior settings: Adjust what gets uploaded and how.

barcodes.txt (Optional)
Barcode-based uploading: Manually specify which exact products to upload.

------------------------------------------------------------------------------------------------------------------
5. Configuration Guide
The config.yaml file lets you control how the scripts behave. Here's what the main settings do, explained simply:

Essential settings:
Brands and Seasons

yaml
Copy
Edit
allowed_brands:
  - BrandA
  - BrandB
recent_seasons:
  - '251'
  - '250'
Defines which product brands and recent seasons will be uploaded.

Stock Calculation

yaml
Copy
Edit
stock_columns:
  - Warehouse1
  - Warehouse2
Chooses which warehouses’ stock counts to include when calculating total available stock.

Optional Barcode Upload:
Inline Barcodes

yaml
Copy
Edit
force_barcodes:
  - 1234567890
  - 0987654321
Forces upload only of these specific barcodes.

Barcodes from File

yaml
Copy
Edit
force_barcodes_file: barcodes.txt
Reads a list of barcodes from a text file (barcodes.txt) instead of defining them inline.

------------------------------------------------------------------------------------------------------------------
6. Special Features
✅ Manual Barcode-based Uploads
Easily specify particular products to upload (useful for special cases or urgent updates).

Simply create a barcodes.txt file or add barcode numbers in config.yaml.

✅ Flexible Product Filtering
Choose exactly which products get uploaded by adjusting allowed brands and recent seasons.

✅ Automatic Stock Aggregation
Automatically calculates and updates total stock from multiple warehouse locations.

------------------------------------------------------------------------------------------------------------------
7. Troubleshooting and FAQs (Please update this list if problems arise, for future reference)
🔹 I ran the script, but no products were uploaded. Why?
Ensure your database has new products that match the allowed brands and recent seasons in config.yaml.

Double-check barcode uploads (barcodes.txt or inline barcodes).

🔹 Error: “Missing API credentials”
Confirm you've correctly filled in your WooCommerce API keys in .env or .env.dev.

🔹 Products not updating properly in WooCommerce
Ensure you're running product_updater.py after changes in the database.

Verify WooCommerce permissions and product IDs are correct.

🔹 How do I upload specific products quickly?
Add their barcodes to barcodes.txt or force_barcodes in config.yaml, then run main.py. Remember to remove these additions afterwards.

🔹 Can I change stock calculation easily?
Yes, just edit the stock_columns in your config.yaml.

------------------------------------------------------------------------------------------------------------------
8. Technical Requirements
To use these scripts, make sure your environment meets these requirements:

📌 Required Software:
Python (v3.8 or higher)
Download Python

WooCommerce (with REST API enabled)
WooCommerce REST API Documentation

MySQL or compatible database
(e.g., MariaDB, MySQL Workbench)

📌 Python Libraries:
These Python packages are required:

requests

PyYAML

python-dotenv

mysql-connector-python

Install them easily via pip:

bash
Copy
Edit
pip install requests PyYAML python-dotenv mysql-connector-python
📌 Credentials and Setup Files:
WooCommerce API keys (.env file)

Database connection details (.env file)

Configuration settings (config.yaml)

------------------------------------------------------------------------------------------------------------------
9. Contact & Contributions
📧 Contact
For questions, support, or bug reports, please contact:

Email: nikos@mgpremium.com

