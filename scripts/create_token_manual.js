#!/usr/bin/env node
/**
 * Create token using Firebase REST API
 * Uses the signed-in Firebase CLI credentials
 */

const { execSync } = require('child_process');
const https = require('https');

const token = 'c7979e050518223bedea817d510ac48819b98a9b90efc633ed586da956534ea1';
const projectId = 'aiodcounter06';

// Get access token from firebase CLI
function getAccessToken() {
    try {
        // Use firebase-tools to get token
        const result = execSync('npx firebase-tools login:ci --no-localhost 2>&1 || true', { encoding: 'utf8' });
        console.log('Note: Using firebase login session');

        // Alternative: use gcloud
        const gcloudToken = execSync('gcloud auth print-access-token 2>/dev/null || echo ""', { encoding: 'utf8' }).trim();
        if (gcloudToken) {
            return gcloudToken;
        }

        return null;
    } catch (e) {
        return null;
    }
}

// Calculate expiration (48 hours)
const expiresAt = new Date();
expiresAt.setHours(expiresAt.getHours() + 48);

const documentData = {
    fields: {
        token: { stringValue: token },
        site_id: { stringValue: 'global-innovation-anaheim-001' },
        org_id: { stringValue: 'global-innovation' },
        used: { booleanValue: false },
        max_uses: { integerValue: '10' },
        use_count: { integerValue: '0' },
        expires_at: { timestampValue: expiresAt.toISOString() }
    }
};

console.log('Token to create:', token);
console.log('Document data:', JSON.stringify(documentData, null, 2));

console.log(`
========================================
  MANUAL STEPS TO CREATE TOKEN
========================================

Since we need authentication, please create the token manually:

Option 1: Firebase Console (Recommended)
----------------------------------------
1. Open: https://console.firebase.google.com/project/aiodcounter06/firestore
2. Click "Start collection" or navigate to existing collection
3. Collection ID: site_tokens
4. Document ID: ${token}
5. Add these fields:
   - token (string): ${token}
   - site_id (string): global-innovation-anaheim-001
   - org_id (string): global-innovation
   - used (boolean): false
   - max_uses (number): 10
   - use_count (number): 0
   - expires_at (timestamp): ${expiresAt.toISOString()}

Option 2: Firebase Emulator
---------------------------
firebase emulators:start --only firestore
# Then use the Emulator UI to create the document

========================================
  QR PAYLOAD (Already saved)
========================================

cat config/qr_payload.json

========================================
  TEST ON RPI
========================================

# Copy the files to RPi:
scp -r . pi@<rpi-ip>:~/aiodcounter01/

# Run the handshake test:
python3 tests/test_handshake.py --token ${token} --test-data

`);
