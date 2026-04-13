# Cloudflare + Lambda Deployment Guide

This repo is now prepared for:

- `Frontend`: Cloudflare Pages
- `Backend API`: AWS Lambda container image
- `Background ingestion jobs`: AWS Lambda triggered by SQS

The old App Runner deployment path has been archived under [`ex-apprunner/`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/ex-apprunner).

## 1. What Changed In The Repo

- The active backend container file is now [`backend/Dockerfile`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/Dockerfile) for Lambda.
- The HTTP Lambda entry point is [`backend/lambda_handler.py`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/lambda_handler.py).
- The SQS worker Lambda entry point is [`backend/jobs_handler.py`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/jobs_handler.py).
- Runtime bootstrap for `/tmp` storage and Firebase decoding lives in [`backend/runtime_bootstrap.py`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/runtime_bootstrap.py).
- Cloudflare SPA routing is enabled by [`bluetide-ui/public/_redirects`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/bluetide-ui/public/_redirects).

## 2. Prerequisites

- AWS CLI configured
- Docker installed
- An AWS account with access to Lambda, ECR, IAM, SQS, and optionally Route 53 / API Gateway
- A Cloudflare account with Pages enabled
- Firebase web config values
- Firebase service account JSON
- Neon/Postgres connection string
- OpenAI key and any connector secrets you use

## 3. Backend Secrets You Need

Use [`backend/.env.lambda.example`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/.env.lambda.example) as the checklist.

Required in most setups:

- `OPENAI_API_KEY`
- `NEON_CONNECTION_STRING`
- `AWS_REGION`
- `AWS_S3_BUCKET_NAME`
- `FIREBASE_SERVICE_ACCOUNT_B64`
- `TOKEN_ENCRYPTION_KEY`
- `CORS_ORIGINS`
- `BACKEND_PUBLIC_URL`
- `JOB_QUEUE_URL`

Common optional ones:

- `GEMINI_API_KEY`
- `GDRIVE_OAUTH_CLIENT_ID`
- `GDRIVE_OAUTH_CLIENT_SECRET`
- `SHAREPOINT_TENANT_ID`
- `SHAREPOINT_CLIENT_ID`
- `SHAREPOINT_CLIENT_SECRET`
- `SHAREPOINT_OAUTH_CLIENT_ID`
- `SHAREPOINT_OAUTH_CLIENT_SECRET`

## 4. Create The SQS Queue

Create the ingestion queue first, because the API Lambda will publish job messages to it.

```bash
AWS_REGION=ap-south-1

aws sqs create-queue \
  --queue-name bluetide-ingestion-jobs \
  --region "$AWS_REGION"
```

Save the resulting queue URL as `JOB_QUEUE_URL`.

## 5. Create The Lambda Execution Role

Create one IAM role for both Lambdas, then attach:

- `AWSLambdaBasicExecutionRole`
- S3 access for your document bucket
- SQS consume permissions for the worker Lambda
- SQS send permissions for the API Lambda

At minimum, the custom policy should allow:

- `s3:GetObject`
- `s3:PutObject`
- `s3:ListBucket`
- `sqs:SendMessage`
- `sqs:ReceiveMessage`
- `sqs:DeleteMessage`
- `sqs:GetQueueAttributes`

## 6. Build And Push The Backend Lambda Image

```bash
AWS_REGION=ap-south-1
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

aws ecr create-repository \
  --repository-name bluetide/backend-lambda \
  --region "$AWS_REGION"

aws ecr get-login-password --region "$AWS_REGION" | \
docker login --username AWS --password-stdin \
"$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com"

docker build \
  --platform linux/amd64 \
  -t bluetide-backend-lambda \
  -f backend/Dockerfile backend

docker tag bluetide-backend-lambda:latest \
  "$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend-lambda:latest"

docker push \
  "$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend-lambda:latest"
```

## 7. Create The API Lambda

Use the image above to create the HTTP API Lambda.

Recommended starting settings:

- `Memory`: `3072` or `4096`
- `Timeout`: `900`
- `Ephemeral storage`: `2048` or higher
- `Reserved concurrency`: `5`

```bash
aws lambda create-function \
  --function-name bluetide-api \
  --package-type Image \
  --code ImageUri="$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend-lambda:latest" \
  --role arn:aws:iam::$AWS_ACCOUNT:role/BlueTideLambdaRole \
  --timeout 900 \
  --memory-size 3072 \
  --ephemeral-storage '{"Size": 2048}' \
  --environment "Variables={AWS_REGION=$AWS_REGION,AWS_S3_BUCKET_NAME=your-bucket,OPENAI_API_KEY=...,NEON_CONNECTION_STRING=...,FIREBASE_SERVICE_ACCOUNT_B64=...,TOKEN_ENCRYPTION_KEY=...,CORS_ORIGINS=https://your-project.pages.dev,BACKEND_PUBLIC_URL=https://api.example.com,JOB_QUEUE_URL=https://sqs.$AWS_REGION.amazonaws.com/$AWS_ACCOUNT/bluetide-ingestion-jobs}"
```

## 8. Create The Worker Lambda

Create a second Lambda from the same image, but override the command to use the SQS worker handler.

```bash
aws lambda create-function \
  --function-name bluetide-jobs \
  --package-type Image \
  --code ImageUri="$AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend-lambda:latest" \
  --role arn:aws:iam::$AWS_ACCOUNT:role/BlueTideLambdaRole \
  --timeout 900 \
  --memory-size 3072 \
  --ephemeral-storage '{"Size": 2048}' \
  --image-config '{"Command":["jobs_handler.handler"]}' \
  --environment "Variables={AWS_REGION=$AWS_REGION,AWS_S3_BUCKET_NAME=your-bucket,OPENAI_API_KEY=...,NEON_CONNECTION_STRING=...,FIREBASE_SERVICE_ACCOUNT_B64=...,TOKEN_ENCRYPTION_KEY=...,CORS_ORIGINS=https://your-project.pages.dev,BACKEND_PUBLIC_URL=https://api.example.com,JOB_QUEUE_URL=https://sqs.$AWS_REGION.amazonaws.com/$AWS_ACCOUNT/bluetide-ingestion-jobs}"
```

Attach the queue as an event source:

```bash
QUEUE_ARN=$(aws sqs get-queue-attributes \
  --queue-url "https://sqs.$AWS_REGION.amazonaws.com/$AWS_ACCOUNT/bluetide-ingestion-jobs" \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)

aws lambda create-event-source-mapping \
  --function-name bluetide-jobs \
  --event-source-arn "$QUEUE_ARN" \
  --batch-size 1
```

## 9. Expose The API Lambda

Simplest path: use a Lambda Function URL.

```bash
aws lambda create-function-url-config \
  --function-name bluetide-api \
  --auth-type NONE
```

Save the URL. Your frontend API base should be:

```text
https://your-lambda-url.lambda-url.<region>.on.aws/api/v1
```

If you use a custom backend domain, point it to API Gateway or another front door and set `BACKEND_PUBLIC_URL` to that final public URL.

## 10. Deploy The Frontend To Cloudflare Pages

In Cloudflare Pages:

- `Framework preset`: `Vite`
- `Build command`: `npm run build`
- `Build output directory`: `dist`
- `Root directory`: `bluetide-ui`

Set these environment variables in Cloudflare Pages:

- `VITE_API_URL=https://api.example.com/api/v1`
- `VITE_FIREBASE_API_KEY=...`
- `VITE_FIREBASE_AUTH_DOMAIN=...`
- `VITE_FIREBASE_PROJECT_ID=...`
- `VITE_FIREBASE_STORAGE_BUCKET=...`
- `VITE_FIREBASE_APP_ID=...`

If you deploy with CLI:

```bash
cd bluetide-ui
npm ci
npm run build
```

Then deploy the `dist` directory through Cloudflare Pages.

## 11. Configure OAuth Redirect URIs

Because the frontend is now static and no longer reverse-proxies `/api/*`, your callback URLs should point at the backend public URL, not the frontend domain.

Register:

- `https://api.example.com/api/v1/auth/gdrive/callback`
- `https://api.example.com/api/v1/auth/sharepoint/callback`

The backend now supports this via `BACKEND_PUBLIC_URL` in [`backend/src/api/routes/oauth.py`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/backend/src/api/routes/oauth.py).

## 12. Smoke Test

Check these in order:

1. Open the frontend and verify login works.
2. Call `GET /api/v1/health` on the backend URL.
3. Start a datalake job and confirm `POST /api/v1/jobs/process` returns a `job_id`.
4. Watch CloudWatch logs for `bluetide-api` and `bluetide-jobs`.
5. Confirm the worker Lambda consumes the SQS message and updates the Firestore job status.

## 13. Important Runtime Note

Direct multipart uploads to Lambda still have AWS payload-size limits. The existing direct-upload UI will work best for smaller files. For larger user uploads, the next improvement would be presigned S3 uploads plus server-side processing from S3.
