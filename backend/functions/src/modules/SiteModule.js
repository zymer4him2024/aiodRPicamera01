const admin = require('firebase-admin');

class SiteModule {
    constructor() {
        this.db = admin.firestore();
    }

    async getSiteConfig(siteId) {
        const doc = await this.db.collection('sites').doc(siteId).get();
        if (!doc.exists) return null;
        return doc.data();
    }

    async validateCamera(siteId, cameraId) {
        const cameraDoc = await this.db
            .collection('sites')
            .doc(siteId)
            .collection('cameras')
            .doc(cameraId)
            .get();

        return cameraDoc.exists;
    }

    async registerCamera(siteId, cameraId, metadata = {}) {
        const cameraRef = this.db
            .collection('sites')
            .doc(siteId)
            .collection('cameras')
            .doc(cameraId);

        await cameraRef.set({
            ...metadata,
            registeredAt: admin.firestore.FieldValue.serverTimestamp(),
            status: 'active'
        }, { merge: true });
    }
}

module.exports = new SiteModule();
