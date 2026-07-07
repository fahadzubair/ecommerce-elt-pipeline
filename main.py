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
