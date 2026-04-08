#!/usr/bin/env node
/**
 * Generate QR Token Script
 * 
 * Creates a registration token directly in Firestore for testing
 * Run this on your local machine with Firebase Admin SDK access
 * 
 * Usage:
 *   node scripts/generate_qr_token.js --site global-innovation-anaheim-001 --org global-innovation
 */

const admin = require('firebase-admin');
const crypto = require('crypto');

// Initialize Firebase Admin (uses GOOGLE_APPLICATION_CREDENTIALS env var)
if (!admin.apps.length) {
    admin.initializeApp({
        projectId: 'aiodcounter06'
    });
}

const db = admin.firestore();

async function generateToken(siteId, orgId, options = {}) {
    const token = crypto.randomBytes(32).toString('hex');
    const expiresAt = new Date();
    expiresAt.setHours(expiresAt.getHours() + (options.validHours || 24));

    const tokenData = {
        token,
        site_id: siteId,
        org_id: orgId,
        created_at: admin.firestore.FieldValue.serverTimestamp(),
        expires_at: admin.firestore.Timestamp.fromDate(expiresAt),
        used: false,
        used_by: null,
        max_uses: options.maxUses || 10,
        use_count: 0
    };

    await db.collection('site_tokens').doc(token).set(tokenData);

    console.log('\n========================================');
    console.log('  QR REGISTRATION TOKEN GENERATED');
    console.log('========================================\n');
    console.log(`Site ID:    ${siteId}`);
    console.log(`Org ID:     ${orgId}`);
    console.log(`Token:      ${token}`);
    console.log(`Expires:    ${expiresAt.toISOString()}`);
    console.log(`Max Uses:   ${options.maxUses || 10}`);
    console.log('\n========================================\n');

    // Generate QR payload JSON for RPi
    const qrPayload = {
        backend_url: 'https://us-central1-aiodcounter06.cloudfunctions.net/api',
        token: token,
        site_id: siteId,
        org_id: orgId
    };

    console.log('📋 QR Payload (copy to config/qr_payload.json on RPi):');
    console.log(JSON.stringify(qrPayload, null, 2));

    console.log('\n📱 Or run on RPi:');
    console.log(`python3 tests/test_handshake.py --token ${token} --test-data`);

    return token;
}

// Parse command line arguments
const args = process.argv.slice(2);
let siteId = 'global-innovation-anaheim-001';
let orgId = 'global-innovation';
let validHours = 24;
let maxUses = 10;

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--site' && args[i + 1]) {
        siteId = args[++i];
    } else if (args[i] === '--org' && args[i + 1]) {
        orgId = args[++i];
    } else if (args[i] === '--hours' && args[i + 1]) {
        validHours = parseInt(args[++i]);
    } else if (args[i] === '--uses' && args[i + 1]) {
        maxUses = parseInt(args[++i]);
    } else if (args[i] === '--help') {
        console.log('Usage: node scripts/generate_qr_token.js [options]');
        console.log('');
        console.log('Options:');
        console.log('  --site  <site_id>   Site ID (default: global-innovation-anaheim-001)');
        console.log('  --org   <org_id>    Organization ID (default: global-innovation)');
        console.log('  --hours <hours>     Token validity in hours (default: 24)');
        console.log('  --uses  <count>     Max uses for token (default: 10)');
        process.exit(0);
    }
}

generateToken(siteId, orgId, { validHours, maxUses })
    .then(() => {
        console.log('\n✅ Token saved to Firestore');
        process.exit(0);
    })
    .catch(err => {
        console.error('❌ Error:', err.message);
        process.exit(1);
    });
