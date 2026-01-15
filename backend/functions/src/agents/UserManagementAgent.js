const Agent = require('./Agent');
const admin = require('firebase-admin');

class UserManagementAgent extends Agent {
    constructor() {
        super('UserManagement');
    }

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

    async approveUser(uid, org_id) {
        // 1. Set Custom Claims
        await this.auth.setCustomUserClaims(uid, {
            role: 'subadmin',
            org_id: org_id
        });

        // 2. Update Firestore
        await this.db.collection('users').doc(uid).update({
            status: 'active',
            org_id: org_id,
            role: 'subadmin',
            approved_at: admin.firestore.FieldValue.serverTimestamp()
        });

        this.log(`User approved: ${uid} for org: ${org_id}`);
        return true;
    }

    async setSuperAdmin(uid) {
        await this.auth.setCustomUserClaims(uid, { role: 'superadmin' });
        await this.db.collection('users').doc(uid).set({
            role: 'superadmin',
            status: 'active',
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
