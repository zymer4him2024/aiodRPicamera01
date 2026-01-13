// Diagnostic script to check what's in Firestore for zymer4him@gmail.com

const admin = require('firebase-admin');

admin.initializeApp({
    projectId: 'aiodcounter05'
});

const db = admin.firestore();
const auth = admin.auth();

async function diagnose() {
    const email = 'zymer4him@gmail.com';

    console.log('🔍 Diagnosing aiodcounter05 for:', email);
    console.log('');

    try {
        // Step 1: Check Firebase Auth
        console.log('1️⃣ Checking Firebase Authentication...');
        const user = await auth.getUserByEmail(email);
        console.log(`   ✅ User exists in Auth`);
        console.log(`   UID: ${user.uid}`);
        console.log(`   Email verified: ${user.emailVerified}`);
        console.log(`   Custom claims:`, user.customClaims || 'none');

        // Step 2: Check all tenants in Firestore
        console.log('\n2️⃣ Checking Firestore tenants...');
        const tenantsSnapshot = await db.collection('tenants').get();

        if (tenantsSnapshot.empty) {
            console.log('   ⚠️  NO TENANTS FOUND in Firestore!');
            console.log('   This is the problem - the database is empty.');
            return;
        }

        console.log(`   Found ${tenantsSnapshot.size} tenant(s)`);

        let userFound = false;

        for (const tenantDoc of tenantsSnapshot.docs) {
            const tenantId = tenantDoc.id;
            console.log(`\n   📁 Tenant: ${tenantId}`);

            // Check if user exists in this tenant
            const userRef = db.collection('tenants').doc(tenantId).collection('users').doc(user.uid);
            const userDoc = await userRef.get();

            if (userDoc.exists) {
                userFound = true;
                const data = userDoc.data();
                console.log(`      ✅ USER FOUND!`);
                console.log(`      Email: ${data.email}`);
                console.log(`      Role: ${data.role}`);
                console.log(`      Status: ${data.status}`);
                console.log(`      Created: ${data.createdAt?.toDate()}`);
            } else {
                console.log(`      ❌ User not found in this tenant`);
            }
        }

        if (!userFound) {
            console.log('\n❌ PROBLEM FOUND: User exists in Auth but NOT in any Firestore tenant!');
            console.log('\n💡 SOLUTION: Run the activate-user.js script to create the Firestore document.');
        } else {
            console.log('\n✅ User found in Firestore. If still seeing white page, check:');
            console.log('   1. Make sure status is "active"');
            console.log('   2. Make sure role is "superadmin"');
            console.log('   3. Make sure custom claims are set in Auth');
            console.log('   4. Sign out and sign back in');
        }

    } catch (error) {
        console.error('\n❌ Error:', error.message);
    }

    process.exit(0);
}

diagnose();
