#!/usr/bin/env node
/**
 * Generate QR Token using Firebase Tools
 * 
 * This script uses firebase-tools (CLI) auth to create tokens
 * Make sure you're logged in with: firebase login
 * 
 * Usage:
 *   node scripts/generate_token_cli.js
 */

const { execSync } = require('child_process');
const crypto = require('crypto');
const fs = require('fs');

// Generate a secure token
const token = crypto.randomBytes(32).toString('hex');
const siteId = process.argv[2] || 'global-innovation-anaheim-001';
const orgId = process.argv[3] || 'global-innovation';

// Calculate expiration (24 hours from now)
const expiresAt = new Date();
expiresAt.setHours(expiresAt.getHours() + 24);

// Create the token document data
const tokenData = {
    token: token,
    site_id: siteId,
    org_id: orgId,
    created_at: { _seconds: Math.floor(Date.now() / 1000) },
    expires_at: { _seconds: Math.floor(expiresAt.getTime() / 1000) },
    used: false,
    used_by: null,
    max_uses: 10,
    use_count: 0
};

console.log('\n========================================');
console.log('  QR REGISTRATION TOKEN GENERATOR');
console.log('========================================\n');

console.log(`Token:      ${token}`);
console.log(`Site ID:    ${siteId}`);
console.log(`Org ID:     ${orgId}`);
console.log(`Expires:    ${expiresAt.toISOString()}`);
console.log(`Max Uses:   10`);

// Create QR payload
const qrPayload = {
    backend_url: 'https://us-central1-aiodcounter06.cloudfunctions.net/api',
    token: token,
    site_id: siteId,
    org_id: orgId
};

console.log('\n========================================');
console.log('  QR PAYLOAD (for RPi)');
console.log('========================================\n');
console.log(JSON.stringify(qrPayload, null, 2));

// Save QR payload to file for easy transfer
const payloadPath = 'config/qr_payload.json';
fs.writeFileSync(payloadPath, JSON.stringify(qrPayload, null, 4));
console.log(`\n✅ Saved QR payload to: ${payloadPath}`);

// Try to write token to Firestore using firebase CLI
console.log('\n========================================');
console.log('  FIRESTORE DOCUMENT');
console.log('========================================\n');
console.log('Document path: site_tokens/' + token);
console.log('Data:', JSON.stringify(tokenData, null, 2));

console.log('\n========================================');
console.log('  NEXT STEPS');
console.log('========================================\n');

console.log('1. Create the token in Firestore:');
console.log('   - Go to Firebase Console > Firestore');
console.log('   - Create collection "site_tokens" if not exists');
console.log('   - Add document with ID: ' + token);
console.log('   - Add fields as shown above');
console.log('');
console.log('2. Copy qr_payload.json to RPi:');
console.log(`   scp ${payloadPath} pi@<rpi-ip>:~/aiodcounter01/config/`);
console.log('');
console.log('3. Run handshake test on RPi:');
console.log(`   python3 tests/test_handshake.py --token ${token} --test-data`);
console.log('');
