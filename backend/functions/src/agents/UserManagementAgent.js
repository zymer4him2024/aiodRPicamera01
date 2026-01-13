const Agent = require('./Agent');
const admin = require('firebase-admin');

class UserManagementAgent extends Agent {
    constructor() {
        super('UserManagement');
    }

    /**
     * Creates a new organization (tenant).
     * SuperAdmin only.
     */
    async createOrganization(orgData) {
        const { org_id, name, company_name } = orgData;
        if (!org_id) throw new Error('org_id is required');

        const orgRef = this.db.collection('organizations').doc(org_id);
        await orgRef.set({
            org_id,
            name,
            company_name,
            status: 'active',
            created_at: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true });

        this.log(`Organization created: ${org_id}`);
        return org_id;
    }

    /**
     * Creates a SubAdmin user and assigns to an organization.
     * SuperAdmin only.
     */
    async createSubAdmin(userData) {
        const { email, password, full_name, org_id } = userData;

        // 1. Create Firebase Auth user
        const userRecord = await this.auth.createUser({
            email,
            password,
            displayName: full_name
        });

        // 2. Set Custom Claims
        await this.auth.setCustomUserClaims(userRecord.uid, {
            role: 'subadmin',
            org_id: org_id
        });

        // 3. Store user record in Firestore
        await this.db.collection('users').doc(userRecord.uid).set({
            email,
            full_name,
            role: 'subadmin',
            org_id,
            status: 'active',
            created_at: admin.firestore.FieldValue.serverTimestamp()
        });

        this.log(`SubAdmin created: ${email} for org: ${org_id}`);
        return userRecord.uid;
    }

    /**
     * Sets SuperAdmin role for a user.
     */
    async setSuperAdmin(uid) {
        await this.auth.setCustomUserClaims(uid, { role: 'superadmin' });
        await this.db.collection('users').doc(uid).set({
            role: 'superadmin',
            updated_at: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true });
        this.log(`SuperAdmin role assigned to: ${uid}`);
    }

    async getOrgUsers(org_id) {
        const snapshot = await this.db.collection('users').where('org_id', '==', org_id).get();
        return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    }
}

module.exports = new UserManagementAgent();
