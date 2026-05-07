import json
import os
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

JOBS_TABLE = os.environ.get("JOBS_TABLE", "")


def lambda_handler(event, context):
    """
    Step 1 of the state machine workflow.
    Fetches the uploaded image from the Inbox S3 bucket and confirms it exists.
    Updates the job status to IN_PROGRESS in the Jobs table.
    Passes job metadata downstream to the next state.
    """
    job_id = event.get("job_id")
    s3_key = event.get("s3_key")
    bucket = event.get("bucket")

    if not all([job_id, s3_key, bucket]):
        raise ValueError("Missing required fields: job_id, s3_key, bucket")

    try:
        # ── Confirm the image exists in S3 ──────────────────────────────────
        s3.head_object(Bucket=bucket, Key=s3_key)

        # ── Update job status to IN_PROGRESS ────────────────────────────────
        table = dynamodb.Table(JOBS_TABLE)
        from datetime import datetime, timezone
        table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #st = :status, updated_at = :ts",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":status": "IN_PROGRESS",
                ":ts": datetime.now(timezone.utc).isoformat()
            }
        )

        # ── Pass data to next Lambda in state machine ───────────────────────
        return {
            "job_id": job_id,
            "s3_key": s3_key,
            "bucket": bucket,
            "status": "IN_PROGRESS"
        }

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code in ("404", "NoSuchKey"):
            raise FileNotFoundError(f"Image not found in S3: s3://{bucket}/{s3_key}")
        raise RuntimeError(f"AWS error during fetch: {str(e)}")
