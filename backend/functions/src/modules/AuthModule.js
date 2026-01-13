const admin = require('firebase-admin');

class AuthModule {
    constructor() {
        this.auth = admin.auth();
    }

    async setUserRole(uid, role) {
        const validRoles = ['superadmin', 'company', 'individual'];
        if (!validRoles.includes(role)) {
            throw new Error(`Invalid role: ${role}`);
        }

        await this.auth.setCustomUserClaims(uid, { role });

        // Also update user document in Firestore for easy querying
        await admin.firestore().collection('users').doc(uid).set({
            role,
            updatedAt: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true });
    }

    async getUser(uid) {
        return await this.auth.getUser(uid);
    }
}

module.exports = new AuthModule();
