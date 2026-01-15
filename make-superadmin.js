const admin = require('firebase-admin');

// IMPORTANT: This script uses the active Firebase CLI project
// Make sure you have run 'firebase use aiodcounter06'
// and 'export GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account.json'
// OR just run this inside a directory with proper admin access.

if (process.argv.length < 3) {
    console.log('Usage: node make-superadmin.js <user_email_or_uid>');
    process.exit(1);
}

const target = process.argv[2];

// Initialize with default credentials (requires being logged in via CLI or service account env)
admin.initializeApp();

async function promote() {
    try {
        let user;
        if (target.includes('@')) {
            user = await admin.auth().getUserByEmail(target);
        } else {
            user = await admin.auth().getUser(target);
        }

        await admin.auth().setCustomUserClaims(user.uid, { role: 'superadmin' });
        console.log(`Successfully promoted ${user.email} (${user.uid}) to SuperAdmin.`);
        console.log('Please log out and log back in to the dashboard to see the changes.');
    } catch (error) {
        console.error('Error promoting user:', error.message);
        if (error.code === 'auth/user-not-found') {
            console.log('Tip: Make sure the user has signed up at https://aiodcounter06.web.app first!');
        }
    }
}

promote();
