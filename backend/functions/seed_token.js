#!/usr/bin/env node
/**
 * Seed Token Script - Creates a test token in Firestore
 * 
 * Run from the backend/functions directory where firebase-admin is available:
 *   cd backend/functions && node seed_token.js
 */

const admin = require('firebase-admin');

// Initialize with project ID (will use ADC or emulator)
if (!admin.apps.length) {
    admin.initializeApp({
        projectId: 'aiodcounter06'
    });
}

const db = admin.firestore();

const token = process.argv[2] || 'c7979e050518223bedea817d510ac48819b98a9b90efc633ed586da956534ea1';
const siteId = 'global-innovation-anaheim-001';
const orgId = 'global-innovation';

const expiresAt = new Date();
expiresAt.setHours(expiresAt.getHours() + 48); // 48 hours validity

async function seedToken() {
    console.log('Creating token in Firestore...');
    console.log(`Token: ${token}`);

    try {
        await db.collection('site_tokens').doc(token).set({
            token: token,
            site_id: siteId,
            org_id: orgId,
            created_at: admin.firestore.FieldValue.serverTimestamp(),
            expires_at: admin.firestore.Timestamp.fromDate(expiresAt),
            used: false,
            used_by: null,
            max_uses: 10,
            use_count: 0
        });

        console.log('✅ Token created successfully!');
        console.log(`Expires: ${expiresAt.toISOString()}`);

        // Verify
        const doc = await db.collection('site_tokens').doc(token).get();
        console.log('Verification:', doc.exists ? 'OK' : 'FAILED');

    } catch (error) {
        console.error('❌ Error:', error.message);
    }

    process.exit(0);
}

seedToken();
