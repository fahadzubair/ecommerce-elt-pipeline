import json
import os
from datetime import datetime

import boto3

BUCKET = os.environ["S3_RAW_BUCKET"]  # required; raises KeyError if not set


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
