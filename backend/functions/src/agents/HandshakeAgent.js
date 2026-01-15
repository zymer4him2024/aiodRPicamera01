/**
 * HandshakeAgent - Handles device registration and binding handshake
 * 
 * Responsibilities:
 * - Validate QR token for device self-registration
 * - Register new devices in Firestore
 * - Generate binding configuration for RPi devices
 * - Track device activation status
 * 
 * Security: Uses one-time QR tokens stored in 'site_tokens' collection
 */
const Agent = require('./Agent');
const admin = require('firebase-admin');
const crypto = require('crypto');

class HandshakeAgent extends Agent {
    constructor() {
        super('Handshake');
    }

    /**
     * Generates a secure onboarding token for a site
     * Called from admin dashboard when creating QR codes
     */
    async generateSiteToken(siteId, orgId, options = {}) {
        const token = crypto.randomBytes(32).toString('hex');
        const expiresAt = new Date();
        expiresAt.setHours(expiresAt.getHours() + (options.validHours || 24));

        const tokenRef = this.db.collection('site_tokens').doc(token);
        await tokenRef.set({
            token,
            site_id: siteId,
            org_id: orgId,
            created_at: admin.firestore.FieldValue.serverTimestamp(),
            expires_at: admin.firestore.Timestamp.fromDate(expiresAt),
            used: false,
            used_by: null,
            max_uses: options.maxUses || 1,
            use_count: 0
        });

        this.log(`Generated token for site ${siteId}, expires at ${expiresAt.toISOString()}`);
        return {
            token,
            site_id: siteId,
            org_id: orgId,
            expires_at: expiresAt.toISOString()
        };
    }

    /**
     * Validates a QR token and returns site/org info
     */
    async validateToken(token) {
        const tokenDoc = await this.db.collection('site_tokens').doc(token).get();

        if (!tokenDoc.exists) {
            return { valid: false, error: 'Invalid token' };
        }

        const data = tokenDoc.data();

        // Check expiration
        if (data.expires_at.toDate() < new Date()) {
            return { valid: false, error: 'Token expired' };
        }

        // Check usage limit
        if (data.max_uses && data.use_count >= data.max_uses) {
            return { valid: false, error: 'Token usage limit exceeded' };
        }

        return {
            valid: true,
            site_id: data.site_id,
            org_id: data.org_id,
            token_id: token
        };
    }

    /**
     * Main handshake handler - Called by RPi to self-register
     * 
     * Expected request body:
     * {
     *   serial: "HAILO-A001-xxxxx",
     *   token: "qr_token_value",
     *   ip: "optional_ip",
     *   firmware_version: "optional"
     * }
     */
    async handleDeviceRegistration(req, res) {
        try {
            const { serial, token, ip, firmware_version } = req.body;

            // 1. Validate required fields
            if (!serial || !token) {
                return res.status(400).send({
                    success: false,
                    error: 'Missing required fields: serial and token'
                });
            }

            this.log(`Registration attempt from serial: ${serial}`);

            // 2. Validate QR token
            const tokenValidation = await this.validateToken(token);
            if (!tokenValidation.valid) {
                this.error(`Token validation failed for ${serial}: ${tokenValidation.error}`);
                return res.status(403).send({
                    success: false,
                    error: tokenValidation.error
                });
            }

            const { site_id, org_id, token_id } = tokenValidation;

            // 3. Check if device already registered
            const existingCamera = await this.db.collection('cameras').doc(serial).get();
            if (existingCamera.exists) {
                const existingData = existingCamera.data();
                // Allow re-binding if same org, otherwise reject
                if (existingData.org_id && existingData.org_id !== org_id) {
                    return res.status(409).send({
                        success: false,
                        error: 'Device already registered to another organization'
                    });
                }
            }

            // 4. Generate camera ID
            const cameraId = `CAM_${serial.slice(-6)}`;

            // 5. Register/Update camera in Firestore
            const cameraRef = this.db.collection('cameras').doc(serial);
            await cameraRef.set({
                camera_id: cameraId,
                serial,
                site_id,
                org_id,
                ip_address: ip || null,
                firmware_version: firmware_version || null,
                status: 'bound',
                registered_at: existingCamera.exists
                    ? existingCamera.data().registered_at
                    : admin.firestore.FieldValue.serverTimestamp(),
                bound_at: admin.firestore.FieldValue.serverTimestamp(),
                last_seen: admin.firestore.FieldValue.serverTimestamp()
            }, { merge: true });

            // 6. Mark token as used (increment count)
            await this.db.collection('site_tokens').doc(token_id).update({
                use_count: admin.firestore.FieldValue.increment(1),
                used: true,
                used_by: serial,
                used_at: admin.firestore.FieldValue.serverTimestamp()
            });

            // 7. Get site info for endpoint construction
            const siteDoc = await this.db.collection('sites').doc(site_id).get();
            const siteName = siteDoc.exists ? siteDoc.data().name : site_id;

            // 8. Build binding configuration for RPi
            // Get the project ID for the API URL
            const projectId = process.env.GCLOUD_PROJECT || 'aiodcounter06';
            const region = 'us-central1';

            const bindingConfig = {
                bound: true,
                camera_id: cameraId,
                site_id: site_id,
                site_name: siteName,
                org_id: org_id,
                endpoint: `https://${region}-${projectId}.cloudfunctions.net/ingestCounts`,
                auth_mode: 'apikey',
                auth_token: `device_${serial}_${Date.now()}`, // Simple device auth token
                payload_format: 'aiod05',
                tenant_id: org_id,
                registered_at: new Date().toISOString()
            };

            this.log(`Device ${serial} successfully registered to site ${site_id}`);

            return res.status(200).send({
                success: true,
                message: 'Device registered and bound successfully',
                binding: bindingConfig
            });

        } catch (error) {
            this.error('Device registration failed', error);
            return res.status(500).send({
                success: false,
                error: 'Internal server error during registration'
            });
        }
    }

    /**
     * Handles activation ping from RPi after binding
     */
    async handleActivation(req, res) {
        try {
            const { serial, status } = req.body;

            if (!serial) {
                return res.status(400).send({ error: 'Missing serial' });
            }

            const cameraRef = this.db.collection('cameras').doc(serial);
            const cameraDoc = await cameraRef.get();

            if (!cameraDoc.exists) {
                return res.status(404).send({ error: 'Camera not registered' });
            }

            await cameraRef.update({
                status: status || 'active',
                last_seen: admin.firestore.FieldValue.serverTimestamp(),
                last_activation: admin.firestore.FieldValue.serverTimestamp()
            });

            this.log(`Camera ${serial} activated with status: ${status || 'active'}`);

            return res.status(200).send({
                success: true,
                message: 'Activation recorded',
                camera_id: cameraDoc.data().camera_id
            });

        } catch (error) {
            this.error('Activation failed', error);
            return res.status(500).send({ error: 'Internal server error' });
        }
    }

    /**
     * Lists all pending (unused) tokens for admin dashboard
     */
    async getPendingTokens(orgId = null) {
        let query = this.db.collection('site_tokens').where('used', '==', false);

        if (orgId) {
            query = query.where('org_id', '==', orgId);
        }

        const snapshot = await query.get();
        return snapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
            expires_at: doc.data().expires_at?.toDate()?.toISOString()
        }));
    }
}

module.exports = new HandshakeAgent();
