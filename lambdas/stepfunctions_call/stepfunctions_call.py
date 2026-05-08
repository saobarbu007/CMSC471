import boto3
import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

textract = boto3.client("textract")

# Items whose confidence falls below this threshold are flagged as uncertain
# rather than saved as confirmed. Default is 80% if not set in environment.
CONFIDENCE_THRESHOLD = float(os.environ.get("CONFIDENCE_THRESHOLD", "80.0"))


def lambda_handler(event, context):
    """
    Step 2 of the state machine: call Amazon Textract on the uploaded image
    and sort detected words into confirmed vs. uncertain buckets based on
    each word's confidence score.

    Expects event keys:
        bucket  (str)  – S3 bucket name
        key     (str)  – S3 object key of the image
        job_id  (str)  – job identifier (passed through unchanged)

    Returns the original event enriched with:
        confirmed_items  (list[str])  – high-confidence detected words
        uncertain_items  (list[dict]) – low-confidence words with their scores
        raw_blocks       (list[dict]) – full Textract LINE blocks for reference
    """
    bucket = event["bucket"]
    key = event["key"]
    job_id = event["job_id"]

    logger.info(
        json.dumps({
            "job_id": job_id,
            "action": "textract_call",
            "bucket": bucket,
            "key": key,
            "confidence_threshold": CONFIDENCE_THRESHOLD,
        })
    )

    response = textract.detect_document_text(
        Document={"S3Object": {"Bucket": bucket, "Name": key}}
    )

    confirmed_items = []
    uncertain_items = []
    raw_blocks = []

    for block in response.get("Blocks", []):
        # Only process LINE blocks so we get whole line text rather than
        # individual words; LINE blocks still carry a per-line confidence.
        if block.get("BlockType") != "LINE":
            continue

        text = block.get("Text", "").strip()
        confidence = block.get("Confidence", 0.0)

        if not text:
            continue

        raw_blocks.append({"text": text, "confidence": confidence})

        if confidence >= CONFIDENCE_THRESHOLD:
            confirmed_items.append(text)
        else:
            uncertain_items.append({"text": text, "confidence": round(confidence, 2)})

    logger.info(
        json.dumps({
            "job_id": job_id,
            "action": "textract_complete",
            "confirmed_count": len(confirmed_items),
            "uncertain_count": len(uncertain_items),
        })
    )

    return {
        **event,
        "confirmed_items": confirmed_items,
        "uncertain_items": uncertain_items,
        "raw_blocks": raw_blocks,
    }