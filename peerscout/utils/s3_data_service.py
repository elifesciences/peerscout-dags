from contextlib import contextmanager
import yaml
import boto3
from botocore.exceptions import ClientError


@contextmanager
def s3_open_binary_read(bucket: str, object_key: str):
    s3_client = boto3.client("s3")
    response = s3_client.get_object(Bucket=bucket, Key=object_key)
    streaming_body = response["Body"]
    try:
        yield streaming_body
    finally:
        streaming_body.close()


def download_s3_yaml_object_as_json(bucket: str, object_key: str) -> dict:
    with s3_open_binary_read(
            bucket=bucket, object_key=object_key
    ) as streaming_body:
        return yaml.safe_load(streaming_body)


def get_stored_state(
        state_file_bucket_name,
        state_file_object_name
):
    try:
        stored_state = (
            download_s3_yaml_object_as_json(
                state_file_bucket_name,
                state_file_object_name
            )
            if state_file_bucket_name and
            state_file_object_name else None
        )
    except ClientError as ex:
        if ex.response['Error']['Code'] == 'NoSuchKey':
            stored_state = {}
        else:
            raise ex
    return stored_state


def upload_s3_object(bucket: str, object_key: str, data_object):
    s3_client = boto3.client("s3")
    s3_client.put_object(Body=data_object, Bucket=bucket, Key=object_key)


def delete_s3_object(bucket, object_key):
    s3_client = boto3.client('s3')
    s3_client.delete_object(
        Bucket=bucket,
        Key=object_key
    )
