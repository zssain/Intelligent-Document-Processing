# Firebase Integration Deployment Checklist

Use this checklist to ensure proper deployment of Firebase integration.

## Pre-Deployment

- [ ] Firebase project created at [console.firebase.google.com](https://console.firebase.google.com)
- [ ] Firebase Authentication enabled (Email/Password provider)
- [ ] Firestore database created
- [ ] Service account JSON key downloaded from Firebase Console
- [ ] Firebase CLI installed: `npm install -g firebase-tools`
- [ ] Logged into Firebase CLI: `firebase login`

## Configuration

### Frontend (.env)
- [ ] `VITE_FIREBASE_API_KEY` set
- [ ] `VITE_FIREBASE_AUTH_DOMAIN` set
- [ ] `VITE_FIREBASE_PROJECT_ID` set
- [ ] `VITE_FIREBASE_STORAGE_BUCKET` set
- [ ] `VITE_FIREBASE_APP_ID` set

### Backend (.env)
- [ ] `FIREBASE_SERVICE_ACCOUNT_KEY_PATH` points to valid JSON file
- [ ] Service account JSON file placed in secure location
- [ ] Service account JSON file excluded from git (.gitignore)

### Firebase Config
- [ ] `.firebaserc` updated with correct project ID
- [ ] `firebase.json` configured (should be already set)

## Installation

- [ ] Frontend dependencies installed: `cd bluetide-ui && npm install`
- [ ] Backend dependencies installed: `cd backend && pip install -e .`
- [ ] Functions dependencies installed: `cd functions && npm install`

Or run: `./setup_firebase.sh`

## Cloud Functions Deployment

- [ ] Functions deployed: `firebase deploy --only functions`
- [ ] Deployment successful (check for errors)
- [ ] Functions visible in Firebase Console
- [ ] `onUserCreate` function listed and active

## Testing

- [ ] Create test user via Firebase Auth Console OR sign up via UI
- [ ] Check Firestore: user document created at `tenants/default-tenant/users/{uid}`
- [ ] Verify user document has correct fields:
  - [ ] `email`
  - [ ] `display_name`
  - [ ] `role: "user"`
  - [ ] `clearance_level: 0`
  - [ ] `is_active: true`
  - [ ] `created_at` timestamp
- [ ] Check custom claims in Firebase Auth Console user details
- [ ] Verify claims contain: `tenant_id`, `role`, `clearance_level`

## Admin User Setup

- [ ] First user created (can be test account)
- [ ] Seed script run: `cd backend && python scripts/seed_admin.py --email admin@example.com`
- [ ] Admin user promoted successfully
- [ ] Verify in Firestore: `role: "org_admin"`, `clearance_level: 3`
- [ ] Verify custom claims updated
- [ ] Test admin login and permissions

## Security (Optional but Recommended)

- [ ] Firestore security rules deployed
- [ ] Test rules with different user roles
- [ ] Verify tenant isolation works
- [ ] Verify only org_admin can write to user docs

Example rules deployment:
```bash
firebase deploy --only firestore:rules
```

## Monitoring

- [ ] Cloud Functions logs accessible: `firebase functions:log`
- [ ] No errors in function logs
- [ ] User creation triggering properly
- [ ] Firestore writes succeeding

## Production Checklist

- [ ] Environment variables set in production hosting platform
- [ ] Service account JSON securely stored (e.g., secrets manager)
- [ ] Firebase project billing enabled (if needed)
- [ ] Firebase quota limits reviewed
- [ ] Backup strategy in place for Firestore
- [ ] Monitoring/alerting configured
- [ ] Error tracking integrated

## Rollback Plan

If issues occur:
- [ ] Previous version tagged in git
- [ ] Can revert Cloud Functions: `firebase deploy --only functions` (from previous commit)
- [ ] Can disable functions in Firebase Console
- [ ] Database backup available
- [ ] Manual user creation process documented as fallback

## Success Criteria

✅ New users can sign up  
✅ User documents auto-created in Firestore  
✅ Custom claims set correctly  
✅ Admin can be promoted via seed script  
✅ Frontend can read user claims  
✅ Backend can verify tokens  
✅ No errors in Cloud Functions logs  

---

**Deployment Date:** _____________

**Deployed By:** _____________

**Notes:**
_______________________________________________________________________
_______________________________________________________________________
_______________________________________________________________________
