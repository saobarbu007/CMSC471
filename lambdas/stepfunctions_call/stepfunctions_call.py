import json
import os
import boto3
from botocore.exceptions import ClientError

textract = boto3.client("textract")
dynamodb = boto3.resource("dynamodb")

JOBS_TABLE = os.environ.get("JOBS_TABLE", "")


def lambda_handler(event, context):
    """
    Step 2 of the state machine workflow.
    Calls Amazon Textract to extract text from the uploaded shopping list image.
    Parses the raw Textract response into a clean list of shopping items.
    Passes the extracted items downstream to the Save Lambda.
    """
    job_id = event.get("job_id")
    s3_key = event.get("s3_key")
    bucket = event.get("bucket")

    if not all([job_id, s3_key, bucket]):
        raise ValueError("Missing required fields: job_id, s3_key, bucket")

    try:
        # ── Call Textract ───────────────────────────────────────────────────
        response = textract.detect_document_text(
            Document={
                "S3Object": {
                    "Bucket": bucket,
                    "Name": s3_key
                }
            }
        )

        # ── Parse Textract blocks into plain text lines ─────────────────────
        lines = []
        for block in response.get("Blocks", []):
            if block.get("BlockType") == "LINE":
                text = block.get("Text", "").strip()
                if text:
                    lines.append(text)

        # ── Build structured shopping items ─────────────────────────────────
        items = []
        for line in lines:
            items.append({
                "item_name": line,
                "quantity": None,       # Could be parsed further with NLP
                "checked": False
            })

        # ── Update job with item count ───────────────────────────────────────
        table = dynamodb.Table(JOBS_TABLE)
        from datetime import datetime, timezone
        table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET item_count = :count, updated_at = :ts",
            ExpressionAttributeValues={
                ":count": len(items),
                ":ts": datetime.now(timezone.utc).isoformat()
            }
        )

        return {
            "job_id": job_id,
            "s3_key": s3_key,
            "bucket": bucket,
            "items": items,
            "item_count": len(items)
        }

    except ClientError as e:
        raise RuntimeError(f"Textract error: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error in Call Lambda: {str(e)}")
