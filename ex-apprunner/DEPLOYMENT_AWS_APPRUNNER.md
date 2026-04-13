# AWS App Runner Deployment Guide – BlueTide IDP

This guide covers deploying the **BlueTide Backend** (FastAPI) and **Frontend** (React/Vite)
as two separate AWS App Runner services backed by Amazon ECR container images.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│                      Internet                        │
└───────────────┬──────────────────────┬───────────────┘
                │                      │
    ┌───────────▼──────────┐ ┌────────▼───────────────┐
    │  App Runner (Frontend)│ │  App Runner (Backend)   │
    │  React SPA via Nginx  │ │  FastAPI + Uvicorn      │
    │  Port 8080            │ │  Port 8000              │
    └───────────────────────┘ └────────┬───────────────┘
                                       │
              ┌────────────────────────┼────────────────────┐
              │                        │                    │
    ┌─────────▼──────┐   ┌────────────▼──────┐   ┌────────▼──────┐
    │   Neon Postgres │   │  Firebase / GCP   │   │   AWS S3      │
    │   (pgvector)    │   │  (Auth+Firestore) │   │  (datalake)   │
    └────────────────┘   └───────────────────┘   └───────────────┘
```

---

## Prerequisites

| Requirement | Why |
|---|---|
| **AWS CLI v2** | Push images, create services |
| **Docker** | Build container images |
| **ECR Repository** | Store Docker images |
| **AWS IAM role** | App Runner instance role with S3 access |
| **Neon Postgres** | Database already provisioned |
| **Firebase project** | Auth + Firestore already configured |

---

## Step 1 – Create ECR Repositories

```bash
AWS_REGION=ap-south-1  # or your preferred region
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# Backend repository
aws ecr create-repository \
    --repository-name bluetide/backend \
    --region $AWS_REGION

# Frontend repository
aws ecr create-repository \
    --repository-name bluetide/frontend \
    --region $AWS_REGION
```

---

## Step 2 – Build & Push Docker Images

### 2a. Login to ECR

```bash
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
```

### 2b. Build & Push Backend

```bash
cd backend

docker build \
    --platform linux/amd64 \
    -t bluetide-backend .

docker tag bluetide-backend:latest \
    $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend:latest

docker push \
    $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend:latest
```

### 2c. Build & Push Frontend

```bash
cd bluetide-ui

# Replace these with your actual values
docker build \
    --platform linux/amd64 \
    --build-arg VITE_API_URL=https://<BACKEND-APPRUNNER-URL>/api/v1 \
    --build-arg VITE_FIREBASE_API_KEY=AIzaSyD8NbjzmQOhyf8lqdM7wlqkpYoFHDdfROM \
    --build-arg VITE_FIREBASE_AUTH_DOMAIN=advanced-idp.firebaseapp.com \
    --build-arg VITE_FIREBASE_PROJECT_ID=advanced-idp \
    --build-arg VITE_FIREBASE_STORAGE_BUCKET=advanced-idp.firebasestorage.app \
    --build-arg VITE_FIREBASE_APP_ID=1:353590867679:web:27b6c816ad32d248975b6a \
    -t bluetide-frontend .

docker tag bluetide-frontend:latest \
    $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/frontend:latest

docker push \
    $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/frontend:latest
```

> **Note:** You must deploy the backend first to get its App Runner URL, then
> rebuild the frontend with the correct `VITE_API_URL`.

---

## Step 3 – Prepare Firebase Service Account Key

App Runner doesn't support file mounts. The entrypoint script decodes a base64-encoded
Firebase service account JSON key from an environment variable at startup.

```bash
# Encode your Firebase service account key as base64
FIREBASE_B64=$(base64 -i advanced-idp-firebase-adminsdk-fbsvc-088b57c35c.json)

# You'll use this value as the FIREBASE_SERVICE_ACCOUNT_B64 env var
echo $FIREBASE_B64
```

---

## Step 4 – Create IAM Roles

### 4a. ECR Access Role (for App Runner to pull images)

```bash
aws iam create-role \
    --role-name AppRunnerECRAccessRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "build.apprunner.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

aws iam attach-role-policy \
    --role-name AppRunnerECRAccessRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

### 4b. Instance Role (for S3 access at runtime)

```bash
aws iam create-role \
    --role-name BlueTideAppRunnerInstanceRole \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "tasks.apprunner.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

# Attach S3 read/write access
aws iam attach-role-policy \
    --role-name BlueTideAppRunnerInstanceRole \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

---

## Step 5 – Deploy Backend App Runner Service

```bash
aws apprunner create-service \
    --service-name bluetide-backend \
    --source-configuration '{
        "AuthenticationConfiguration": {
            "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT':role/AppRunnerECRAccessRole"
        },
        "ImageRepository": {
            "ImageIdentifier": "'$AWS_ACCOUNT'.dkr.ecr.'$AWS_REGION'.amazonaws.com/bluetide/backend:latest",
            "ImageRepositoryType": "ECR",
            "ImageConfiguration": {
                "Port": "8000",
                "RuntimeEnvironmentVariables": {
                    "PORT": "8000",
                    "WORKERS": "2",
                    "LOG_LEVEL": "info",
                    "OPENAI_API_KEY": "<YOUR_OPENAI_KEY>",
                    "NEON_CONNECTION_STRING": "<YOUR_NEON_CONN_STRING>",
                    "GEMINI_API_KEY": "<YOUR_GEMINI_KEY>",
                    "AWS_REGION": "ap-south-1",
                    "AWS_S3_BUCKET_NAME": "teclusion-datalake-idp",
                    "FIREBASE_SERVICE_ACCOUNT_B64": "<BASE64_ENCODED_JSON>",
                    "CORS_ORIGINS": "https://<FRONTEND-APPRUNNER-URL>",
                    "TOKEN_ENCRYPTION_KEY": "<YOUR_FERNET_KEY>",
                    "SHAREPOINT_TENANT_ID": "<SP_TENANT_ID>",
                    "SHAREPOINT_CLIENT_ID": "<SP_CLIENT_ID>",
                    "SHAREPOINT_CLIENT_SECRET": "<SP_SECRET>",
                    "GDRIVE_OAUTH_CLIENT_ID": "<GDRIVE_CLIENT_ID>",
                    "GDRIVE_OAUTH_CLIENT_SECRET": "<GDRIVE_SECRET>"
                }
            }
        }
    }' \
    --instance-configuration '{
        "Cpu": "1 vCPU",
        "Memory": "2 GB",
        "InstanceRoleArn": "arn:aws:iam::'$AWS_ACCOUNT':role/BlueTideAppRunnerInstanceRole"
    }' \
    --health-check-configuration '{
        "Protocol": "HTTP",
        "Path": "/api/v1/health",
        "Interval": 20,
        "Timeout": 5,
        "HealthyThreshold": 1,
        "UnhealthyThreshold": 5
    }' \
    --region $AWS_REGION
```

### Get the Backend URL

```bash
aws apprunner describe-service \
    --service-arn <BACKEND_SERVICE_ARN> \
    --region $AWS_REGION \
    --query 'Service.ServiceUrl' --output text
```

---

## Step 6 – Deploy Frontend App Runner Service

After getting the backend URL, rebuild the frontend image with the correct `VITE_API_URL`
(see Step 2c), then:

```bash
aws apprunner create-service \
    --service-name bluetide-frontend \
    --source-configuration '{
        "AuthenticationConfiguration": {
            "AccessRoleArn": "arn:aws:iam::'$AWS_ACCOUNT':role/AppRunnerECRAccessRole"
        },
        "ImageRepository": {
            "ImageIdentifier": "'$AWS_ACCOUNT'.dkr.ecr.'$AWS_REGION'.amazonaws.com/bluetide/frontend:latest",
            "ImageRepositoryType": "ECR",
            "ImageConfiguration": {
                "Port": "8080"
            }
        }
    }' \
    --instance-configuration '{
        "Cpu": "0.25 vCPU",
        "Memory": "0.5 GB"
    }' \
    --health-check-configuration '{
        "Protocol": "HTTP",
        "Path": "/health",
        "Interval": 20,
        "Timeout": 5,
        "HealthyThreshold": 1,
        "UnhealthyThreshold": 3
    }' \
    --region $AWS_REGION
```

---

## Step 7 – Update Backend CORS with Frontend URL

Once the frontend is deployed, update the backend's `CORS_ORIGINS` env var:

```bash
aws apprunner update-service \
    --service-arn <BACKEND_SERVICE_ARN> \
    --source-configuration '{
        "ImageRepository": {
            "ImageIdentifier": "'$AWS_ACCOUNT'.dkr.ecr.'$AWS_REGION'.amazonaws.com/bluetide/backend:latest",
            "ImageRepositoryType": "ECR",
            "ImageConfiguration": {
                "Port": "8000",
                "RuntimeEnvironmentVariables": {
                    "CORS_ORIGINS": "https://<FRONTEND_APPRUNNER_URL>"
                }
            }
        }
    }' \
    --region $AWS_REGION
```

---

## Step 8 – Firebase Allowed Domains

Add the App Runner frontend URL to Firebase Authentication → Settings → Authorized domains:
- `<random>.awsapprunner.com`

---

## Environment Variables Reference

### Backend

| Variable | Required | Description |
|---|---|---|
| `PORT` | ✅ | `8000` |
| `WORKERS` | | Number of uvicorn workers (default `2`) |
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `NEON_CONNECTION_STRING` | ✅ | Postgres connection string |
| `GEMINI_API_KEY` | ✅ | Google Gemini key for Docling extraction |
| `AWS_REGION` | ✅ | AWS region (e.g., `ap-south-1`) |
| `AWS_S3_BUCKET_NAME` | ✅ | S3 bucket name |
| `AWS_ACCESS_KEY_ID` | | Not needed if using instance role |
| `AWS_SECRET_ACCESS_KEY` | | Not needed if using instance role |
| `FIREBASE_SERVICE_ACCOUNT_B64` | ✅ | Base64-encoded Firebase SA JSON |
| `CORS_ORIGINS` | ✅ | Frontend URL (comma-separated) |
| `TOKEN_ENCRYPTION_KEY` | ✅ | Fernet key for OAuth token encryption |
| `EXTRACTION_BACKEND` | | `docling` (default) or `azure` |
| `SHAREPOINT_TENANT_ID` | | SharePoint app-only auth |
| `SHAREPOINT_CLIENT_ID` | | SharePoint app-only auth |
| `SHAREPOINT_CLIENT_SECRET` | | SharePoint app-only auth |
| `GDRIVE_OAUTH_CLIENT_ID` | | Google Drive OAuth |
| `GDRIVE_OAUTH_CLIENT_SECRET` | | Google Drive OAuth |
| `RUN_MIGRATIONS` | | Set to `true` to run Alembic on startup |

### Frontend (Build Args)

| Variable | Description |
|---|---|
| `VITE_API_URL` | Backend API URL (e.g., `https://api.bluetide.example.com/api/v1`) |
| `VITE_FIREBASE_API_KEY` | Firebase Web API key |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `VITE_FIREBASE_PROJECT_ID` | Firebase project ID |
| `VITE_FIREBASE_STORAGE_BUCKET` | Firebase storage bucket |
| `VITE_FIREBASE_APP_ID` | Firebase app ID |

---

## Updating the Application

### Push a new Backend version

```bash
cd backend
docker build --platform linux/amd64 -t bluetide-backend .
docker tag bluetide-backend:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/backend:latest

# Trigger redeployment
aws apprunner start-deployment --service-arn <BACKEND_SERVICE_ARN> --region $AWS_REGION
```

### Push a new Frontend version

```bash
cd bluetide-ui
docker build --platform linux/amd64 \
    --build-arg VITE_API_URL=https://<BACKEND_URL>/api/v1 \
    --build-arg VITE_FIREBASE_API_KEY=... \
    -t bluetide-frontend .
docker tag bluetide-frontend:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/frontend:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/bluetide/frontend:latest

aws apprunner start-deployment --service-arn <FRONTEND_SERVICE_ARN> --region $AWS_REGION
```

---

## Quick Deploy Script

A helper script `ex-apprunner/deploy-apprunner.sh` is provided in this archive:

```bash
# Deploy backend only
./ex-apprunner/deploy-apprunner.sh backend

# Deploy frontend only
./ex-apprunner/deploy-apprunner.sh frontend

# Deploy both
./ex-apprunner/deploy-apprunner.sh all
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `CORS error` in browser | Add frontend URL to `CORS_ORIGINS` env var on backend |
| Firebase auth fails | Add `*.awsapprunner.com` to Firebase authorized domains |
| S3 access denied | Attach `AmazonS3FullAccess` to instance role |
| Health check failing | Check `/api/v1/health` or `/health` endpoints |
| `docling` crash (OOM) | Increase memory to `3 GB` or `4 GB` |
| Slow cold start | App Runner may take 30-60s on first request after idle |
