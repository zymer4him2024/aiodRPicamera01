const Agent = require('./Agent');
const admin = require('firebase-admin');

class DeviceManagerAgent extends Agent {
    constructor() {
        super('DeviceManager');
    }

    /**
     * Registers a new camera in the system.
     */
    async registerCamera(deviceData) {
        const { serial, ip, org_id } = deviceData;
        if (!serial) throw new Error('Serial is required');

        const cameraId = `CAM_${serial.slice(-6)}`; // Simple predictable ID
        const cameraRef = this.db.collection('cameras').doc(serial);

        await cameraRef.set({
            camera_id: cameraId,
            serial,
            ip_address: ip,
            org_id: org_id || null, // Can be unassigned initially
            status: 'unbound',
            created_at: admin.firestore.FieldValue.serverTimestamp()
        }, { merge: true });

        this.log(`Camera registered: ${serial} as ${cameraId}`);
        return cameraId;
    }

    /**
     * Binds a camera to an organization and site.
     */
    async bindCamera(serial, org_id, site_id) {
        const cameraRef = this.db.collection('cameras').doc(serial);

        await cameraRef.update({
            org_id,
            site_id,
            status: 'bound',
            bound_at: admin.firestore.FieldValue.serverTimestamp()
        });

        this.log(`Camera ${serial} bound to org: ${org_id}, site: ${site_id}`);
    }

    async getCamerasByOrg(org_id) {
        const snapshot = await this.db.collection('cameras').where('org_id', '==', org_id).get();
        return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    }

    async getAllCameras() {
        const snapshot = await this.db.collection('cameras').get();
        return snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    }
}

module.exports = new DeviceManagerAgent();
