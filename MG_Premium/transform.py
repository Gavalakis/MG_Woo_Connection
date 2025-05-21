# transform.py  – turn raw DB rows into Woo JSON
# -------------------------------------------------
import yaml, pathlib, re, datetime, os
from collections import defaultdict

# -------------------------
# load YAML once
# -------------------------
_cfg = yaml.safe_load(pathlib.Path("config.yaml").read_text())

# Handy aliases from config.yaml
_fmap         = _cfg["field_map"]
_attr_rules   = _cfg["attributes"]
_color_map    = _cfg["color_mapping"]
_computed_map = _cfg["computed"]

# Size ordering aliases from config.yaml
sizes_order = [x.lower() for x in _cfg.get("sizes_order", [])]
cups_order = [x.upper() for x in _cfg.get("cups_order", [])]

# Images from config.yaml
_img_cfg = _cfg["images"]
_img_cols = _img_cfg["columns"]
base_url = _img_cfg["base_url"]
file_ext = _img_cfg.get("file_ext", ".jpg")
skip_empty = _img_cfg.get("skip_empty", True)

# Season logic from config.yaml
season_cfg = _cfg.get("season_logic", {})
summer_month = season_cfg.get("summer_cutoff", {}).get("month", 3)
summer_day   = season_cfg.get("summer_cutoff", {}).get("day", 1)
winter_month = season_cfg.get("winter_cutoff", {}).get("month", 9)
winter_day   = season_cfg.get("winter_cutoff", {}).get("day", 1)
num_recent   = season_cfg.get("num_recent", 2)

# Filters from config.yaml 
_filters = _cfg.get("filters", {})
_allowed_brands = {b.strip().lower() for b in _filters.get("allowed_brands", [])}

# List of warehouse columns used to compute actual stock
_stock_columns = _cfg.get("stock_columns", [])

# -------------------------
# helper: debugging. Call to return a 0 anywhere you choose.
# -------------------------
def noop(row):
    """Always return zero or a fixed test value."""
    return 0

# -------------------------
# helper: concat style+color
# -------------------------
def concat_style_color(row):
    return f"{row['b_Style'].strip()}-{row['b_Color'].strip()}"

def same_as_parent_key(row):
    return concat_style_color(row)

# -------------------------
# helper: compute seasons
# -------------------------
def recent_season_codes():
    """
    Return a set of most recent season codes:
      - the logic is set in config.yaml
    """
    today = datetime.date.today()
    yy    = today.year % 100

    # Determine current and previous season codes using config
    # Summer
    if (today.month, today.day) >= (summer_month, summer_day):
        summer = f"{yy}1"
    else:
        summer = f"{yy-1:02d}1"
    # Winter
    if (today.month, today.day) >= (winter_month, winter_day):
        winter = f"{yy}2"
    else:
        winter = f"{yy-1:02d}2"

    # Collect most recent N season codes (e.g., {242, 241})
    seasons = []
    if num_recent >= 2:
        seasons.append(winter)
        seasons.append(summer)
        # If you want more, go further back:
        y_prev = (today.year-1) % 100
        if num_recent > 2:
            seasons.append(f"{y_prev}2")  # previous winter
        if num_recent > 3:
            seasons.append(f"{y_prev}1")  # previous summer
        # ...extend logic as needed
    else:
        seasons = [winter]  # fallback

    return set(seasons[:num_recent])

def current_season_code():
    """
    Return only the most recent single season code:
      - Winter if ≥ Sept 1 (YY2)
      - Else Summer if ≥ Mar 1 (YY1)
      - Else last year's Winter
    """
    today = datetime.date.today()
    yy    = today.year % 100
    if (today.month, today.day) >= (9,1):
        return f"{yy}2"
    if (today.month, today.day) >= (3,1):
        return f"{yy}1"
    return f"{yy-1:02d}2"

# -------------------------
# color + stock helpers (re-used from script)
# -------------------------
def size_sort_key(s):
    s_clean = s.strip().lower()
    m = re.match(r"^(\d+)([a-z]+)$", s_clean)
    if m:
        band = int(m.group(1))
        cup  = m.group(2).upper()
        try:
            cup_idx = cups_order.index(cup)
        except ValueError:
            cup_idx = ord(cup[0]) if cup else 999
        return (0, band, cup_idx)
    if s_clean in sizes_order:
        return (1, sizes_order.index(s_clean))
    return (2, s_clean)

def sort_sizes_naturally(sizes):
    sizes = [s.strip() for s in sizes if s.strip()]
    return sorted(set(sizes), key=size_sort_key)

def calculate_actual_stock(row):
    """
    Sums the actual stock from all warehouses defined in config.yaml.
    """
    total = 0
    for col in _stock_columns:
        try:
            # cast to str so ints don’t break .strip()
            value = str(row.get(col, "")).strip() or "0"
            total += int(value)
        except ValueError:
            # non‐numeric entries count as zero
            pass
    return total

def calculate_safe_stock(row):
    actual = calculate_actual_stock(row)
    if actual <= 0:      return 0
    if actual <= 5:      return max(0, actual-1)
    if actual <= 10:     return max(0, actual-1)
    return max(0, actual)

def return_color_sum(row):
    return sum(1 for c in ["c_P1","c_P2","c_P3","c_P4","c_P5"] if row.get(c,"").strip())

# -------------------------
# image URL builder
# -------------------------
def build_images_url(row, skujoin):
    urls = []
    for col in _img_cols:
        val = row.get(col)
        if skip_empty and not val:
            continue
        # just update YAML or this line to use a format string from config.
        #urls.append(f"{base_url}/{skujoin}/{val}{file_ext}")
        urls.append(f"{base_url}/{val}{file_ext}") #--------------------------------------------FOR TESTING PURPOSES
    return [{"src": u} for u in urls]

# -------------------------
# category breadcrumb
# -------------------------
def _normalize_crumb(s: str) -> str:
    """
    Normalize a breadcrumb string for lookup:
      - split on '>'    
      - strip whitespace around each part
      - lowercase everything
      - rejoin with a single '>'
    """
    parts = [p.strip().lower() for p in s.split(">")]
    return ">".join(parts)

def build_categories(row) -> str:
    """
    Return a single comma-separated breadcrumb string
    (e.g.  'CLOTHING>Tights,BRANDS>Hanro').
    The helper is called by transform.build_parent_payload().
    """
    categories = []

    # cast everything to str before .strip(), to guard against ints
    gender = str(row.get("Gender",   "")).strip()
    l1     = str(row.get("L_1",      "")).strip()
    l2     = str(row.get("L_2",      "")).strip()
    l3     = str(row.get("L_3",      "")).strip()
    cl2    = str(row.get("c_L2",     "")).strip()
    season = str(row.get("L_Sea",    "")).strip()
    brand_name= str(row.get("Brand", "")).strip()


    #ALL Current Season
    if season == current_season_code() and (l2 == "T" or (l2 == "E" and cl2 == "F")):
      #All New In
      if gender == "W" and l1 in ("LW", "RW", "UW", "SW", "BW", "AC", "AW", "HW", "NW"):
        categories.append("NEW IN>All New In")
      #Clothing
      if gender == "W" and l1 == "RW":
        categories.append("NEW IN>Clothing")
      #Intimates
      if gender == "W" and l1 == "UW":
        categories.append("NEW IN>Intimates")
      #Swimwear
      if gender == "W" and l1 in ("SW", "BW"):
        categories.append("NEW IN>Swimwear")
      #Men's Corner
      if gender == "M" and l1 in ("LW", "RW", "UW", "SW", "BW", "AC", "AW", "HW", "NW"):
        categories.append("NEW IN>Men's Corner")

    #Womens
    if gender == "W":
      #CLOTHING
      #All Clothing
      if l1 in ("RW", "AC", "LW"):
        categories.append("CLOTHING>All Clothing")
      #Bodysuits
      if l3 == "RW BODIES" or l3 == "RW STRING BODIES":
        categories.append("CLOTHING>Bodysuits")
      #Tops
      if l3 in ("RW T-SHIRTS", "RW SHIRTS", "RW TOPS", "RW BLOUSES", "RW TUNICS", "RW SWEATSHIRTS", "RW POLOS"):
        categories.append("CLOTHING>Tops")
      #Trousers & Leggings
      if l3 in ("RW PANTS", "RW LEGGINGS", "LW LEGGINGS"):
        categories.append("CLOTHING>Trousers & Leggings")
      #Dresses
      if l3 == "RW DRESSES":
        categories.append("CLOTHING>Dresses")
      #Shorts & Skirts
      if l3 == "RW SKIRTS" or l3 == "RW SHORTS":
        categories.append("CLOTHING>Shorts & Skirts")
      #Activewear
      if l1 == "AC":
        categories.append("CLOTHING>Activewear")
      #Cover Ups
      if l3 in ("RW BLAZERS", "RW BOLEROS", "RW CARDIGANS", "RW COATS", "RW JACKETS", "RW PONCHOS", "RW TUNICS", "RW VESTS", "RW SUITS"):
        categories.append("CLOTHING>Cover Ups")
      #Tights
      if l3 in ("LW TIGHTS", "LW STAY UPS", "LW KNEE-HIGHS", "LW OVERKNEES"):
        categories.append("CLOTHING>Tights")
      #Socks
      if l3 == "RW SOCKS":
        categories.append("CLOTHING>Socks")
      #Accessories
      if l3 == "RW ACCESSORIES":
        categories.append("CLOTHING>Accessories")

      #INTIMATES
      #All Intimates
      if l1 in ("UW", "NW", "HW", "FW"):
        categories.append("INTIMATES>All Intimates")
      #Bras
      if l3 == "UW BRAS":
        categories.append("INTIMATES>Bras")
      #D+ Cups
      if l1 == "UW" and any(letter in row.get("Cup","") for letter in "DEFGH"):
        categories.append("INTIMATES>D+ Cups")
      #Panties
      if l3 == "UW BRIEFS" or l3 == "UW PANTIES":
        categories.append("INTIMATES>Panties")
      #Bodies
      if l3 == "UW BODIES" or l3 == "UW STRING BODIES":
        categories.append("INTIMATES>Bodies")
      #Shape & Control
      if l1 in ("UW", "NW", "HW") and row.get("Fit","") in ("SH STRONG", "SH MEDIUM", "SH LIGHT"):
        categories.append("INTIMATES>Shape & Control")
      #Camisoles & Chemises
      if l3 == "UW TOPS":
        categories.append("INTIMATES>Camisoles & Chemises")
      #Sleep & Lounge
      if l1 == "NW" or l1 == "HW":
        categories.append("INTIMATES>Sleep & Lounge")
      #Slippers
      if l1 == "FW":
        categories.append("INTIMATES>Slippers")

      #SWIMWEAR
      #All Swimwear
      if l1 == "SW" or l1 == "BW":
        categories.append("SWIMWEAR>All Swimwear")
      #1 Piece
      if l3 == "SW SWIMBODIES":
        categories.append("SWIMWEAR>1 Piece")
      #Bikinis
      if l3 == "SW BIKINI SETS":
        categories.append("SWIMWEAR>Bikinis")
      #D+ Cups
      if l1 == "SW" and any(letter in row.get("Cup","") for letter in "DEFGH"):
        categories.append("SWIMWEAR>D+ Cups")
      #Bikini Tops
      if l3 == "SW SWIMBRAS":
        categories.append("SWIMWEAR>Bikini Tops")
      #Bikini Bottoms
      if l3 == "SW SWIMBRIEFS":
        categories.append("SWIMWEAR>Bikini Bottoms")
      #Beachwear
      if l1 == "BW":
        categories.append("SWIMWEAR>Beachwear")
      #Sandals
      if l3 == "BW SANDALS":
        categories.append("SWIMWEAR>Sandals")


    #Men's Corner
    if gender == "M":
      #MEN'S CORNER
      #All Men's Corner
      if l1 in ("LW", "RW", "UW", "SW", "BW", "AC", "AW", "HW", "NW"):
        categories.append("MEN'S CORNER>All Men's Corner")
      #Underwear
      if l1 == "UW":
        categories.append("MEN'S CORNER>Underwear")
      #Socks
      if l3 == "LW SOCKS":
        categories.append("MEN'S CORNER>Socks")
      #Nightwear
      if l1 == "NW":
        categories.append("MEN'S CORNER>Nightwear")
      #Leisure
      if l1 == "HW":
        categories.append("MEN'S CORNER>Leisure")
      #Swim
      if l1 == "SW" or l1 == "BW":
        categories.append("MEN'S CORNER>Swim")
      #Accesories
      if l1 == "AC":
        categories.append("MEN'S CORNER>Accesories")


    #Brand Categorization
    if brand_name:
      categories.append(f"BRANDS>{brand_name}")

    #Is Living?
    if l1 == "LV":
      categories.append("LIVING>All Living")

    # #Join Categories with (,)
    # return ",".join(categories)        DEPRICATED

    # -------------------------------------------------------
    # 1)  Add every level-1 'general' category (CLOTHING, SWIMWEAR ...)
    #     that occurs to the list, if it's not there already.
    extra_parents = {c.split(">")[0].strip()               # take text before first '>'
                     for c in categories if ">" in c}      # only crumbs that had a child
    for parent in extra_parents:
        if parent and parent not in categories:
            categories.append(parent)

    # 2)  De-duplicate while preserving the order in which we appended
    categories = list(dict.fromkeys(categories))
    # -------------------------------------------------------

    # -- Normalize the config id_map and look up each crumb --
    bc_cfg = _cfg["categories"]
    id_map = bc_cfg.get("id_map", {})

    # build a normalized lookup dict once
    norm_map = { _normalize_crumb(k): v for k, v in id_map.items() }

    result = []
    for crumb in categories:
        key = _normalize_crumb(crumb)
        if key not in norm_map:
            raise KeyError(f"Category '{crumb}' (normalized to '{key}') not found in config.yaml id_map")
        result.append({"id": norm_map[key]})
    return result

# -------------------------
# basic-colour meta list
# -------------------------
def build_basic_color_meta(row):
    """
    Dynamically build basic_color meta: emit only the actual colours present,
    each with its mapped ID and descending weight, and finally a total count.
    """
    meta = []
    # only include entries for non-empty colours
    for idx, col in enumerate(["c_P1","c_P2","c_P3","c_P4","c_P5"]):
        raw = str(row.get(col, "")).strip()
        if not raw:
            continue
        mapped = _color_map.get(raw, "")
        # add the basic_color ID
        meta.append({
            "key":   f"basic_colors_{idx}_basic_color",
            "value": mapped
        })
        # add the corresponding weight (5 down to 1)
        meta.append({
            "key":   f"basic_colors_{idx}_percentage",
            "value": str(5 - idx)
        })
    # finally, the count of how many colours were present
    total = return_color_sum(row)
    meta.append({
        "key":   "basic_colors",
        "value": str(total)
    })
    return meta


def all_basic_colors(row):
    """
    Return the list of all non-empty c_P1–c_P5 values
    in the original order (P1 → P5) which implies weight.
    """
    vals = [row.get(col, "").strip() for col in ["c_P1","c_P2","c_P3","c_P4","c_P5"]]
    return [v for v in vals if v]


# -------------------------
# parent payload builder
# -------------------------
def build_parent_payload(group_rows):
  """
  Given all rows for a single parent (same style+color),
  return (parent_sku, parent_payload_dict) or (None, None) to skip.
  """
  first = group_rows[0]
  force_mode = os.getenv("FORCE_UPLOAD") == "1"

  # --- 1) Brand whitelist check ------------------------------------------
  if not force_mode:
    brand = str(first.get("Brand", "")).strip()
    if brand.lower() not in _allowed_brands:
        print(f"  ↳ SKIP parent '{concat_style_color(first)}': brand '{brand}' not allowed")
        return None, None

  # --- 2) Season code check ----------------------------------------------
  if not force_mode:
    l_sea = str(first.get("L_Sea", "")).strip()
    if l_sea not in recent_season_codes():
        print(f"  ↳ SKIP parent '{concat_style_color(first)}': season '{l_sea}' out of date")
        return None, None

  # --- Initialize payload and basic 1:1 field mappings -------------------
  parent = {"type": "variable"}
  for db_col, woo_key in _fmap.items():
      if woo_key.startswith("meta:"):
          continue
      parent[woo_key] = str(first.get(db_col, "")).strip()

  # --- SKU must exist before computed helpers ----------------------------
  parent_sku = concat_style_color(first)
  parent["sku"] = parent_sku

  # --- Dispatch computed fields (images, stock_quantity, etc.) -----------
  for field_name, helper_name in _computed_map.items():
      fn = globals().get(helper_name)
      if not fn:
          raise KeyError(f"Missing helper for computed field '{field_name}': '{helper_name}'")
      if field_name == "images":
          parent[field_name] = fn(first, parent_sku)
      else:
          parent[field_name] = fn(first)

  # --- Build global‐attribute payloads (so Woo shows pills) ---------------
  parent_attrs = []
  for attr_name, rule in _attr_rules.items():
      # Special‐case Size: collect from every row
      if rule["db_col"] == "b_Size":
          raw_sizes = [str(r.get("b_Size","")).strip() for r in group_rows if r.get("b_Size")]
          options = sort_sizes_naturally(raw_sizes)
      else:
          raw = str(first.get(rule["db_col"], "")).strip()
          if not raw:
              continue
          options = [o.strip() for o in raw.split(",") if o.strip()]

      parent_attrs.append({
          "id":        rule["id"],            # global attribute ID
          "name":      attr_name,
          "options":   options,
          "visible":   bool(rule["visible"]),
          "variation": bool(rule["variation"])
      })
  parent["attributes"] = parent_attrs

  # --- Build meta_data: 1-to-1 meta mappings + dynamic basic colors ------
  meta_list = []
  # 1) Any field_map entries starting with "meta:"
  for db_col, woo_key in _fmap.items():
      if woo_key.startswith("meta:"):
          meta_key = woo_key.split("meta:")[1]
          val = str(first.get(db_col, "")).strip()
          if val:
              meta_list.append({"key": meta_key, "value": val})

  # 2) Your dynamic basic-color metas (only non-empty ones)
  meta_list += build_basic_color_meta(first)
  parent["meta_data"] = meta_list

  return parent_sku, parent

# -------------------------
# child / variation builder
# -------------------------
def build_variation_payload(row, parent_sku, position):
  """
  Builds a single variation payload, including Size,
  stock, price, and any meta_data you want on each child.
  """
  # look up the attribute rule for Size so we can grab its global ID
  size_rule = _attr_rules["Size"]
  size_id   = size_rule["id"]
  size_opt  = str(row["b_Size"]).strip()

  payload = {
      "sku":            f"{parent_sku}-{size_opt}",
      "regular_price":  str(row["RP"]).strip(),
      "manage_stock":   True,
      "stock_quantity": calculate_safe_stock(row),
      "position":       position,
      # include the attribute ID so Woo doesn’t treat it as “Any Size”
      "attributes": [
          {
              "id":     size_id,         # global attribute ID for Size
              "name":   "Size",
              "option": size_opt
          }
      ],
      "meta_data": [
          { "key": "composition",       "value": str(row.get("Composition1","")).strip() },
          { "key": "care_instructions", "value": str(row.get("Care_Instr","")).strip() }
      ]
  }
  return payload

# -------------------------
# public API used by main.py
# -------------------------
def group_rows(rows):
  """rows: list[dict]  ->  dict[parent_key] = [rows]"""
  buckets = defaultdict(list)
  for r in rows:
      buckets[concat_style_color(r)].append(r)
  return buckets

def build_parent_and_children(rows):
  """Given list[dict] (same parent), return parentJSON, [childJSONs]"""
  parent = build_parent_payload(rows)
  if parent[0] is None:
      return None, []     # no parent, no children

  parent_sku, parent_json = parent

  sizes_sorted = sort_sizes_naturally([r["b_Size"] for r in rows])
  children_json = []
  for pos, size in enumerate(sizes_sorted, start=1):
      # pick the row that matches this size
      row = next(r for r in rows if r["b_Size"].strip() == size)
      variation_payload = build_variation_payload(row, parent_sku, pos)
      children_json.append((variation_payload, row["id"]))
  return parent_json, children_json
