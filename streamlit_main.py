import contextlib
import io
import logging
import os

import streamlit as st
from dotenv import load_dotenv
from snowflake.connector import connect

from dbt.cli.main import dbtRunner
from fetch_and_load import api_call, s3_uploader, s3_to_snowflake

load_dotenv()  # load AWS + Snowflake credentials from .env into os.environ

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
        account="CNSFQSU-VL97973",
        user="FAHADZUBAIR",
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        role="ACCOUNTADMIN",
        warehouse="ecomm_dw",
        database="ecomm_dw",
    )


def run_query(sql):
    cur = get_connection().cursor()
    try:
        cur.execute(sql)
        return cur.fetch_pandas_all()
    finally:
        cur.close()


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
# Data viewer
# ------------------------------------------------------------------
st.header("Data")

schema = st.selectbox("Layer", ["RAW", "CLEANSED", "CURATED"])

try:
    tables = run_query(
        "select table_name from ecomm_dw.information_schema.tables "
        f"where table_schema = '{schema}' order by table_name"
    )

    if tables.empty:
        st.info(f"No tables in {schema} yet - run the pipeline steps above first.")
    else:
        table = st.selectbox("Table", tables["TABLE_NAME"])
        st.caption(f"Showing up to 100 rows from ECOMM_DW.{schema}.{table}")
        st.dataframe(
            run_query(f"select * from ECOMM_DW.{schema}.{table} limit 100"),
            use_container_width=True,
        )
except Exception as e:
    st.error(f"Could not read from Snowflake: {e}")
