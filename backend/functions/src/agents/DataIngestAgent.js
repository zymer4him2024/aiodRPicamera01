const Agent = require('./Agent');
const admin = require('firebase-admin');

class DataIngestAgent extends Agent {
    constructor() {
        super('DataIngest');
    }

    /**
     * Entry point for count ingestion.
     * Enforces organization (tenant) isolation.
     */
    async handleIngest(req, res) {
        try {
            const body = req.body;
            this.log('Received ingestion data', { body });

            // 1. Identify Camera and Org
            const serial = body.identity?.serial || body.serial;
            if (!serial) {
                return res.status(400).send({ error: 'Missing device serial' });
            }

            // 2. Lookup Camera Registration and Org
            const cameraDoc = await this.db.collection('cameras').doc(serial).get();
            if (!cameraDoc.exists) {
                this.error(`Unregistered camera ingestion: ${serial}`);
                return res.status(404).send({ error: 'Camera not registered' });
            }

            const cameraData = cameraDoc.data();
            const org_id = cameraData.org_id;
            const site_id = cameraData.site_id;

            if (!org_id) {
                this.error(`Camera ${serial} not assigned to any organization`);
                return res.status(403).send({ error: 'Camera unassigned' });
            }

            // 3. Normalize Payload
            const counts = body.data?.counts || body.counts;
            const timestamp = body.environment?.timestamp || body.timestamp || new Date().toISOString();
            const hardware = counts.hardware || {};
            const fps = counts.fps || null;

            // 4. Store in Firestore (Isolated by Org)
            const countRef = this.db
                .collection('counts')
                .doc(); // Auto-ID for time-series data

            await countRef.set({
                camera_id: cameraData.camera_id,
                serial,
                org_id,
                site_id,
                timestamp: admin.firestore.Timestamp.fromDate(new Date(timestamp)),
                counts,
                total: Object.values(counts).reduce((a, b) => (typeof b === 'number' ? a + b : a), 0),
                hardware: {
                    cpu_temp: hardware.cpu_temp || null,
                    hailo_temp: hardware.hailo_temp || null,
                    hailo_load: hardware.hailo_load || null,
                    fps: fps
                },
                created_at: admin.firestore.FieldValue.serverTimestamp()
            });

            // 5. Update Camera Last Seen
            await cameraDoc.ref.update({
                last_seen: admin.firestore.FieldValue.serverTimestamp(),
                status: 'active'
            });

            return res.status(200).send({
                success: true,
                message: 'Data ingested successfully',
                id: countRef.id
            });

        } catch (error) {
            this.error('Ingestion failed', error);
            return res.status(500).send({ error: 'Internal Server Error' });
        }
    }
}

module.exports = new DataIngestAgent();
