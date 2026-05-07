import json
import os
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

RECORDS_TABLE = os.environ.get("RECORDS_TABLE", "")
JOBS_TABLE = os.environ.get("JOBS_TABLE", "")
INBOX_BUCKET = os.environ.get("INBOX_BUCKET", "")


def lambda_handler(event, context):
    """
    Handles two routes:
      GET  /records             -> Returns all shopping list records from DynamoDB.
      DELETE /records/{record_id} -> Deletes a single record from DynamoDB.
                                     If it's the last record for a job, also deletes
                                     the source image from S3 and the job entry.
    """
    http_method = event.get("httpMethod", "GET")
    path_params = event.get("pathParameters") or {}
    record_id = path_params.get("record_id")

    if http_method == "GET":
        return get_all_records()
    elif http_method == "DELETE" and record_id:
        return delete_record(record_id)
    else:
        return _response(400, {"error": "Unsupported method or missing record_id."})


# ── GET /records ────────────────────────────────────────────────────────────────
def get_all_records():
    try:
        table = dynamodb.Table(RECORDS_TABLE)
        result = table.scan()
        items = result.get("Items", [])

        # Handle DynamoDB pagination
        while "LastEvaluatedKey" in result:
            result = table.scan(ExclusiveStartKey=result["LastEvaluatedKey"])
            items.extend(result.get("Items", []))

        # Sort by created_at descending (newest first)
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return _response(200, {
            "records": items,
            "count": len(items)
        })

    except ClientError as e:
        return _response(500, {"error": "Failed to retrieve records.", "detail": str(e)})


# ── DELETE /records/{record_id} ─────────────────────────────────────────────────
def delete_record(record_id):
    try:
        records_table = dynamodb.Table(RECORDS_TABLE)
        jobs_table = dynamodb.Table(JOBS_TABLE)

        # ── Fetch the record first to get job_id and source image ────────────
        result = records_table.get_item(Key={"record_id": record_id})
        item = result.get("Item")

        if not item:
            return _response(404, {"error": f"Record '{record_id}' not found."})

        job_id = item.get("job_id")
        source_image = item.get("source_image")

        # ── Delete the individual record ─────────────────────────────────────
        records_table.delete_item(Key={"record_id": record_id})

        # ── Check if any records remain for this job ─────────────────────────
        if job_id:
            remaining = records_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr("job_id").eq(job_id)
            )
            remaining_items = remaining.get("Items", [])

            # If no records remain, clean up the job and its S3 image
            if len(remaining_items) == 0:
                # Delete the source image from S3
                if source_image and INBOX_BUCKET:
                    try:
                        s3.delete_object(Bucket=INBOX_BUCKET, Key=source_image)
                    except ClientError:
                        pass  # Best-effort S3 cleanup

                # Delete the job record from DynamoDB
                try:
                    jobs_table.delete_item(Key={"job_id": job_id})
                except ClientError:
                    pass  # Best-effort job cleanup

        return _response(200, {
            "message": f"Record '{record_id}' deleted successfully.",
            "record_id": record_id,
            "job_id": job_id
        })

    except ClientError as e:
        return _response(500, {"error": "Failed to delete record.", "detail": str(e)})
    except Exception as e:
        return _response(500, {"error": "Unexpected error.", "detail": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, default=str)
    }
