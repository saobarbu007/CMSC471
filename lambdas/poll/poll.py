import json
import os
import boto3
from botocore.exceptions import ClientError

# Reads the job_id from the path parameter and queries DynamoDB to return the latest processing status to the frontend
dynamodb = boto3.resource("dynamodb")

JOBS_TABLE = os.environ.get("JOBS_TABLE", "")


def lambda_handler(event, context):
    """
    Polls the Jobs DynamoDB table for the current processing status of a job.
    The front end calls this repeatedly after submitting an image
    until the status is COMPLETE or FAILED.

    Path parameter: /poll/{job_id}
    """
    try:
        # ── Extract job_id from path parameters ─────────────────────────────
        path_params = event.get("pathParameters") or {}
        job_id = path_params.get("job_id")

        if not job_id:
            return _response(400, {"error": "Missing job_id in path."})

        # ── Look up job in DynamoDB ──────────────────────────────────────────
        table = dynamodb.Table(JOBS_TABLE)
        result = table.get_item(Key={"job_id": job_id})
        item = result.get("Item")

        if not item:
            return _response(404, {"error": f"Job '{job_id}' not found."})

        # ── Return status and relevant metadata ──────────────────────────────
        return _response(200, {
            "job_id": job_id,
            "status": item.get("status", "UNKNOWN"),
            "item_count": item.get("item_count", 0),
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
            "record_ids": item.get("record_ids", []),
            "error_detail": item.get("error_detail")
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
