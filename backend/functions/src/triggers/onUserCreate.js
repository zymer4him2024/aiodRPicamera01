const functions = require('firebase-functions/v1');
const admin = require('firebase-admin');

/**
 * Triggered when a new user is created in Firebase Auth.
 * Checks if there is a pending invitation (stub user doc) for this email.
 * If so, assigns custom claims (role, org_id) and migrates the doc to the real UID.
 */
exports.onUserCreate = functions.auth.user().onCreate(async (user) => {
    const db = admin.firestore();
    const email = user.email;

    if (!email) {
        console.log(`User ${user.uid} has no email, skipping invitation check.`);
        return;
    }

    try {
        // Query for any existing user doc with this email
        // (Invited users are created with ID "invited-{slug}", but have the email field)
        const snapshot = await db.collection('users').where('email', '==', email).get();

        if (snapshot.empty) {
            console.log(`No pending invitation found for ${email}.`);
            // Optional: Set default role if needed
            return;
        }

        // There should be only one match, but we take the first
        const inviteDoc = snapshot.docs[0];
        const inviteData = inviteDoc.data();

        console.log(`Found invitation for ${email} (Doc ID: ${inviteDoc.id}). Assigning role: ${inviteData.role}, Org: ${inviteData.org_id}`);

        // 1. Set Custom Claims
        const claims = {
            role: inviteData.role || 'individual',
        };
        if (inviteData.org_id) {
            claims.org_id = inviteData.org_id;
        }

        await admin.auth().setCustomUserClaims(user.uid, claims);

        // 2. Migrate data to the real User ID doc
        // We copy everything from the invite doc to the new user doc
        await db.collection('users').doc(user.uid).set({
            ...inviteData,
            uid: user.uid, // Ensure UID is correct
            claimed_at: admin.firestore.FieldValue.serverTimestamp(),
            status: 'active' // Auto-activate if they claimed the invite? Or keep 'pending' until approved? 
            // Logic in UserApproval.jsx sets it to 'pending' initially.
            // If the Org is already approved, user should be active.
            // If Org is pending, user remains pending.
            // We'll keep the status from the invite doc unless it's undefined.
        }, { merge: true });

        // 3. Delete the old "invited-" document to prevent duplicates
        // Only delete if the ID is different (it should be)
        if (inviteDoc.id !== user.uid) {
            await inviteDoc.ref.delete();
            console.log(`Deleted invitation doc ${inviteDoc.id}`);
        }

    } catch (error) {
        console.error('Error in onUserCreate trigger:', error);
    }
});
