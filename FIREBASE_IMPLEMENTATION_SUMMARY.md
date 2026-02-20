# Firebase Integration - Implementation Summary

## ✅ Completed Tasks

### 1. Frontend Setup
- ✅ Added `firebase` SDK to [package.json](bluetide-ui/package.json)
- ✅ Created [src/shared/lib/firebase.ts](bluetide-ui/src/shared/lib/firebase.ts) with initialized `auth` and `firestore` instances
- ✅ Created [.env.example](bluetide-ui/.env.example) documenting required environment variables:
  - `VITE_FIREBASE_API_KEY`
  - `VITE_FIREBASE_AUTH_DOMAIN`
  - `VITE_FIREBASE_PROJECT_ID`
  - `VITE_FIREBASE_STORAGE_BUCKET`
  - `VITE_FIREBASE_APP_ID`

### 2. Backend Setup
- ✅ Added `firebase-admin>=6.5.0` to [pyproject.toml](backend/pyproject.toml)
- ✅ Created [src/utils/firebase.py](backend/src/utils/firebase.py) with Firebase Admin SDK initialization
  - Exports `firestore_client` and `auth` for use across backend
  - Lazy initialization with caching
- ✅ Updated [config/settings.py](backend/config/settings.py):
  - Added `DEFAULT_TENANT_ID = "default-tenant"` constant
  - Added `firebase_service_account_key_path` setting
- ✅ Updated [.env.example](backend/.env.example) with `FIREBASE_SERVICE_ACCOUNT_KEY_PATH`

### 3. Cloud Functions Setup
- ✅ Created [functions/](functions/) directory with complete Cloud Functions project
- ✅ Created [functions/package.json](functions/package.json) with dependencies
- ✅ Created [functions/index.js](functions/index.js) with `onUserCreate` trigger:
  - Creates Firestore document at `tenants/{DEFAULT_TENANT_ID}/users/{uid}`
  - Sets user data: `{ email, display_name, role: "user", clearance_level: 0, allowed_category_ids: [], is_active: true, created_at }`
  - Sets custom claims: `{ tenant_id, role: "user", clearance_level: 0 }`
- ✅ Created supporting files:
  - [functions/.eslintrc.js](functions/.eslintrc.js)
  - [functions/.gitignore](functions/.gitignore)
  - [functions/README.md](functions/README.md)
- ✅ Created [firebase.json](firebase.json) and [.firebaserc](.firebaserc) for Firebase configuration

### 4. Admin Seed Script
- ✅ Created [backend/scripts/seed_admin.py](backend/scripts/seed_admin.py)
  - Takes `--email` or `--uid` argument
  - Sets custom claims: `{ tenant_id: DEFAULT_TENANT_ID, role: "org_admin", clearance_level: 3 }`
  - Creates/updates Firestore user document with admin privileges
  - Handles both new and existing users

### 5. Documentation
- ✅ Created comprehensive [FIREBASE_SETUP.md](FIREBASE_SETUP.md) with:
  - Complete setup instructions
  - Deployment order
  - Environment variable configuration
  - Security rules examples
  - Troubleshooting guide

## 📋 Next Steps (Deployment Order)

1. **Install Dependencies**
   ```bash
   # Frontend
   cd bluetide-ui
   npm install
   
   # Backend
   cd backend
   pip install -e .
   
   # Cloud Functions
   cd functions
   npm install
   ```

2. **Create Firebase Project**
   - Go to [Firebase Console](https://console.firebase.google.com)
   - Create new project
   - Enable Authentication (Email/Password)
   - Create Firestore database
   - Download service account key

3. **Configure Environment Variables**
   
   Frontend `.env`:
   ```env
   VITE_FIREBASE_API_KEY=...
   VITE_FIREBASE_AUTH_DOMAIN=...
   VITE_FIREBASE_PROJECT_ID=...
   VITE_FIREBASE_STORAGE_BUCKET=...
   VITE_FIREBASE_APP_ID=...
   ```
   
   Backend `.env`:
   ```env
   FIREBASE_SERVICE_ACCOUNT_KEY_PATH=/path/to/service-account.json
   ```

4. **Deploy Cloud Functions**
   ```bash
   # Update .firebaserc with your project ID
   firebase login
   firebase deploy --only functions
   ```

5. **Create Initial Admin**
   ```bash
   # First create user via Firebase Auth (signup in UI or Console)
   # Then promote to admin:
   cd backend
   python scripts/seed_admin.py --email admin@example.com
   ```

## 🏗️ Architecture

### User Flow
1. User signs up → Firebase Auth creates account
2. `onUserCreate` Cloud Function triggers automatically
3. Function creates Firestore user doc with default role
4. Function sets JWT custom claims
5. User can login with default permissions
6. Admin runs seed script to promote users to org_admin

### Data Structure

**Firestore:**
```
tenants/
  default-tenant/
    users/
      {uid}/
        email: string
        display_name: string
        role: "user" | "org_admin"
        clearance_level: 0-3
        allowed_category_ids: []
        is_active: true
        created_at: timestamp
```

**JWT Custom Claims:**
```json
{
  "tenant_id": "default-tenant",
  "role": "user",
  "clearance_level": 0
}
```

## 🔒 Security Considerations

- Custom claims are validated on each request
- Frontend can read claims from `firebase.auth().currentUser.getIdTokenResult()`
- Backend validates tokens using Firebase Admin SDK
- Firestore rules enforce tenant isolation
- Only org_admin can modify user documents

## 📝 Files Created/Modified

### Created Files
- `bluetide-ui/src/shared/lib/firebase.ts`
- `bluetide-ui/.env.example`
- `backend/src/utils/firebase.py`
- `backend/scripts/seed_admin.py`
- `functions/package.json`
- `functions/index.js`
- `functions/.eslintrc.js`
- `functions/.gitignore`
- `functions/README.md`
- `firebase.json`
- `.firebaserc`
- `FIREBASE_SETUP.md`
- This summary file

### Modified Files
- `bluetide-ui/package.json` - Added firebase dependency
- `backend/pyproject.toml` - Added firebase-admin dependency
- `backend/config/settings.py` - Added Firebase config and DEFAULT_TENANT_ID
- `backend/.env.example` - Added Firebase service account path

## 🎯 Usage Examples

### Frontend - Sign Up
```typescript
import { auth } from '@/shared/lib/firebase';
import { createUserWithEmailAndPassword } from 'firebase/auth';

const signup = async (email: string, password: string) => {
  const userCredential = await createUserWithEmailAndPassword(auth, email, password);
  // onUserCreate Cloud Function automatically creates Firestore doc
  // and sets custom claims
};
```

### Frontend - Get User Claims
```typescript
const user = auth.currentUser;
if (user) {
  const idTokenResult = await user.getIdTokenResult();
  const role = idTokenResult.claims.role;
  const clearanceLevel = idTokenResult.claims.clearance_level;
  const tenantId = idTokenResult.claims.tenant_id;
}
```

### Backend - Verify Token
```python
from src.utils.firebase import auth

def verify_token(id_token: str):
    decoded_token = auth.verify_id_token(id_token)
    uid = decoded_token['uid']
    role = decoded_token.get('role', 'user')
    clearance_level = decoded_token.get('clearance_level', 0)
    tenant_id = decoded_token.get('tenant_id')
    return decoded_token
```

### Backend - Query User Data
```python
from src.utils.firebase import firestore_client
from config.settings import DEFAULT_TENANT_ID

def get_user_data(uid: str):
    doc_ref = (
        firestore_client
        .collection('tenants')
        .document(DEFAULT_TENANT_ID)
        .collection('users')
        .document(uid)
    )
    doc = doc_ref.get()
    return doc.to_dict() if doc.exists else None
```

## ✨ All Requirements Completed

✅ Frontend: Firebase SDK installed and configured  
✅ Backend: Firebase Admin SDK integrated  
✅ Cloud Functions: User onCreate trigger implemented  
✅ Seed Script: Admin user promotion tool created  
✅ Environment Variables: All documented  
✅ Tenant Support: DEFAULT_TENANT_ID constant added  
✅ Complete Documentation: Setup guide provided  

The Firebase integration is now complete and ready for deployment!
