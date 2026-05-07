import json
import os
import uuid
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
sfn = boto3.client("stepfunctions")

INBOX_BUCKET = os.environ.get("INBOX_BUCKET", "")
JOBS_TABLE = os.environ.get("JOBS_TABLE", "")
STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")


def lambda_handler(event, context):
    """
    Accepts a base64-encoded image upload from the front end.
    1. Saves the image to the Inbox S3 bucket.
    2. Creates a job record in the Jobs DynamoDB table with status PENDING.
    3. Starts the Step Functions state machine to process the image.
    Returns the job_id so the client can poll for status.
    """
    try:
        # ── Parse request body ──────────────────────────────────────────────
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)

        image_data = body.get("image")          # base64-encoded image string
        file_name = body.get("file_name", "upload.jpg")
        content_type = body.get("content_type", "image/jpeg")

        if not image_data:
            return _response(400, {"error": "Missing 'image' field in request body."})

        # ── Decode and store image in Inbox bucket ──────────────────────────
        import base64
        image_bytes = base64.b64decode(image_data)
        job_id = str(uuid.uuid4())
        s3_key = f"uploads/{job_id}/{file_name}"

        s3.put_object(
            Bucket=INBOX_BUCKET,
            Key=s3_key,
            Body=image_bytes,
            ContentType=content_type
        )

        # ── Write job record to DynamoDB ────────────────────────────────────
        table = dynamodb.Table(JOBS_TABLE)
        timestamp = datetime.now(timezone.utc).isoformat()

        table.put_item(Item={
            "job_id": job_id,
            "status": "PENDING",
            "s3_key": s3_key,
            "file_name": file_name,
            "created_at": timestamp,
            "updated_at": timestamp
        })

        # ── Start Step Functions execution ──────────────────────────────────
        sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=f"job-{job_id}",
            input=json.dumps({
                "job_id": job_id,
                "s3_key": s3_key,
                "bucket": INBOX_BUCKET
            })
        )

        return _response(200, {
            "message": "Image submitted successfully.",
            "job_id": job_id
        })

    except ClientError as e:
        return _response(500, {"error": "AWS error", "detail": str(e)})
    except Exception as e:
        return _response(500, {"error": "Unexpected error", "detail": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }
