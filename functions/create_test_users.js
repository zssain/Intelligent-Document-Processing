#!/usr/bin/env node
/**
 * Script to create test users in Firebase Authentication
 * 
 * Usage: node create_test_users.js
 */

const admin = require('firebase-admin');
const path = require('path');

// Initialize Firebase Admin SDK
const serviceAccount = require('../advanced-idp-firebase-adminsdk-fbsvc-088b57c35c.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});

const DEFAULT_TENANT_ID = 'default-tenant';

const TEST_USERS = [
  {
    email: 'admin@teclusion.ai',
    password: 'qwerty123',
    role: 'org_admin',
    clearance_level: 3,
    display_name: 'Admin User',
  },
  {
    email: 'user@teclusion.ai',
    password: 'qwerty123',
    role: 'user',
    clearance_level: 1,
    display_name: 'Regular User',
  },
];

async function createUser(userData) {
  const { email, password, role, clearance_level, display_name } = userData;

  try {
    console.log(`\n🔄 Processing ${email}...`);

    // Check if user already exists
    let user;
    try {
      user = await admin.auth().getUserByEmail(email);
      console.log(`   User already exists with UID: ${user.uid}`);
      
      // Update password
      await admin.auth().updateUser(user.uid, { password });
      console.log(`   ✓ Password updated`);
    } catch (error) {
      if (error.code === 'auth/user-not-found') {
        // Create new user
        user = await admin.auth().createUser({
          email,
          password,
          displayName: display_name,
          emailVerified: true,
        });
        console.log(`   ✓ User created with UID: ${user.uid}`);
      } else {
        throw error;
      }
    }

    // Set custom claims
    const customClaims = {
      tenant_id: DEFAULT_TENANT_ID,
      role,
      clearance_level,
    };

    await admin.auth().setCustomUserClaims(user.uid, customClaims);
    console.log(`   ✓ Custom claims set:`, customClaims);

    // Create/update Firestore user document
    const userDocRef = admin.firestore()
      .collection('tenants')
      .doc(DEFAULT_TENANT_ID)
      .collection('users')
      .doc(user.uid);

    const firestoreData = {
      email: email,
      display_name: display_name,
      role,
      clearance_level,
      allowed_category_ids: role === 'org_admin' ? [] : ['general'],
      is_active: true,
      updated_at: admin.firestore.FieldValue.serverTimestamp(),
    };

    const doc = await userDocRef.get();
    if (doc.exists) {
      await userDocRef.update(firestoreData);
      console.log(`   ✓ Firestore document updated`);
    } else {
      firestoreData.created_at = admin.firestore.FieldValue.serverTimestamp();
      await userDocRef.set(firestoreData);
      console.log(`   ✓ Firestore document created`);
    }

    console.log(`   ✅ ${email} ready!`);
    console.log(`      Role: ${role}`);
    console.log(`      Clearance: ${clearance_level}`);
    console.log(`      Password: ${password}`);

  } catch (error) {
    console.error(`   ❌ Error creating ${email}:`, error.message);
    throw error;
  }
}

async function main() {
  console.log('🚀 Creating test users in Firebase...\n');
  console.log(`Tenant ID: ${DEFAULT_TENANT_ID}`);

  try {
    for (const userData of TEST_USERS) {
      await createUser(userData);
    }

    console.log('\n✅ All test users created successfully!\n');
    console.log('You can now sign in with:');
    console.log('  • admin@teclusion.ai / qwerty123 (Admin)');
    console.log('  • user@teclusion.ai / qwerty123 (Regular User)\n');

  } catch (error) {
    console.error('\n❌ Failed to create test users:', error);
    process.exit(1);
  } finally {
    process.exit(0);
  }
}

main();
