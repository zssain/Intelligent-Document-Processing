#!/usr/bin/env node
/**
 * Script to verify test users and their claims
 */

const admin = require('firebase-admin');
const serviceAccount = require('../advanced-idp-firebase-adminsdk-fbsvc-bb28208c38.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount),
});

async function verifyUsers() {
  const emails = ['admin@teclusion.ai', 'user@teclusion.ai'];
  
  console.log('🔍 Verifying test users...\n');
  
  for (const email of emails) {
    try {
      const user = await admin.auth().getUserByEmail(email);
      
      console.log(`✅ ${email}`);
      console.log(`   UID: ${user.uid}`);
      console.log(`   Custom Claims:`, user.customClaims);
      console.log(`   Email Verified: ${user.emailVerified}`);
      
      // Check Firestore document
      const userDoc = await admin.firestore()
        .collection('tenants')
        .doc('default-tenant')
        .collection('users')
        .doc(user.uid)
        .get();
      
      if (userDoc.exists) {
        console.log(`   Firestore Data:`, userDoc.data());
      } else {
        console.log(`   ⚠️  No Firestore document found`);
      }
      console.log('');
      
    } catch (error) {
      console.error(`❌ Error verifying ${email}:`, error.message);
    }
  }
  
  process.exit(0);
}

verifyUsers();
