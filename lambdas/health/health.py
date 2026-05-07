import json


def lambda_handler(event, context):
    """
    Health check endpoint.
    Returns 200 OK to confirm the API is reachable.
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "status": "ok",
            "message": "Shopping List API is healthy."
        })
    }
