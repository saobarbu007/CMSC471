import json

# Lightweight endpoint that returns a fixed JSON payload so monitors and developers can verify the API gateway is reachable
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
