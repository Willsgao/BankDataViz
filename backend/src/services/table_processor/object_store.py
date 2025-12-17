# backend/services/table_processor/object_store.py
import os, gzip, json
from pathlib import Path

STORE_TYPE = os.getenv("OBJECT_STORE", "local")   # local | s3
BUCKET = os.getenv("OBJECT_STORE_BUCKET", "")
LOCAL_ROOT = Path(os.getenv("LOCAL_OBJECT_STORE", "obj_cache"))
LOCAL_ROOT.mkdir(exist_ok=True)

def _local_path(key: str) -> Path:
    return LOCAL_ROOT / key

def put_object(key: str, body: bytes):
    if STORE_TYPE == "local":
        _local_path(key).parent.mkdir(parents=True, exist_ok=True)
        _local_path(key).write_bytes(body)
    else:  # s3
        import boto3
        boto3.client('s3').put_object(Bucket=BUCKET, Key=key, Body=body)

def get_object(key: str) -> bytes:
    if STORE_TYPE == "local":
        return _local_path(key).read_bytes()
    else:
        import boto3
        return boto3.client('s3').get_object(Bucket=BUCKET, Key=key)["Body"].read()