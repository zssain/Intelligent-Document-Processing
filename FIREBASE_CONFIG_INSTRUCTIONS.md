# Firebase Configuration Setup Instructions

## ⚠️ IMPORTANT: Firebase Web App Configuration Required

The application is currently showing an error because the Firebase web app configuration is missing from the `.env` file.

## Quick Fix (2 minutes)

### Step 1: Get Firebase Web App Config

Go to the [Firebase Console](https://console.firebase.google.com/project/advanced-idp/settings/general) and:

1. Scroll down to **"Your apps"** section
2. Look for a web app (icon: **</>**)
3. If no web app exists:
   - Click **"Add app"** button
   - Select **Web** platform (</> icon)
   - Register with nickname: `bluetide-web`
   - **Do NOT** select "Also set up Firebase Hosting"
   - Click "Register app"

4. You'll see a code snippet like this:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
  authDomain: "advanced-idp.firebaseapp.com",
  projectId: "advanced-idp",
  storageBucket: "advanced-idp.appspot.com",
  appId: "1:XXXXXXXXXXXX:web:XXXXXXXXXXXXXXXX"
};
```

### Step 2: Update .env File

Edit `bluetide-ui/.env` and replace the placeholder values:

```bash
# Replace this line:
VITE_FIREBASE_API_KEY=REPLACE_WITH_YOUR_FIREBASE_API_KEY

# With your actual API key from above:
VITE_FIREBASE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

# Replace this line:
VITE_FIREBASE_APP_ID=REPLACE_WITH_YOUR_FIREBASE_APP_ID

# With your actual App ID from above:
VITE_FIREBASE_APP_ID=1:XXXXXXXXXXXX:web:XXXXXXXXXXXXXXXX
```

The other values (authDomain, projectId, storageBucket) should already be correct:
- `VITE_FIREBASE_AUTH_DOMAIN=advanced-idp.firebaseapp.com` ✓
- `VITE_FIREBASE_PROJECT_ID=advanced-idp` ✓  
- `VITE_FIREBASE_STORAGE_BUCKET=advanced-idp.appspot.com` ✓

### Step 3: Restart Dev Server

After updating `.env`:

```bash
cd bluetide-ui
npm run dev
```

The app should now load without errors!

## Alternative: Using Firebase CLI

If you prefer using the command line:

```bash
# Install Firebase CLI (if not installed)
npm install -g firebase-tools

# Login to Firebase
firebase login

# List all apps
firebase apps:list --project advanced-idp

# Get web app config (replace WEB_APP_ID with ID from list above)
firebase apps:sdkconfig WEB <WEB_APP_ID>
```

## Current .env File Status

Your `.env` file currently has:
- ✅ API URL configured
- ✅ Firebase project ID, auth domain, storage bucket (correct defaults)
- ❌ Firebase API key (placeholder - **NEEDS REPLACEMENT**)
- ❌ Firebase App ID (placeholder - **NEEDS REPLACEMENT**)

## Error Details

**Current Error:**
```
Uncaught FirebaseError: Firebase: Error (auth/invalid-api-key).
```

**Cause:** The `VITE_FIREBASE_API_KEY` is set to placeholder value `REPLACE_WITH_YOUR_FIREBASE_API_KEY` instead of an actual Firebase Web API key.

**Solution:** Follow Step 1 & 2 above to get and update the actual values.

## Test Users (After Fix)

Once configured, you can test with these accounts:

- **Admin Account:**
  - Email: `admin@teclusion.ai`
  - Password: `qwerty123`
  - Role: org_admin
  - Clearance: 3

- **User Account:**
  - Email: `user@teclusion.ai`
  - Password: `qwerty123`
  - Role: user
  - Clearance: 1
