# Shopping List AI — CMSC 471 Final Project

An AWS serverless application that processes handwritten shopping list photos using Amazon Textract.

---

## Project Structure

```
project/
├── template.yaml                        # SAM infrastructure template (14 resources)
├── samconfig.toml                       # SAM deploy configuration
├── frontend/
│   └── index.html                       # Static front-end UI
├── statemachine/
│   └── shopping_list.asl.json           # Step Functions state machine definition
└── lambdas/
    ├── health/health.py                 # GET /health
    ├── static_proxy/static_proxy.py     # GET /  (serves index.html)
    ├── submit_process/submit_process.py # POST /submit
    ├── stepfunctions_fetch/...          # Step 1: confirm image in S3
    ├── stepfunctions_call/...           # Step 2: call Textract
    ├── stepfunctions_save/...           # Step 3: save items to DynamoDB
    ├── poll/poll.py                     # GET /poll/{job_id}
    └── records/records.py              # GET /records, DELETE /records/{id}
```

---

## Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI installed (`sam --version`)
- Python 3.11+

---

## Deploy

```bash
# 1. Build
sam build

# 2. Deploy (first time — walks you through setup)
sam deploy --guided

# Or use samconfig.toml defaults
sam deploy
```

---

## After Deploying

1. Copy the `ApiEndpoint` from the Outputs section of the deploy.
2. Open `frontend/index.html` and replace `YOUR_API_ID` in the `API_BASE` variable:
   ```js
   const API_BASE = "https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/Prod";
   ```
3. Upload `index.html` to your static S3 bucket:
   ```bash
   aws s3 cp frontend/index.html s3://shopping-list-static-YOUR_ACCOUNT_ID/index.html
   ```

---

## Teardown

```bash
sam delete --stack-name shopping-list-app
```

---

## Architecture

```
User → index.html (S3)
     → POST /submit → SubmitProcessLambda → InboxBucket (S3) + JobsTable (DynamoDB)
                                          → Step Functions State Machine
                                              → StepFunctionsFetchLambda  (confirm image)
                                              → StepFunctionsCallLambda   (Textract OCR)
                                              → StepFunctionsSaveLambda   (save to RecordsTable)
     → GET /poll/{job_id} → PollLambda → JobsTable
     → GET /records       → RecordsLambda → RecordsTable
     → DELETE /records/{id} → RecordsLambda → RecordsTable + S3 cleanup
```
