import json
import os
import boto3
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

RECORDS_TABLE = os.environ["RECORDS_TABLE"]
JOBS_TABLE    = os.environ["JOBS_TABLE"]
INBOX_BUCKET  = os.environ["INBOX_BUCKET"]

records_table = dynamodb.Table(RECORDS_TABLE)
jobs_table    = dynamodb.Table(JOBS_TABLE)


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    method      = event.get("httpMethod", "")
    path_params = event.get("pathParameters") or {}
    record_id   = path_params.get("record_id")
    resource    = event.get("resource", "")

    As a user, I want to view all my extracted shopping list items so that I can see what was recognized
    # ── GET /records ──────────────────────────────────────────────────────────
    if method == "GET":
        result = records_table.scan()
        items  = result.get("Items", [])
        # Sort newest first; fall back gracefully if created_at is missing
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return _response(200, {"items": items})

    # On DELETE, removes the record from DynamoDB, cleans up the source image in S3, and deletes the job entry if no records remain
    # ── DELETE /records/{record_id} ───────────────────────────────────────────
    if method == "DELETE" and record_id:
        # Fetch the record so we know job_id and s3_key before deleting
        resp = records_table.get_item(Key={"record_id": record_id})
        item = resp.get("Item")
        if not item:
            return _response(404, {"error": "Record not found"})

        job_id = item.get("job_id")
        s3_key = item.get("s3_key")

        # Delete the record
        records_table.delete_item(Key={"record_id": record_id})

        # Check if any sibling records remain for the same job
        siblings = records_table.scan(
            FilterExpression=Attr("job_id").eq(job_id)
        ).get("Items", [])

        if not siblings:
            # Last item for this job — clean up S3 image and job record
            if s3_key:
                try:
                    s3.delete_object(Bucket=INBOX_BUCKET, Key=s3_key)
                except Exception:
                    pass  # Don't fail the delete if S3 cleanup errors
            jobs_table.delete_item(Key={"job_id": job_id})

        return _response(200, {"deleted": record_id})

    # ── PUT /records/{record_id}/star ─────────────────────────────────────────
    if method == "PUT" and record_id and resource.endswith("/star"):
        # Confirm the record exists before updating
        resp = records_table.get_item(Key={"record_id": record_id})
        if not resp.get("Item"):
            return _response(404, {"error": "Record not found"})

        body = json.loads(event.get("body") or "{}")
        starred = bool(body.get("starred", True))

        records_table.update_item(
            Key={"record_id": record_id},
            UpdateExpression="SET starred = :val",
            ExpressionAttributeValues={":val": starred},
        )
        return _response(200, {"record_id": record_id, "starred": starred})

    return _response(400, {"error": "Unsupported route"})
