const DataModule = require('../modules/DataModule');
const SiteModule = require('../modules/SiteModule');
const { logger } = require('firebase-functions');

class IngestionAgent {
    /**
     * Entry point for standard HTTP count ingestion.
     * Supports various payload formats as defined in HW TransportAgent.
     */
    async handleReport(req, res) {
        try {
            const body = req.body;
            logger.info('Received ingestion report', { body });

            let processedPayload;

            // 1. Determine payload format and normalize
            if (body.identity && body.data) {
                // Universal/Nested Schema
                processedPayload = {
                    siteId: body.identity.site_id,
                    cameraId: body.identity.camera_id,
                    timestamp: body.environment?.timestamp,
                    counts: body.data.counts
                };
            } else if (body.tenant_id && body.data) {
                // AIODCOUNTER05 Schema
                processedPayload = {
                    siteId: body.site_id,
                    cameraId: body.camera_id,
                    timestamp: body.timestamp,
                    counts: body.data.counts
                };
            } else if (body.site_id && body.camera_id) {
                // Legacy Flat Schema
                processedPayload = {
                    siteId: body.site_id,
                    cameraId: body.camera_id,
                    timestamp: body.timestamp,
                    counts: body.counts
                };
            } else {
                return res.status(400).send({ error: 'Unsupported or malformed payload schema' });
            }

            // 2. Business Logic / Validation
            if (!processedPayload.siteId || !processedPayload.cameraId) {
                return res.status(400).send({ error: 'Missing identity fields (site_id/camera_id)' });
            }

            // (Optional) Validate camera registration
            // const isValid = await SiteModule.validateCamera(processedPayload.siteId, processedPayload.cameraId);
            // if (!isValid) logger.warn('Ingestion from unregistered camera', { processedPayload });

            // 3. Delegate to DataModule
            const docId = await DataModule.storeCount(processedPayload);

            return res.status(200).send({
                success: true,
                message: 'Data ingested successfully',
                id: docId
            });

        } catch (error) {
            logger.error('Ingestion failed', error);
            return res.status(500).send({ error: 'Internal Server Error', detail: error.message });
        }
    }
}

module.exports = new IngestionAgent();
