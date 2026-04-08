// Quick fix: Change zymer4him@gmail.com from "pending" to "active" in Firestore
// This will allow immediate login

const admin = require('firebase-admin');

admin.initializeApp({
    projectId: 'aiodcounter05'
});

const db = admin.firestore();
const auth = admin.auth();

async function activateUser() {
    const email = 'zymer4him@gmail.com';

    console.log('🔧 Activating user:', email);
    console.log('');

    try {
        // Step 1: Get the user from Firebase Auth
        const user = await auth.getUserByEmail(email);
        console.log(`✅ Found user in Auth: ${user.uid}`);

        // Step 2: Set custom claims
        await auth.setCustomUserClaims(user.uid, {
            role: 'superadmin',
            admin: true,
            superadmin: true
        });
        console.log(`✅ Set custom claims`);

        // Step 3: Find and update the user in Firestore
        // Search in all possible tenant locations
        console.log(`\n🔍 Searching for user in Firestore...`);

        const tenantsSnapshot = await db.collection('tenants').get();
        let found = false;

        for (const tenantDoc of tenantsSnapshot.docs) {
            const tenantId = tenantDoc.id;
            const userRef = db.collection('tenants').doc(tenantId).collection('users').doc(user.uid);
            const userDoc = await userRef.get();

            if (userDoc.exists) {
                console.log(`✅ Found user in tenant: ${tenantId}`);
                const currentData = userDoc.data();
                console.log(`   Current status: ${currentData.status}`);
                console.log(`   Current role: ${currentData.role}`);

                // Update to active superadmin
                await userRef.update({
                    status: 'active',
                    role: 'superadmin',
                    updatedAt: admin.firestore.FieldValue.serverTimestamp()
                });

                console.log(`\n✨ Updated user to:`);
                console.log(`   status: active`);
                console.log(`   role: superadmin`);

                found = true;
                break;
            }
        }

        if (!found) {
            console.log(`⚠️  User not found in Firestore. Creating new document...`);

            // Create in default tenant
            const defaultUserRef = db.collection('tenants').doc('default').collection('users').doc(user.uid);
            await defaultUserRef.set({
                email: email,
                role: 'superadmin',
                status: 'active',
                createdAt: admin.firestore.FieldValue.serverTimestamp(),
                updatedAt: admin.firestore.FieldValue.serverTimestamp()
            });

            console.log(`✅ Created user document in tenants/default/users/${user.uid}`);
        }

        console.log(`\n🎉 SUCCESS! User is now active and can log in.`);
        console.log(`\n📋 Next steps:`);
        console.log(`   1. Go to https://aiodcounter05.web.app/`);
        console.log(`   2. If already logged in, SIGN OUT first`);
        console.log(`   3. Sign in with ${email}`);
        console.log(`   4. You should be redirected to the Superadmin dashboard`);

    } catch (error) {
        console.error(`\n❌ Error:`, error.message);

        if (error.code === 'auth/user-not-found') {
            console.log(`\n💡 User doesn't exist in Firebase Auth yet.`);
            console.log(`   Please sign in at https://aiodcounter05.web.app/ once to create the account.`);
        }
    }

    process.exit(0);
}

activateUser();
