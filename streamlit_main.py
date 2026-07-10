import contextlib
import io
import logging
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from snowflake.connector import connect

from dbt.cli.main import dbtRunner

load_dotenv()  # must run BEFORE the fetch_and_load import (those modules read env at import time)

from fetch_and_load import api_call, s3_uploader, s3_to_snowflake  # noqa: E402

# Worker threads (dbt / snowflake) print while stdout is redirected to the UI,
# which makes Streamlit warn "missing ScriptRunContext". Silence that logger...
logging.getLogger(
    "streamlit.runtime.scriptrunner_utils.script_run_context"
).setLevel(logging.ERROR)

# ...and only touch the UI from a thread that actually owns the Streamlit context.
try:
    from streamlit.runtime.scriptrunner import get_script_run_ctx
except Exception:  # pragma: no cover - import path can differ across versions
    def get_script_run_ctx():
        return object()  # assume a context exists if we cannot check

st.set_page_config(page_title="Ecommerce ELT", layout="wide")

# Trim the default top padding, and make the log code block a black "terminal"
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; }
    [data-testid="stCode"] pre, .stCode pre { background-color: #000 !important; }
    [data-testid="stCode"] pre,
    [data-testid="stCode"] code,
    [data-testid="stCode"] span { color: #e6e6e6 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛒 Ecommerce ELT Pipeline")


# --- Snowflake connection (opened once, reused) ---
@st.cache_resource
def get_connection():
    return connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
    )


def run_query(sql):
    cur = get_connection().cursor()
    try:
        cur.execute(sql)
        return cur.fetch_pandas_all()
    finally:
        cur.close()


@st.cache_data(ttl=300)
def load_df(sql):
    """Cached query loader so metric charts don't re-hit Snowflake on every rerun."""
    return run_query(sql)


def load_curated(sql, columns):
    """Run a curated query; return an empty DataFrame(columns) when the data isn't there
    yet (schema/table missing or nothing loaded) so charts render empty instead of erroring."""
    try:
        df = load_df(sql)
    except Exception:  # noqa: BLE001 - missing schema/table => treat as no data
        return pd.DataFrame(columns=columns)
    return df if not df.empty else pd.DataFrame(columns=columns)


LOG_HEIGHT = 180  # px height of the scrollable log box


class LiveLog(io.StringIO):
    """A stdout replacement that live-updates a fixed-height, scrollable log box."""

    def __init__(self, placeholder):
        super().__init__()
        self._placeholder = placeholder

    def write(self, text):
        n = super().write(text)
        # Only update the UI from a thread that owns the Streamlit context.
        # Worker-thread writes are still captured, just not rendered from here.
        if get_script_run_ctx() is not None:
            box = self._placeholder.container(height=LOG_HEIGHT)
            box.markdown("**📋 Logs**")  # heading inside the scrollable box
            box.code(self.getvalue().strip() or "...", language="text")
        return n


def run_step(label, fn, placeholder):
    """Run fn(), streaming its printed output live into the given (full-width) placeholder."""
    live = LiveLog(placeholder)
    error = None
    result = None
    with st.spinner(f"{label}..."):
        with contextlib.redirect_stdout(live), contextlib.redirect_stderr(live):
            try:
                result = fn()
            except Exception as e:  # noqa: BLE001 - surface any failure to the user
                print(f"\nERROR: {e}")  # flows into the live log too
                error = e

    if error is not None:
        st.error(f"{label} failed: {error}")
    return result, error


# ------------------------------------------------------------------
# Pipeline controls
# ------------------------------------------------------------------
st.header("Pipeline")


def fetch_and_upload():
    datasets = api_call.api_caller()
    s3_uploader.upload_to_s3(datasets)


c1, c2, c3 = st.columns(3)
clicked_fetch = c1.button("1. Fetch API to S3", use_container_width=True)
clicked_load = c2.button("2. Load S3 to Snowflake (RAW)", use_container_width=True)
clicked_dbt = c3.button("3. Run dbt (CLEANSED + CURATED)", use_container_width=True)

# Full-width log area, created outside the columns so it spans the whole page
log_area = st.empty()

if clicked_fetch:
    _, error = run_step("Fetching from API and uploading to S3", fetch_and_upload, log_area)
    if error is None:
        st.success("Fetched and uploaded to S3")

elif clicked_load:
    _, error = run_step("Loading latest S3 files into Snowflake raw", s3_to_snowflake.put, log_area)
    if error is None:
        st.success("Loaded into Snowflake raw")

elif clicked_dbt:
    result, error = run_step(
        "Running dbt",
        lambda: dbtRunner().invoke(["run", "--project-dir", "dbt_ecomm"]),
        log_area,
    )
    if error is None:
        if result is not None and result.success:
            st.success("dbt run succeeded")
        else:
            st.error("dbt run failed - see messages above / terminal")


# ------------------------------------------------------------------
# Metrics (curated data)
# ------------------------------------------------------------------
st.header("📊 Metrics")

# Database name comes from the environment (same var the connection uses)
DATABASE = os.environ["SNOWFLAKE_DATABASE"]
CURATED = f"{DATABASE}.CURATED"

# --- KPI row: one aggregate scan over the fact table ---
kpis = load_curated(
    f"""
    select
        sum(net_amount)            as revenue,
        count(distinct order_id)   as orders,
        sum(quantity)              as units,
        avg(net_amount)            as avg_line
    from {CURATED}.FCT_ORDERS
    """,
    ["REVENUE", "ORDERS", "UNITS", "AVG_LINE"],
)

# When the table exists but is empty, the aggregate returns one row of NULLs.
has_data = not kpis.empty and kpis["REVENUE"].iloc[0] is not None
if not has_data:
    st.caption("No curated data yet - run the pipeline steps above to populate these charts.")

revenue = float(kpis["REVENUE"].iloc[0]) if has_data else 0.0
orders = int(kpis["ORDERS"].iloc[0]) if has_data else 0
units = int(kpis["UNITS"].iloc[0]) if has_data else 0
aov = revenue / orders if orders else 0.0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"${revenue:,.0f}")
k2.metric("Total Orders", f"{orders:,}")
k3.metric("Units Sold", f"{units:,}")
k4.metric("Avg Order Value", f"${aov:,.2f}")

# --- Charts: 2x2 grid (render empty frames when there is no data) ---
r1c1, r1c2 = st.columns(2)

with r1c1:
    st.subheader("Revenue over time")
    trend = load_curated(
        f"""
        select
            date_trunc('month', order_date) as month,
            sum(net_amount)                 as revenue
        from {CURATED}.FCT_ORDERS
        where order_date is not null
        group by 1
        order by 1
        """,
        ["MONTH", "REVENUE"],
    )
    st.line_chart(trend, x="MONTH", y="REVENUE")

with r1c2:
    st.subheader("Revenue by category")
    by_cat = load_curated(
        f"""
        select
            c.category_name  as category_name,
            sum(f.net_amount) as revenue
        from {CURATED}.FCT_ORDERS f
        join {CURATED}.DIM_PRODUCTS p   on f.product_id = p.product_id
        join {CURATED}.DIM_CATEGORIES c on p.category_id = c.category_id
        group by 1
        order by revenue desc
        """,
        ["CATEGORY_NAME", "REVENUE"],
    )
    st.bar_chart(by_cat, x="CATEGORY_NAME", y="REVENUE")

r2c1, r2c2 = st.columns(2)

with r2c1:
    st.subheader("Top 10 products by revenue")
    top_prod = load_curated(
        f"""
        select
            p.product_name   as product_name,
            sum(f.net_amount) as revenue
        from {CURATED}.FCT_ORDERS f
        join {CURATED}.DIM_PRODUCTS p on f.product_id = p.product_id
        group by 1
        order by revenue desc
        limit 10
        """,
        ["PRODUCT_NAME", "REVENUE"],
    )
    st.bar_chart(top_prod, x="PRODUCT_NAME", y="REVENUE", horizontal=True)

with r2c2:
    st.subheader("Top 10 customers by revenue")
    top_cust = load_curated(
        f"""
        select
            cu.company_name  as company_name,
            sum(f.net_amount) as revenue
        from {CURATED}.FCT_ORDERS f
        join {CURATED}.DIM_CUSTOMERS cu on f.customer_id = cu.customer_id
        group by 1
        order by revenue desc
        limit 10
        """,
        ["COMPANY_NAME", "REVENUE"],
    )
    st.bar_chart(top_cust, x="COMPANY_NAME", y="REVENUE", horizontal=True)


# ------------------------------------------------------------------
# Data viewer
# ------------------------------------------------------------------
st.header("Data")

schema = st.selectbox("Layer", ["RAW", "CLEANSED", "CURATED"])

# Database name comes from the environment (same var the connection uses)
DATABASE = os.environ["SNOWFLAKE_DATABASE"]

try:
    tables = run_query(
        f"select table_name from {DATABASE}.information_schema.tables "
        f"where table_schema = '{schema}' order by table_name"
    )

    if tables.empty:
        st.info(f"No tables in {schema} yet - run the pipeline steps above first.")
    else:
        table = st.selectbox("Table", tables["TABLE_NAME"])
        st.caption(f"Showing up to 100 rows from {DATABASE.upper()}.{schema}.{table}")
        st.dataframe(
            run_query(f"select * from {DATABASE}.{schema}.{table} limit 100"),
            use_container_width=True,
        )
except Exception as e:
    st.error(f"Could not read from Snowflake: {e}")
