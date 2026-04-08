// Fix superadmin role for zymer4him@gmail.com in aiodcounter05
// This version uses the service account from AIAutotraining03 but targets aiodcounter05

const admin = require('firebase-admin');
const path = require('path');

// Use the service account from AIAutotraining03 directory
const serviceAccountPath = path.join(__dirname, '../AIAutotraining03/aiautotraining03-firebase-adminsdk-fbsvc-a6333aec41.json');

console.log(`📁 Loading service account from: ${serviceAccountPath}`);

try {
    const serviceAccount = require(serviceAccountPath);

    // Initialize Firebase Admin for aiodcounter05 project
    admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
        projectId: 'aiodcounter05'  // Override to target aiodcounter05
    });

    console.log(`✅ Firebase Admin initialized for project: aiodcounter05`);

} catch (error) {
    console.error(`❌ Failed to load service account:`, error.message);
    console.log(`\n💡 Please ensure the service account file exists at:`);
    console.log(`   ${serviceAccountPath}`);
    process.exit(1);
}

async function setSuperadmin() {
    const email = 'zymer4him@gmail.com';

    try {
        console.log(`\n🔍 Looking up user: ${email}`);
        const user = await admin.auth().getUserByEmail(email);

        console.log(`✅ Found user!`);
        console.log(`   UID: ${user.uid}`);
        console.log(`   Email: ${user.email}`);
        console.log(`   Current custom claims:`, user.customClaims || 'none');

        // Set superadmin custom claims
        console.log(`\n🔧 Setting superadmin custom claims...`);
        await admin.auth().setCustomUserClaims(user.uid, {
            role: 'superadmin',
            admin: true,
            superadmin: true
        });

        console.log(`✨ Successfully set superadmin role!`);

        // Verify the claims were set
        const updated = await admin.auth().getUser(user.uid);
        console.log(`\n✅ Verified new custom claims:`, updated.customClaims);

        console.log(`\n⚠️  IMPORTANT NEXT STEPS:`);
        console.log(`   1. User must sign out of aiodcounter05.web.app`);
        console.log(`   2. User must sign back in`);
        console.log(`   3. Then navigate to /Superadmin or /admin`);

    } catch (error) {
        console.error(`\n❌ Error:`, error.message);

        if (error.code === 'auth/user-not-found') {
            console.log(`\n💡 User doesn't exist in aiodcounter05 yet.`);
            console.log(`   They need to sign in at https://aiodcounter05.web.app at least once first.`);
        } else if (error.code === 'auth/project-not-found') {
            console.log(`\n💡 Make sure you have the correct permissions for aiodcounter05 project.`);
        }
    }

    process.exit(0);
}

setSuperadmin();
