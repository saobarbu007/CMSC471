import json
import os
import uuid
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")

JOBS_TABLE = os.environ.get("JOBS_TABLE", "")
RECORDS_TABLE = os.environ.get("RECORDS_TABLE", "")


def lambda_handler(event, context):
    """
    Step 3 (final) of the state machine workflow.
    Saves each extracted shopping list item as its own record in the Records DynamoDB table.
    Updates the job status to COMPLETE in the Jobs table.
    """
    job_id = event.get("job_id")
    items = event.get("items", [])
    s3_key = event.get("s3_key", "")

    if not job_id:
        raise ValueError("Missing required field: job_id")

    records_table = dynamodb.Table(RECORDS_TABLE)
    jobs_table = dynamodb.Table(JOBS_TABLE)
    timestamp = datetime.now(timezone.utc).isoformat()

    saved_record_ids = []

    try:
        # ── Save each item as an individual record ──────────────────────────
        for item in items:
            record_id = str(uuid.uuid4())
            records_table.put_item(Item={
                "record_id": record_id,
                "job_id": job_id,
                "item_name": item.get("item_name", "Unknown Item"),
                "quantity": item.get("quantity"),
                "checked": item.get("checked", False),
                "source_image": s3_key,
                "created_at": timestamp
            })
            saved_record_ids.append(record_id)

        # ── Mark job as COMPLETE ────────────────────────────────────────────
        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #st = :status, updated_at = :ts, record_ids = :rids",
            ExpressionAttributeNames={"#st": "status"},
            ExpressionAttributeValues={
                ":status": "COMPLETE",
                ":ts": timestamp,
                ":rids": saved_record_ids
            }
        )

        return {
            "job_id": job_id,
            "status": "COMPLETE",
            "saved_count": len(saved_record_ids),
            "record_ids": saved_record_ids
        }

    except ClientError as e:
        # ── Mark job as FAILED on error ─────────────────────────────────────
        try:
            jobs_table.update_item(
                Key={"job_id": job_id},
                UpdateExpression="SET #st = :status, updated_at = :ts, error_detail = :err",
                ExpressionAttributeNames={"#st": "status"},
                ExpressionAttributeValues={
                    ":status": "FAILED",
                    ":ts": timestamp,
                    ":err": str(e)
                }
            )
        except Exception:
            pass
        raise RuntimeError(f"Failed to save records: {str(e)}")
