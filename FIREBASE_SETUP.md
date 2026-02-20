# Firebase Setup and Deployment Guide

## Overview

This project integrates Firebase Authentication and Firestore for multi-tenant user management.

## Architecture

- **Frontend**: Firebase SDK for authentication
- **Backend**: Firebase Admin SDK for user management and token verification
- **Cloud Functions**: Auth triggers for automatic user provisioning

## Setup Instructions

### 1. Firebase Project Setup

1. Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Authentication (Email/Password provider)
3. Create a Firestore database
4. Download service account key: Project Settings → Service Accounts → Generate New Private Key

### 2. Frontend Configuration

Add these environment variables to `bluetide-ui/.env`:

```env
VITE_FIREBASE_API_KEY=your_api_key
VITE_FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your_project_id
VITE_FIREBASE_STORAGE_BUCKET=your_project.appspot.com
VITE_FIREBASE_APP_ID=your_app_id
```

Get these values from: Firebase Console → Project Settings → General → Your apps

Install dependencies:
```bash
cd bluetide-ui
npm install
```

### 3. Backend Configuration

Add to `backend/.env`:

```env
FIREBASE_SERVICE_ACCOUNT_KEY_PATH=/path/to/your-service-account-key.json
```

Install dependencies:
```bash
cd backend
pip install -e .
```

### 4. Cloud Functions Deployment

1. Install Firebase CLI:
```bash
npm install -g firebase-tools
```

2. Login to Firebase:
```bash
firebase login
```

3. Update `.firebaserc` with your project ID:
```json
{
  "projects": {
    "default": "your-project-id"
  }
}
```

4. Install function dependencies:
```bash
cd functions
npm install
```

5. Deploy functions:
```bash
firebase deploy --only functions
```

### 5. Create Initial Admin User

**IMPORTANT**: Run this AFTER deploying Cloud Functions and creating your first user.

```bash
# First, create a user via Firebase Auth (Console or your app signup)
# Then run:
cd backend
python scripts/seed_admin.py --email admin@example.com
```

Or using UID:
```bash
python scripts/seed_admin.py --uid abc123def456
```

## Deployment Order

1. ✅ Create Firebase project and enable services
2. ✅ Configure environment variables (frontend + backend)
3. ✅ Deploy Cloud Functions (`firebase deploy --only functions`)
4. ✅ Create first user account via signup
5. ✅ Run seed script to promote user to admin
6. ✅ Admin can now manage all users from UI

## User Roles & Permissions

### Roles
- `user`: Basic access (clearance_level: 0)
- `org_admin`: Organization admin (clearance_level: 3)

### Custom Claims
Each authenticated user has JWT claims:
```json
{
  "tenant_id": "default-tenant",
  "role": "user" | "org_admin",
  "clearance_level": 0-3
}
```

## Firestore Structure

```
tenants/
  {tenant_id}/
    users/
      {uid}/
        - email: string
        - display_name: string
        - role: "user" | "org_admin"
        - clearance_level: number (0-3)
        - allowed_category_ids: string[]
        - is_active: boolean
        - created_at: timestamp
        - updated_at: timestamp
```

## Testing

Test the Cloud Function locally:
```bash
cd functions
npm run serve
```

Then create a test user via Firebase Auth Console and watch the logs.

## Troubleshooting

### Function not triggering
- Check Cloud Functions logs: `firebase functions:log`
- Verify function is deployed: `firebase functions:list`

### Permission errors
- Ensure service account has proper roles (Firebase Admin)
- Check that `.env` paths are correct

### Custom claims not working
- Claims take effect on next token refresh
- Force logout/login to get new token
- Check token in browser DevTools: `firebase.auth().currentUser.getIdTokenResult()`

## Security Rules

Add Firestore security rules to restrict access:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /tenants/{tenantId}/users/{userId} {
      allow read: if request.auth != null 
                  && request.auth.token.tenant_id == tenantId;
      allow write: if request.auth != null 
                   && request.auth.token.tenant_id == tenantId
                   && request.auth.token.role == 'org_admin';
    }
  }
}
```

Deploy rules:
```bash
firebase deploy --only firestore:rules
```
