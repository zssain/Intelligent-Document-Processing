# Firebase Cloud Functions

This directory contains Firebase Cloud Functions for the BlueTide application.

## Setup

1. Install dependencies:
```bash
cd functions
npm install
```

2. Configure Firebase project:
```bash
firebase use --add
```

## Functions

### onUserCreate

Triggered when a new user signs up via Firebase Authentication.

**Actions:**
- Creates a Firestore user document at `tenants/{DEFAULT_TENANT_ID}/users/{uid}`
- Sets initial user data: role="user", clearance_level=0
- Sets custom JWT claims for authorization

## Development

Run functions locally:
```bash
npm run serve
```

## Deployment

Deploy functions to Firebase:
```bash
npm run deploy
```

View function logs:
```bash
npm run logs
```
