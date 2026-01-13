const admin = require('firebase-admin');

// Initialize Firebase Admin
const serviceAccount = require('./aiodcounter05-service-account.json');

admin.initializeApp({
    credential: admin.credential.cert(serviceAccount)
});

async function setSuperadminRole() {
    const email = 'zymer4him@gmail.com';

    try {
        // Get user by email
        const user = await admin.auth().getUserByEmail(email);
        console.log(`Found user: ${user.uid}`);

        // Set custom claims for superadmin
        await admin.auth().setCustomUserClaims(user.uid, {
            role: 'superadmin',
            admin: true
        });

        console.log(`✅ Successfully set superadmin role for ${email}`);
        console.log('Custom claims:', { role: 'superadmin', admin: true });

        // Verify the claims were set
        const updatedUser = await admin.auth().getUser(user.uid);
        console.log('Verified custom claims:', updatedUser.customClaims);

        process.exit(0);
    } catch (error) {
        console.error('❌ Error setting superadmin role:', error);
        process.exit(1);
    }
}

setSuperadminRole();
