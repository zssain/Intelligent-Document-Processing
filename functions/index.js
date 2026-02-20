const functions = require('firebase-functions');
const admin = require('firebase-admin');

// Initialize Firebase Admin SDK
admin.initializeApp();

// Default tenant ID - should match backend settings.py DEFAULT_TENANT_ID
const DEFAULT_TENANT_ID = 'default-tenant';

/**
 * Cloud Function triggered when a new user is created.
 * Creates a user document in Firestore and sets custom claims.
 */
exports.onUserCreate = functions.auth.user().onCreate(async (user) => {
  const { uid, email, displayName } = user;

  console.log(`New user created: ${uid} (${email})`);

  try {
    // Create Firestore user document
    const userDocRef = admin.firestore()
      .collection('tenants')
      .doc(DEFAULT_TENANT_ID)
      .collection('users')
      .doc(uid);

    const userData = {
      email: email || '',
      display_name: displayName || '',
      role: 'user',
      clearance_level: 0,
      allowed_category_ids: [],
      is_active: true,
      created_at: admin.firestore.FieldValue.serverTimestamp(),
    };

    await userDocRef.set(userData);
    console.log(`Created Firestore document for user ${uid}`);

    // Set custom user claims
    const customClaims = {
      tenant_id: DEFAULT_TENANT_ID,
      role: 'user',
      clearance_level: 0,
    };

    await admin.auth().setCustomUserClaims(uid, customClaims);
    console.log(`Set custom claims for user ${uid}:`, customClaims);

    return {
      success: true,
      uid,
      message: `User ${email} initialized successfully`,
    };
  } catch (error) {
    console.error(`Error creating user ${uid}:`, error);
    throw new functions.https.HttpsError(
      'internal',
      'Failed to initialize user',
      error
    );
  }
});
