# Firebase Quick Reference

## 🔧 Development Commands

### Cloud Functions
```bash
# Deploy functions
firebase deploy --only functions

# View logs
firebase functions:log

# Run locally
cd functions && npm run serve
```

### Firestore Rules
```bash
# Deploy security rules
firebase deploy --only firestore:rules
```

### Admin Management
```bash
# Promote user to admin
cd backend
python scripts/seed_admin.py --email admin@example.com

# Or by UID
python scripts/seed_admin.py --uid abc123def456
```

## 📝 Code Snippets

### Frontend - Auth
```typescript
import { auth } from '@/shared/lib/firebase';
import { 
  createUserWithEmailAndPassword,
  signInWithEmailAndPassword,
  signOut
} from 'firebase/auth';

// Sign up
await createUserWithEmailAndPassword(auth, email, password);

// Sign in
await signInWithEmailAndPassword(auth, email, password);

// Sign out
await signOut(auth);

// Get current user
const user = auth.currentUser;

// Get custom claims
const idToken = await user?.getIdTokenResult();
console.log(idToken?.claims.role); // 'user' or 'org_admin'
console.log(idToken?.claims.clearance_level); // 0-3
console.log(idToken?.claims.tenant_id); // 'default-tenant'
```

### Frontend - Firestore
```typescript
import { firestore } from '@/shared/lib/firebase';
import { doc, getDoc, collection, query, where, getDocs } from 'firebase/firestore';

// Get user document
const userRef = doc(firestore, 'tenants/default-tenant/users', userId);
const userDoc = await getDoc(userRef);
const userData = userDoc.data();

// Query documents
const q = query(
  collection(firestore, 'tenants/default-tenant/documents'),
  where('category_id', '==', 'category-123')
);
const snapshot = await getDocs(q);
snapshot.forEach(doc => console.log(doc.data()));
```

### Backend - Token Verification
```python
from src.utils.firebase import auth
from fastapi import HTTPException, Header

async def verify_firebase_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing or invalid token")
    
    token = authorization.split('Bearer ')[1]
    try:
        decoded = auth.verify_id_token(token)
        return {
            'uid': decoded['uid'],
            'email': decoded.get('email'),
            'role': decoded.get('role', 'user'),
            'clearance_level': decoded.get('clearance_level', 0),
            'tenant_id': decoded.get('tenant_id')
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

# Use in route
@router.get("/protected")
async def protected_route(user = Depends(verify_firebase_token)):
    return {"message": f"Hello {user['email']}, role: {user['role']}"}
```

### Backend - Firestore Operations
```python
from src.utils.firebase import firestore_client
from config.settings import DEFAULT_TENANT_ID

# Get user document
user_ref = (
    firestore_client
    .collection('tenants')
    .document(DEFAULT_TENANT_ID)
    .collection('users')
    .document(uid)
)
user_doc = user_ref.get()
if user_doc.exists:
    user_data = user_doc.to_dict()

# Update user
user_ref.update({
    'last_login': firestore.SERVER_TIMESTAMP,
    'is_active': True
})

# Query users
users_ref = (
    firestore_client
    .collection('tenants')
    .document(DEFAULT_TENANT_ID)
    .collection('users')
)
query = users_ref.where('role', '==', 'org_admin')
docs = query.stream()
for doc in docs:
    print(f'{doc.id}: {doc.to_dict()}')
```

## 🗂️ Firestore Data Structure

```
tenants/
  {tenant_id}/              # e.g., 'default-tenant'
    users/
      {uid}/
        email: string
        display_name: string
        role: 'user' | 'org_admin'
        clearance_level: 0 | 1 | 2 | 3
        allowed_category_ids: string[]
        is_active: boolean
        created_at: timestamp
        updated_at: timestamp
    
    documents/              # Your documents collection
      {doc_id}/
        title: string
        category_id: string
        clearance_level: number
        ...
    
    categories/             # Document categories
      {category_id}/
        name: string
        description: string
        ...
```

## 🔑 Custom Claims Structure

```json
{
  "tenant_id": "default-tenant",
  "role": "user" | "org_admin",
  "clearance_level": 0-3
}
```

## 🛡️ Role Permissions

| Role | Level | Can Do |
|------|-------|--------|
| `user` | 0 | Read own documents, limited access |
| `org_admin` | 3 | Full access, manage users, all documents |

## 🚨 Common Issues

### Token expired
```typescript
// Force token refresh
await auth.currentUser?.getIdToken(true);
```

### Claims not updated
```typescript
// Sign out and sign in again to get new token
await signOut(auth);
await signInWithEmailAndPassword(auth, email, password);
```

### Backend can't find settings
```python
# Run from backend directory
cd backend
python scripts/seed_admin.py --email user@example.com
```

## 📚 Documentation Files

- [FIREBASE_README.md](FIREBASE_README.md) - Overview
- [FIREBASE_SETUP.md](FIREBASE_SETUP.md) - Complete setup guide
- [FIREBASE_DEPLOYMENT_CHECKLIST.md](FIREBASE_DEPLOYMENT_CHECKLIST.md) - Deployment checklist
- [FIREBASE_IMPLEMENTATION_SUMMARY.md](FIREBASE_IMPLEMENTATION_SUMMARY.md) - Technical details

## 🔗 External Resources

- [Firebase Docs](https://firebase.google.com/docs)
- [Firebase Auth](https://firebase.google.com/docs/auth)
- [Firestore](https://firebase.google.com/docs/firestore)
- [Cloud Functions](https://firebase.google.com/docs/functions)
- [Security Rules](https://firebase.google.com/docs/firestore/security/get-started)
