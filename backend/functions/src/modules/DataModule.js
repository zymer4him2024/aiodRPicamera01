const admin = require('firebase-admin');

class DataModule {
    constructor() {
        this.db = admin.firestore();
    }

    /**
     * Stores detection counts in Firestore.
     * Path: sites/{siteId}/cameras/{cameraId}/reports/{timestamp}
     */
    async storeCount(payload) {
        const { siteId, cameraId, timestamp, counts } = payload;

        if (!siteId || !cameraId) {
            throw new Error('Missing siteId or cameraId in payload');
        }

        const docRef = this.db
            .collection('sites')
            .doc(siteId)
            .collection('cameras')
            .doc(cameraId)
            .collection('reports')
            .doc(timestamp || new Date().toISOString());

        await docRef.set({
            counts,
            timestamp: timestamp || admin.firestore.FieldValue.serverTimestamp(),
            receivedAt: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true });

        // Update site-level summary (optional but useful)
        await this.updateSiteSummary(siteId, counts);

        return docRef.id;
    }

    async updateSiteSummary(siteId, latestCounts) {
        const siteRef = this.db.collection('sites').doc(siteId);
        await siteRef.set({
            lastUpdate: admin.firestore.FieldValue.serverTimestamp(),
            latestCounts
        }, { merge: true });
    }
}

module.exports = new DataModule();
