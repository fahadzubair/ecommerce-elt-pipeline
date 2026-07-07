# MASTERPLAN — Ecommerce ELT Pipeline

> A complete blueprint to reproduce this project **exactly** and to onboard a new
> developer. It documents every folder, file, line of code, naming rule,
> commenting style, external service setup, and run command.
>
> Last updated: 2026-07-07

---

## 1. What this project is

An end-to-end **ELT** (Extract → Load → Transform) pipeline for the public
**Northwind** ecommerce dataset, with a small **Streamlit** control panel.

**Data flow:**

```
Northwind OData API                (10 REST endpoints, JSON)
      │  extract (requests)
      ▼
AWS S3  s3://<bucket>/<timestamp>/data/<table>.json   (raw JSON, partitioned by run)
      │  load (boto3 + pandas + snowflake write_pandas)
      ▼
Snowflake  ECOMM_DW.RAW.<TABLE>     (one table per entity, full-refresh each run)
      │  transform (dbt)
      ▼
Snowflake  ECOMM_DW.CLEANSED.<TABLE>   (renamed, typed, trimmed — 1:1 with raw)
      │  transform (dbt)
      ▼
Snowflake  ECOMM_DW.CURATED.DIM_* / FCT_ORDERS   (star schema)
```

Two entry points:
- **`main.py`** — headless CLI that runs the whole pipeline top to bottom.
- **`streamlit_main.py`** — a browser UI with 3 buttons (fetch→S3, load→Snowflake, run dbt) plus a data viewer, streaming live logs.

---

## 2. Tech stack & exact versions

Python **3.14** (venv named `elt_venv`). Pinned in `requirements.txt`:

```
boto3==1.43.40
dbt-snowflake==1.11.6
pandas==2.3.3
python-dotenv==1.2.2
requests==2.34.2
snowflake-connector-python[pandas]==4.6.0
streamlit==1.58.0
```

`dbt-core` (1.12.0b3), `pyarrow`, and `numpy` are installed transitively — do **not** pin them.

---

## 3. External infrastructure (must exist before running)

### 3.1 AWS S3
- An S3 bucket for raw landing, e.g. `de-ecommerce-raw-data-123456789`.
- An IAM user/key with `s3:PutObject`, `s3:GetObject`, `s3:ListBucket` on that bucket.
- Region: `us-east-1` (adjust as needed).

### 3.2 Snowflake
Objects (created once as `ACCOUNTADMIN`):
```sql
CREATE DATABASE  ECOMM_DW;
CREATE WAREHOUSE ECOMM_DW WITH WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60;
CREATE SCHEMA    ECOMM_DW.RAW;
-- CLEANSED and CURATED schemas are created automatically by dbt on first run.
```
- Account identifier format: **`<ORG>-<ACCOUNT>`** e.g. `CNSFQSU-VL97973`
  (NOT the full `https://....snowflakecomputing.com` URL, and **no dots/slashes/hyphens‑as‑URL**).
- User: `FAHADZUBAIR`, Role: `ACCOUNTADMIN`.
- **All Snowflake object names use underscores, never hyphens** (`ecomm_dw`, not `ecomm-dw`).

> ⚠️ **Secrets**: the AWS keys and Snowflake password live only in `.env` (git-ignored).
> The Snowflake **account** and **user** are currently hardcoded in the Python
> connect() calls — replace them with your own when reproducing.

---

## 4. Folder structure (exact)

```
ecommerce-elt-pipeline/
├── .env                          # secrets + config (NOT committed)
├── requirements.txt
├── MASTERPLAN.md                 # this file
├── main.py                       # CLI orchestrator (headless run)
├── streamlit_main.py             # Streamlit UI
├── elt_venv/                     # Python 3.14 virtualenv (not committed)
│
├── fetch_and_load/               # extraction + load package (plain modules, no __init__.py)
│   ├── api_call.py               # API  -> in-memory datasets
│   ├── s3_uploader.py            # datasets -> S3 (timestamped JSON)
│   └── s3_to_snowflake.py        # latest S3 files -> Snowflake RAW
│
├── downloads/                    # local CSV samples (dev artifact; optional)
│   ├── categories.csv ... territories.csv   (10 files)
│
└── dbt_ecomm/                    # dbt project (profile name: dbt_ecomm)
    ├── dbt_project.yml
    ├── README.md                 # default dbt README
    ├── .gitignore                # default dbt gitignore (target/, dbt_packages/, logs/)
    ├── analyses/.gitkeep
    ├── seeds/.gitkeep
    ├── snapshots/.gitkeep
    ├── tests/.gitkeep
    ├── macros/
    │   ├── .gitkeep
    │   └── generate_schema_name.sql       # schema-naming override
    └── models/
        ├── cleansed/
        │   ├── sources.yml                # declares the RAW source
        │   ├── CATEGORIES.sql
        │   ├── CUSTOMERS.sql
        │   ├── EMPLOYEES.sql
        │   ├── ORDERS.sql
        │   ├── ORDER_DETAILS.sql
        │   ├── PRODUCTS.sql
        │   ├── REGIONS.sql
        │   ├── SHIPPERS.sql
        │   ├── SUPPLIERS.sql
        │   └── TERRITORIES.sql
        └── curated/
            ├── sources.yml                # declares the CLEANSED source (legacy; models use ref())
            ├── DIM_CATEGORIES.sql
            ├── DIM_CUSTOMERS.sql
            ├── DIM_EMPLOYEES.sql
            ├── DIM_PRODUCTS.sql
            ├── DIM_REGIONS.sql
            ├── DIM_SHIPPERS.sql
            ├── DIM_SUPPLIERS.sql
            ├── DIM_TERRITORIES.sql
            └── FCT_ORDERS.sql
```

Note the `~/.dbt/profiles.yml` file (outside the repo) — see §7.

---

## 5. Environment setup (from zero)

```bash
# 1. Create the virtualenv (named exactly elt_venv)
python3 -m venv elt_venv

# 2. Install dependencies
./elt_venv/bin/pip install -r requirements.txt

# 3. Create the .env file (see §6), then it is loaded either by
#    `source .env` (for CLI) or automatically by load_dotenv() (in the app).
```

---

## 6. `.env` (project root, git-ignored)

Uses `export` syntax so it works both with `source .env` (shell) and
`python-dotenv` (which strips the `export`). Structure:

```bash
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_DEFAULT_REGION=us-east-1
export S3_RAW_BUCKET=de-ecommerce-raw-data-123456789
export S3_RAW_PREFIX=raw

export SNOWFLAKE_PASSWORD=<your-snowflake-password>
```

- `AWS_*` — picked up automatically by boto3.
- `S3_RAW_BUCKET` — read via `os.getenv("S3_RAW_BUCKET")` in the loaders.
- `SNOWFLAKE_PASSWORD` — read via `os.getenv("SNOWFLAKE_PASSWORD")`.
- **Add `.env` to `.gitignore`.** There is currently no repo-root `.gitignore` — create one containing at least `.env`, `elt_venv/`, `__pycache__/`, `downloads/`.

---

## 7. dbt profile — `~/.dbt/profiles.yml`

The dbt project uses `profile: 'dbt_ecomm'`. That profile must exist in the
**user home** `~/.dbt/profiles.yml` (created by `dbt init`, then edited):

```yaml
dbt_ecomm:
  outputs:
    dev:
      type: snowflake
      account: CNSFQSU-VL97973        # <ORG>-<ACCOUNT>, no URL, no dots
      user: FAHADZUBAIR
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"   # recommended over plaintext
      role: ACCOUNTADMIN
      database: ecomm_dw              # underscores only
      warehouse: ecomm_dw
      schema: raw                     # the default/fallback target schema
      threads: 1
  target: dev
```

Validate with:
```bash
cd dbt_ecomm
dbt debug        # expect: Connection test: [OK]
```

**Gotchas learned (all cause SQL compilation errors):**
- Account must be `CNSFQSU-VL97973`, not the `https://...snowflakecomputing.com` URL.
- Database/warehouse must be `ecomm_dw` (underscore), never `ecomm-dw` (hyphen).

---

## 8. The extraction/load package — `fetch_and_load/`

Plain modules imported as `from fetch_and_load import api_call, s3_uploader, s3_to_snowflake`.
(No `__init__.py`; Python 3 namespace packages make this work when run from the repo root.)

### 8.1 `fetch_and_load/api_call.py`
Fetches all 10 Northwind OData endpoints and returns `{table_name: parsed_json}` — **no local files**.

```python
import requests

API_ENDPOINTS = [
    "https://services.odata.org/v4/northwind/northwind.svc/Customers",
    "https://services.odata.org/v4/northwind/northwind.svc/Orders",
    "https://services.odata.org/v4/northwind/northwind.svc/Order_Details",
    "https://services.odata.org/v4/northwind/northwind.svc/Products",
    "https://services.odata.org/v4/northwind/northwind.svc/Categories",
    "https://services.odata.org/v4/northwind/northwind.svc/Suppliers",
    "https://services.odata.org/v4/northwind/northwind.svc/Employees",
    "https://services.odata.org/v4/northwind/northwind.svc/Shippers",
    "https://services.odata.org/v4/northwind/northwind.svc/Regions",
    "https://services.odata.org/v4/northwind/northwind.svc/Territories",
]


def api_caller():
    """Fetch every endpoint and return {table_name: parsed_json}. No local files."""
    datasets = {}

    for endpoint in API_ENDPOINTS:

        # GET request
        response = requests.get(endpoint)
        data = response.json()

        name = endpoint.split('/')[-1].lower()
        datasets[name] = data

        print(f"Fetched {len(data.get('value', []))} rows from {name} endpoint")

    return datasets
```

Key detail: OData wraps records under a **`value`** key. Table name = last URL
segment, lowercased (`Order_Details` → `order_details`).

### 8.2 `fetch_and_load/s3_uploader.py`
Serializes each dataset in memory and `put_object`s it to S3 under a per-run
timestamp prefix. Bucket comes from the `S3_RAW_BUCKET` env var.

```python
import json
import os
from datetime import datetime

import boto3

BUCKET = os.getenv("S3_RAW_BUCKET")  # reads the S3_RAW_BUCKET environment variable


def upload_to_s3(datasets):
    """Upload each in-memory dataset directly to S3 as JSON — nothing touches disk."""
    # Credentials are picked up automatically from the file / env vars above
    s3 = boto3.client("s3")

    # Build a folder name from the current timestamp, e.g. "2026-07-03_15-52-00"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Serialize each dataset in memory and push the bytes straight to S3.
    # S3 creates the folders automatically from the key prefix.
    for name, data in datasets.items():
        body = json.dumps(data, indent=4).encode("utf-8")
        key = f"{timestamp}/data/{name}.json"
        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        print(f"Uploaded {name}.json -> s3://{BUCKET}/{key}")

    print(f"\nDone. All files are under s3://{BUCKET}/{timestamp}/data/")
```

Key detail: S3 key layout is `<YYYY-MM-DD_HH-MM-SS>/data/<name>.json`. The
timestamp format uses **dashes/underscores only** (colons break tooling) and
sorts chronologically as text.

### 8.3 `fetch_and_load/s3_to_snowflake.py`
Finds the **latest** timestamp folder, reads each JSON from S3 into memory, and
bulk-loads it into `ECOMM_DW.RAW.<TABLE>` via `write_pandas`.

```python
import json
import os

import boto3
import pandas as pd
from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas

BUCKET = os.getenv("S3_RAW_BUCKET")


def put():
    s3 = boto3.client("s3")

    # Every key looks like  <timestamp>/data/<file>.json
    s3_objects = s3.list_objects_v2(Bucket=BUCKET)["Contents"]
    keys = []

    for obj in s3_objects:
        key = obj["Key"]
        if key.endswith(".json"):
            keys.append(key)


    # Latest timestamp = the biggest folder name (they sort chronologically).
    # Sort the keys, so the last one belongs to the latest timestamp folder.
    keys.sort(reverse=True)
    latest_keys = keys[:10]

    # Connect to Snowflake (password comes from the SNOWFLAKE_PASSWORD env var)
    conn = connect(
        account="CNSFQSU-VL97973",
        user="FAHADZUBAIR",
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role="ACCOUNTADMIN",
        warehouse="ecomm_dw",
        database="ecomm_dw",
        schema="raw",
    )

    # Load each JSON file into its own table in ecomm_dw.raw
    for key in latest_keys:
        # Read the JSON object straight from S3 into memory
        body = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        rows = json.loads(body)["value"]  # OData puts the records under "value"

        if not rows:
            print("Skipped (empty):", key)
            continue

        # e.g. "customers.json" -> table CUSTOMERS
        table = os.path.basename(key).replace(".json", "").upper()
        df = pd.DataFrame(rows)

        # Drop OData metadata columns like "@odata.etag" — they aren't real data
        # and "@"/"." are illegal in an unquoted Snowflake identifier.
        df = df.loc[:, ~df.columns.str.startswith("@")]

        # Creates the table if needed and replaces its contents each run
        write_pandas(
            conn,
            df,
            table_name=table,
            auto_create_table=True,
            overwrite=True,
            quote_identifiers=False,
        )
        print(f"Loaded {len(df)} rows into ECOMM_DW.RAW.{table}")

    conn.close()
```

Critical details:
- **Drop `@odata.*` columns** — `@` and `.` are illegal in unquoted Snowflake
  identifiers and cause `syntax error ... unexpected '@odata.etag'`.
- `write_pandas(..., quote_identifiers=False)` stores columns as **unquoted
  UPPERCASE**, so dbt can reference them without case-sensitivity pain.
- `auto_create_table=True, overwrite=True` → full-refresh of each raw table.
- `latest_keys = keys[:10]` assumes exactly 10 tables per run.

---

## 9. Orchestration entry points

### 9.1 `main.py` (CLI, headless)
```python
from fetch_and_load import api_call
from fetch_and_load import s3_uploader
from fetch_and_load import s3_to_snowflake
from dbt.cli.main import dbtRunner

# Call API — returns the fetched datasets in memory (no local files)
datasets = api_call.api_caller()

# Push the in-memory datasets straight to S3
s3_uploader.upload_to_s3(datasets)

# Run S3_to_Snowflake file.
s3_to_snowflake.put()

dbtRunner().invoke(["run", "--project-dir", "dbt_ecomm"])
```
Run with:
```bash
source .env
./elt_venv/bin/python main.py
```

### 9.2 `streamlit_main.py` (UI)
A Streamlit app with:
- CSS to trim top padding and render the log block as a **black terminal**.
- A cached Snowflake connection (`@st.cache_resource`) + `run_query()` helper
  returning a pandas DataFrame via `cursor.fetch_pandas_all()`.
- A `LiveLog(io.StringIO)` class that redirects `stdout`/`stderr` and live-updates
  a fixed-height (`LOG_HEIGHT = 150`) scrollable container with a **📋 Logs**
  heading inside it. It only touches the UI when `get_script_run_ctx()` is not
  None (prevents "missing ScriptRunContext" warnings from dbt/snowflake worker
  threads), and that logger is also silenced.
- Three buttons in `st.columns(3)` whose click flags are handled *below* the
  columns so the full-width log area spans the page: Fetch API→S3, Load
  S3→Snowflake (raw), Run dbt.
- A data viewer: `st.selectbox` for layer (RAW/CLEANSED/CURATED) → tables listed
  from `ecomm_dw.information_schema.tables` → `st.dataframe` of up to 100 rows
  from `ECOMM_DW.<schema>.<table>`.

Run with:
```bash
./elt_venv/bin/streamlit run streamlit_main.py     # opens http://localhost:8501
```
(dbt logs still print to the launching terminal, not the browser.)

---

## 10. dbt project — `dbt_ecomm/`

### 10.1 `dbt_project.yml` (models section)
```yaml
name: 'dbt_ecomm'
version: '1.0.0'
profile: 'dbt_ecomm'
model-paths: ["models"]
# ... default paths ...
models:
  dbt_ecomm:
    cleansed:
      +materialized: table
      +schema: cleansed
    curated:
      +materialized: table
      +schema: curated
```

### 10.2 `macros/generate_schema_name.sql` — REQUIRED
Without this, dbt names schemas `<target>_<custom>` → `raw_cleansed`,
`raw_curated`. This override makes `+schema: cleansed` produce exactly
`CLEANSED`:
```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
```

### 10.3 Sources
- `models/cleansed/sources.yml` declares source **`raw`** → `ecomm_dw.raw.<table>`
  (10 tables, lowercase names). Cleansed models read from `{{ source('raw', '<t>') }}`.
- `models/curated/sources.yml` declares source **`cleansed`** → `ecomm_dw.cleansed.<table>`.
  (Legacy: curated models actually use `ref()` to the cleansed models, so this
  file is not strictly required. Kept for reference.)

### 10.4 Cleansed layer (10 models, `models/cleansed/`)
Each is a **minimal, basic** raw→cleansed transform: rename to snake_case,
cast ids/dates/numerics, `trim()` text, drop binary blobs (`Picture`, `Photo`).
Model name = filename (UPPERCASE). Reads from `source('raw', <lowercase>)`.

Example — `EMPLOYEES.sql`:
```sql
-- Cleansed Employees: type-cast ids/dates, trim text, drop the photo blob
with source as (

    select * from {{ source('raw', 'employees') }}

)

select
    cast(employeeid as integer) as employee_id,
    trim(lastname)              as last_name,
    trim(firstname)             as first_name,
    trim(title)                 as title,
    trim(titleofcourtesy)       as title_of_courtesy,
    cast(birthdate as date)     as birth_date,
    cast(hiredate as date)      as hire_date,
    trim(address)               as address,
    trim(city)                  as city,
    trim(region)                as region,
    trim(postalcode)            as postal_code,
    trim(country)               as country,
    trim(homephone)             as home_phone,
    trim(extension)             as extension,
    trim(notes)                 as notes,
    cast(reportsto as integer)  as reports_to
    -- "photo" column dropped: base64 image blob, not useful downstream
from source
```

Per-table cleansed output columns:
| Model | Output columns (snake_case) | Notes |
|---|---|---|
| CATEGORIES | category_id, category_name, description | drops `picture` blob |
| CUSTOMERS | customer_id, company_name, contact_name, contact_title, address, city, region, postal_code, country, phone, fax | `customer_id` kept as text |
| EMPLOYEES | employee_id, last_name, first_name, title, title_of_courtesy, birth_date, hire_date, address, city, region, postal_code, country, home_phone, extension, notes, reports_to | drops `photo` blob |
| ORDER_DETAILS | order_id, product_id, unit_price, quantity, discount | prices `number(10,2)` |
| ORDERS | order_id, customer_id, employee_id, order_date, required_date, shipped_date, ship_via, freight, ship_name, ship_address, ship_city, ship_region, ship_postal_code, ship_country | dates cast to `date` |
| PRODUCTS | product_id, product_name, supplier_id, category_id, quantity_per_unit, unit_price, units_in_stock, units_on_order, reorder_level, is_discontinued | `is_discontinued` boolean |
| REGIONS | region_id, region_description | trim (trailing spaces) |
| SHIPPERS | shipper_id, company_name, phone | |
| SUPPLIERS | supplier_id, company_name, contact_name, contact_title, address, city, region, postal_code, country, phone, fax, home_page | |
| TERRITORIES | territory_id, territory_description, region_id | `territory_id` kept as text |

### 10.5 Curated layer (star schema, `models/curated/`)
8 pass-through **dimensions** + 1 **fact**. Dimensions `ref()` the cleansed model
and select columns straight through (no complex transforms). Model name = filename.

Example — `DIM_CUSTOMERS.sql`:
```sql
-- DIM_CUSTOMERS: customer dimension built on the cleansed customers model
with customers as (

    select * from {{ ref('CUSTOMERS') }}

)

select
    customer_id, company_name, contact_name, contact_title,
    address, city, region, postal_code, country, phone, fax
from customers
```

The fact — `FCT_ORDERS.sql` — order-line grain, joins ORDER_DETAILS→ORDERS:
```sql
-- FCT_ORDERS: sales fact at the order-line grain (one row per order + product).
-- Joins order details to their parent order for the dimension keys and dates.
with order_details as (
    select * from {{ ref('ORDER_DETAILS') }}
),
orders as (
    select * from {{ ref('ORDERS') }}
)
select
    -- dimension keys
    od.order_id, od.product_id, o.customer_id, o.employee_id,
    o.ship_via as shipper_id,
    -- order dates
    o.order_date, o.required_date, o.shipped_date,
    -- measures
    od.unit_price, od.quantity, od.discount,
    (od.unit_price * od.quantity * (1 - od.discount)) as net_amount
from order_details od
left join orders o
    on od.order_id = o.order_id
```

Star schema wiring: `FCT_ORDERS` → DIM_CUSTOMERS (customer_id), DIM_EMPLOYEES
(employee_id), DIM_PRODUCTS (product_id), DIM_SHIPPERS (shipper_id).
DIM_PRODUCTS → DIM_CATEGORIES / DIM_SUPPLIERS. DIM_TERRITORIES → DIM_REGIONS.

---

## 11. Conventions & style (follow these when adding code)

### Python
- **Import order**: stdlib, blank line, third-party, blank line, local (`fetch_and_load`, `dbt`). No `__init__.py`.
- **Env/config** read at module top: `BUCKET = os.getenv("S3_RAW_BUCKET")`.
- **Functions have a one-line docstring**, often with an em-dash aside, e.g.
  `"""Upload each in-memory dataset directly to S3 as JSON — nothing touches disk."""`.
- **Inline comments explain *why***, placed on their own line above the code, sentence case.
- **f-strings** for all printed messages; DB/schema names printed **UPPERCASE**
  (`ECOMM_DW.RAW.{table}`).
- Snowflake connect args always in this order: account, user, password, role, warehouse, database, schema.

### SQL (dbt models)
- **Filename = model name in UPPERCASE** (`CUSTOMERS.sql`, `DIM_CUSTOMERS.sql`, `FCT_ORDERS.sql`).
- **First line is a comment header**: `-- <ModelName>: <one-line purpose>`.
- Lead with a CTE named after the source (`source`, `customers`, `orders`, `order_details`), blank lines padding the CTE body.
- `select` lists **column aliases aligned** with `as`, snake_case output names.
- Inline `--` comments to justify drops/casts (e.g. dropping blob columns).
- Cleansed models read via `{{ source('raw', '<lower>') }}`; curated via `{{ ref('<CLEANSED_MODEL>') }}`.
- Keep transforms minimal: rename, cast, trim, drop blobs. No business logic beyond `FCT_ORDERS.net_amount`.

### YAML
- `version: 2` header; sources have `name`, `description`, `database`, `schema`, and a `tables:` list of lowercase `name`s.

### Schemas / naming
- Snowflake identifiers: **underscores only**, unquoted, resolve as UPPERCASE.
- Layers map 1:1 to schemas: `RAW` → `CLEANSED` → `CURATED`.

---

## 12. Run order (full pipeline)

```bash
# one-time
python3 -m venv elt_venv
./elt_venv/bin/pip install -r requirements.txt
# create .env (§6) and ~/.dbt/profiles.yml (§7)
# create Snowflake DB/WH/RAW schema (§3.2)

# every run — option A: headless
source .env
./elt_venv/bin/python main.py

# every run — option B: UI
./elt_venv/bin/streamlit run streamlit_main.py
#   click 1 → 2 → 3 in order

# dbt only
cd dbt_ecomm
dbt debug            # verify connection
dbt run              # build all models (cleansed + curated)
dbt run --select cleansed        # one layer
dbt run --select +DIM_CUSTOMERS  # a model and its upstreams
```

---

## 13. Gotchas / lessons (things that already bit us)

1. **Account identifier**: use `CNSFQSU-VL97973`, never the full `https://...snowflakecomputing.com` URL (error `251001 Invalid account identifier`).
2. **Hyphen vs underscore**: `ecomm-dw` fails (`syntax error ... unexpected '-'`); use `ecomm_dw` everywhere.
3. **`@odata.*` columns** must be dropped before loading (illegal unquoted identifiers).
4. **Schema prefixing**: dbt appends target schema by default (`raw_cleansed`). The `generate_schema_name` macro fixes it to a clean `CLEANSED`/`CURATED`.
5. **dbt selection**: `dbt run --select CATEGORIES`, not `dbt run model categories`.
6. **Streamlit**: launch with `streamlit run`, not `python`; `st.code` background is themed → override with CSS + `!important`; worker-thread `st` calls warn about `ScriptRunContext` → guard with `get_script_run_ctx()`.
7. **`write_pandas` needs `pyarrow`** — comes via `snowflake-connector-python[pandas]`.

---

## 14. Knowledge-transfer quick start (new dev, 15 min)

1. Read §1 (data flow) and §4 (structure).
2. Get AWS keys + Snowflake creds from the team; put them in `.env` and `~/.dbt/profiles.yml`.
3. `python3 -m venv elt_venv && ./elt_venv/bin/pip install -r requirements.txt`.
4. `cd dbt_ecomm && dbt debug` → must say `[OK]`.
5. Run the UI (`streamlit run streamlit_main.py`), click buttons 1→2→3, watch the logs.
6. Open the data viewer, inspect RAW → CLEANSED → CURATED.
7. To change a transform: edit the matching `models/cleansed/<TABLE>.sql`, `dbt run --select <TABLE>+`.

---

## 15. Ideas / not yet done
- Add dbt tests (`unique`, `not_null`) and a `schema.yml` for models.
- Move hardcoded Snowflake `account`/`user` into env vars.
- Add a repo-root `.gitignore` (`.env`, `elt_venv/`, `__pycache__/`, `downloads/`).
- Incremental raw loads / Snowpipe instead of full-refresh.
- Auto-scroll the Streamlit live log to the newest line.
```
