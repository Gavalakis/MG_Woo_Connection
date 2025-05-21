#E-shop Product Synchronization Tool

------------------------------------------------------------------------------------------------------------------
##1. Introduction
This set of scripts automates the process of synchronizing product information between a local database (such as your company's internal product system) and an online WooCommerce e-shop.

The main goal of these scripts is to:

1.Automatically upload new products to your online store.

2.Update existing product information like pricing and stock levels.

3.Provide an easy way to manually upload selected products based on barcodes.

By automating these tasks, the scripts save significant time, minimize human error, and ensure your online shop remains accurate and up-to-date.

------------------------------------------------------------------------------------------------------------------
##2. Overview of the Process
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
##3. Script Breakdown
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
Here’s a detailed but easy-to-follow guide for using the scripts:

📌 Step-by-Step Instructions:
① Prepare Your Files
Ensure you have the following files in one folder:

.env or .env.dev (with credentials)

config.yaml (configuration settings)

Script files (main.py, product_updater.py, etc.)

② Open Command Prompt
Windows:

Right-click inside the folder containing your scripts.

Select "Open in Terminal" or "Open Command Prompt Here".

Mac/Linux:

Right-click the folder, select "Open in Terminal".

③ Install Required Python Libraries
Type or copy-paste the following and press Enter:
pip install requests PyYAML python-dotenv mysql-connector-python

④ Configure Settings
Open config.yaml in any text editor (e.g., Notepad, VSCode).

Set your preferences clearly:

Brands, seasons, stock settings, barcodes (optional).

Mappings of WooCommerce attributes.

⑤ Optional: Barcode-based Upload
To manually upload specific products, create a file named barcodes.txt with one barcode per line, or specify barcodes directly in config.yaml.

⑥ Run the Scripts
In the command prompt or terminal, run:

To upload new products:
python main.py
To update existing products:
python product_updater.py


------------------------------------------------------------------------------------------------------------------
5. Configuration Guide (Expanded)
The config.yaml file contains multiple useful functionalities. Here are detailed explanations for each:

📌 Main settings:
Allowed Brands and Recent Seasons

allowed_brands:
  - BrandA
  - BrandB
recent_seasons:
  - '251'
  - '250'
Defines which brands and seasons will be synchronized.

Stock Calculation

stock_columns:
  - Warehouse1
  - Warehouse2
Specifies which warehouse stock columns to include in calculations.

📌 Barcode-specific Uploads
Inline Barcodes:

force_barcodes:
  - 1234567890
  - 0987654321
File-based Barcodes:

force_barcodes_file: barcodes.txt
📌 Advanced Product Matching (for Updater)
J-Style Column

updater:
  style_col: J_Style
  size_col: b_Size
Groups product stock based on style and size rather than barcode alone, useful when multiple barcodes represent a single product style.

📌 WooCommerce Attributes Mapping
Use WooCommerce Attribute IDs for better reliability:

woo_attributes:
  COLOR:
    id: 3
  SIZE:
    id: 2
Specifies WooCommerce Attribute IDs explicitly for stable synchronization.

📌 Parent-Child Product Handling
Allows synchronization of product variations under correct parent products by referencing WooCommerce IDs:

external_parent_id_column: woo_parent_id
Tracks and maintains product relationships easily.

------------------------------------------------------------------------------------------------------------------
6. Special Features
✅ Manual Barcode-based Uploads
Quickly and selectively upload products via barcode lists without altering other settings.

✅ Flexible Product Filtering
Choose exactly which products to upload by specifying allowed brands, seasons, or particular barcodes.

✅ Intelligent Stock Aggregation
Combines stock automatically from multiple warehouses or from multiple barcodes representing the same style.

✅ Automatic WooCommerce Attribute Handling
The system seamlessly handles WooCommerce attributes by ID mappings, preventing issues if attribute names change.

✅ Efficient Debugging and Fallbacks
Detailed logging for skipped products with clear explanations (brand or season filters).

Clear, human-readable messages explain any issues during uploads or updates.

✅ Reliable Variation Handling
Accurate management of product variations, ensuring variations remain properly grouped under their parent products in WooCommerce.

✅ Database Tracking
Automatically tracks which products have been uploaded, preventing duplicates and improving sync efficiency.

✅ Safe Operation
The scripts are designed to prevent accidental data overwrites, maintaining database integrity by updating only when necessary.

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

