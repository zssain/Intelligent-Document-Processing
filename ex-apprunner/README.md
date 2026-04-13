# App Runner Archive

This folder contains the old App Runner deployment path that used:

- backend and frontend container images
- an Nginx frontend reverse proxy
- App Runner-specific deployment docs and helper scripts

The active deployment target for this repo is now:

- `Cloudflare Pages` for the frontend
- `AWS Lambda` for the backend API
- `AWS Lambda + SQS` for background ingestion jobs

Current deployment guide:

- [`DEPLOYMENT_CLOUDFLARE_LAMBDA.md`](/Users/zuhairhussain/Desktop/bluetide-B-5-2/DEPLOYMENT_CLOUDFLARE_LAMBDA.md)
