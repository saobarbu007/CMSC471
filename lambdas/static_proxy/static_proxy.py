import json
import os
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
STATIC_BUCKET = os.environ.get("STATIC_BUCKET", "")


def lambda_handler(event, context):
    """
    Serves index.html from the static S3 website bucket.
    Acts as a proxy so API Gateway can deliver the front-end page.
    """
    try:
        response = s3.get_object(Bucket=STATIC_BUCKET, Key="index.html")
        html_content = response["Body"].read().decode("utf-8")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html",
                "Access-Control-Allow-Origin": "*"
            },
            "body": html_content
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        return {
            "statusCode": 404 if error_code == "NoSuchKey" else 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Could not retrieve index.html",
                "detail": str(e)
            })
        }
