// Bootstrap script to create the first superadmin user in aiodcounter05
// This bypasses the approval flow by directly writing to Firestore

const admin = require('firebase-admin');

// Initialize for aiodcounter05
admin.initializeApp({
    projectId: 'aiodcounter05'
});

const db = admin.firestore();
const auth = admin.auth();

async function bootstrapSuperadmin() {
    const email = 'zymer4him@gmail.com';

    console.log('🚀 Bootstrapping first superadmin for aiodcounter05...\n');

    try {
        // Step 1: Get or create the user in Firebase Auth
        let user;
        try {
            user = await auth.getUserByEmail(email);
            console.log(`✅ Found existing user: ${user.uid}`);
        } catch (error) {
            if (error.code === 'auth/user-not-found') {
                console.log(`📝 User doesn't exist yet. Creating...`);
                user = await auth.createUser({
                    email: email,
                    emailVerified: true,
                    disabled: false
                });
                console.log(`✅ Created user: ${user.uid}`);
            } else {
                throw error;
            }
        }

        // Step 2: Set custom claims for superadmin
        console.log(`\n🔧 Setting custom claims...`);
        await auth.setCustomUserClaims(user.uid, {
            role: 'superadmin',
            admin: true,
            superadmin: true
        });
        console.log(`✅ Custom claims set`);

        // Step 3: Create/update user document in Firestore
        // Based on the security rules, the path should be: tenants/{tenantId}/users/{userId}
        // For the first superadmin, we'll use a default tenant or create one

        const tenantId = 'default';
        const userDocRef = db.collection('tenants').doc(tenantId).collection('users').doc(user.uid);

        const userData = {
            email: email,
            role: 'superadmin',
            status: 'active',  // IMPORTANT: Set to active to bypass approval
            createdAt: admin.firestore.FieldValue.serverTimestamp(),
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
        };

        console.log(`\n📝 Creating/updating Firestore document...`);
        await userDocRef.set(userData, { merge: true });
        console.log(`✅ Firestore document created at: tenants/${tenantId}/users/${user.uid}`);

        // Step 4: Verify everything
        console.log(`\n🔍 Verifying setup...`);
        const updatedUser = await auth.getUser(user.uid);
        console.log(`   Custom claims:`, updatedUser.customClaims);

        const userDoc = await userDocRef.get();
        console.log(`   Firestore data:`, userDoc.data());

        console.log(`\n✨ SUCCESS! Superadmin bootstrapped!`);
        console.log(`\n📋 Next steps:`);
        console.log(`   1. Go to https://aiodcounter05.web.app/`);
        console.log(`   2. Sign in with ${email}`);
        console.log(`   3. You should be automatically redirected to /admin or /Superadmin`);
        console.log(`\n⚠️  If you were already logged in, SIGN OUT FIRST, then sign back in.`);

    } catch (error) {
        console.error(`\n❌ Error:`, error);
        console.log(`\nTroubleshooting:`);
        console.log(`   - Make sure you're authenticated: gcloud auth application-default login`);
        console.log(`   - Or download service account key for aiodcounter05`);
    }

    process.exit(0);
}

bootstrapSuperadmin();
