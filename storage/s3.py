import os
import boto3

_s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com",
    aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
)


def upload_file(file_path: str, key: str) -> str:
    bucket = os.getenv("R2_BUCKET_NAME")
    _s3.upload_file(file_path, bucket, key)
    return f"https://{bucket}.{os.getenv('R2_ACCOUNT_ID')}.r2.cloudflarestorage.com/{key}"
