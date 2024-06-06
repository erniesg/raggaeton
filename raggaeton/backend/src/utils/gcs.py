import os
import logging
from google.cloud import storage
from raggaeton.backend.src.utils.common import config_loader, base_dir

logger = logging.getLogger(__name__)


def get_gcs_client():
    return storage.Client()


def get_bucket(bucket_name):
    client = get_gcs_client()
    return client.bucket(bucket_name)


def save_data(local_path, bucket_name=None, gcs_path=None):
    config = config_loader.get_config()
    bucket_name = bucket_name or config["gcs"]["bucket_name"]
    gcs_path = gcs_path or config["gcs"]["index_path"]

    bucket = get_bucket(bucket_name)
    for root, _, files in os.walk(local_path):
        for file in files:
            local_file_path = os.path.join(root, file)
            blob_path = os.path.relpath(local_file_path, local_path)
            blob = bucket.blob(os.path.join(gcs_path, blob_path))
            blob.upload_from_filename(local_file_path)
            logger.info(
                f"Uploaded {local_file_path} to gs://{bucket_name}/{gcs_path}/{blob_path}"
            )


def read_data(bucket_name=None, gcs_path=None, local_path=None):
    config = config_loader.get_config()
    bucket_name = bucket_name or config["gcs"]["bucket_name"]
    gcs_path = gcs_path or config["gcs"]["index_path"]
    local_path = local_path or os.path.join(base_dir, ".ragatouille/colbert/indexes")

    bucket = get_bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=gcs_path)
    for blob in blobs:
        local_file_path = os.path.join(local_path, os.path.relpath(blob.name, gcs_path))
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        blob.download_to_filename(local_file_path)
        logger.info(f"Downloaded {blob.name} to {local_file_path}")


def create_bucket(bucket_name):
    """Create a GCS bucket if it does not exist."""
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        logger.info(f"Bucket {bucket_name} does not exist. Creating it.")
        bucket.create(location="us")
        logger.info(f"Bucket {bucket_name} created.")
    else:
        logger.info(f"Bucket {bucket_name} already exists.")
