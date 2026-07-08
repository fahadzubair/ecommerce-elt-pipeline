import json
import os

import boto3
import pandas as pd
from snowflake.connector import connect
from snowflake.connector.pandas_tools import write_pandas

BUCKET = os.environ["S3_RAW_BUCKET"]  # required; raises KeyError if not set


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

    # Connect to Snowflake — all settings come from the .env / environment
    conn = connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
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