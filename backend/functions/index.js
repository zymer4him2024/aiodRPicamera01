const admin = require('firebase-admin');
const { onRequest } = require('firebase-functions/v2/https');
const express = require('express');

// Initialize Admin SDK
admin.initializeApp();

// Import Agents
const OrchestratorAgent = require('./src/agents/OrchestratorAgent');
const DataIngestAgent = require('./src/agents/DataIngestAgent');
const DeviceManagerAgent = require('./src/agents/DeviceManagerAgent');
const UserManagementAgent = require('./src/agents/UserManagementAgent');
const AnalyticsAgent = require('./src/agents/AnalyticsAgent');
const HandshakeAgent = require('./src/agents/HandshakeAgent');

// Import Middleware
const { authenticate, requireRole, requireOrgAccess } = require('./src/middleware/auth');

const app = express();
app.use(express.json());

const cors = require('cors')({ origin: true });
app.use(cors);

// Register all agents with Orchestrator
OrchestratorAgent.registerAgent(DataIngestAgent);
OrchestratorAgent.registerAgent(DeviceManagerAgent);
OrchestratorAgent.registerAgent(UserManagementAgent);
OrchestratorAgent.registerAgent(AnalyticsAgent);
OrchestratorAgent.registerAgent(HandshakeAgent);

// --- PUBLIC ENDPOINTS ---

app.get('/status', async (req, res) => {
    const status = await OrchestratorAgent.getSystemStatus();
    res.status(200).send(status);
});

app.post('/ingest', (req, res) => DataIngestAgent.handleIngest(req, res));

// Public: List available sites for device onboarding
app.get('/public/sites', async (req, res) => {
    try {
        const admin = require('firebase-admin');
        const db = admin.firestore();

        // Get all active sites with their org info
        const sitesSnapshot = await db.collection('sites')
            .where('status', '==', 'active')
            .get();

        const sites = [];
        for (const doc of sitesSnapshot.docs) {
            const siteData = doc.data();

            // Get org name
            let orgName = siteData.org_id;
            try {
                const orgDoc = await db.collection('organizations').doc(siteData.org_id).get();
                if (orgDoc.exists) {
                    orgName = orgDoc.data().name || siteData.org_id;
                }
            } catch (e) { /* ignore */ }

            sites.push({
                id: doc.id,
                name: siteData.name,
                org_id: siteData.org_id,
                org_name: orgName
            });
        }

        res.status(200).send(sites);
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});


// --- DEVICE HANDSHAKE ENDPOINTS (Called by RPi) ---

// Device self-registration using QR token
app.post('/device/register', (req, res) => HandshakeAgent.handleDeviceRegistration(req, res));

// Device activation ping
app.post('/device/activate', (req, res) => HandshakeAgent.handleActivation(req, res));

// DEV ONLY: Seed a test token (remove in production)
app.post('/dev/seed-token', async (req, res) => {
    try {
        const { token, site_id, org_id } = req.body;
        if (!token || !site_id || !org_id) {
            return res.status(400).send({ error: 'Missing required fields: token, site_id, org_id' });
        }
        const tokenData = await HandshakeAgent.generateSiteToken(site_id, org_id, {
            validHours: 48,
            maxUses: 10
        });
        // Override with provided token for testing
        const admin = require('firebase-admin');
        await admin.firestore().collection('site_tokens').doc(token).set({
            token,
            site_id,
            org_id,
            created_at: admin.firestore.FieldValue.serverTimestamp(),
            expires_at: admin.firestore.Timestamp.fromDate(new Date(Date.now() + 48 * 60 * 60 * 1000)),
            used: false,
            used_by: null,
            max_uses: 10,
            use_count: 0
        });
        res.status(201).send({ success: true, token, site_id, org_id });
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});


// --- SUPERADMIN ENDPOINTS ---

app.post('/admin/users/approve', authenticate, requireRole('superadmin'), async (req, res) => {
    try {
        const { uid, org_id } = req.body;
        if (!uid || !org_id) throw new Error('uid and org_id are required');
        await UserManagementAgent.approveUser(uid, org_id);
        res.status(200).send({ success: true });
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});

app.post('/admin/organizations', authenticate, requireRole('superadmin'), async (req, res) => {
    try {
        const orgId = await UserManagementAgent.createOrganization(req.body);
        res.status(201).send({ success: true, orgId });
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});

app.post('/admin/subadmins', authenticate, requireRole('superadmin'), async (req, res) => {
    try {
        const uid = await UserManagementAgent.createSubAdmin(req.body);
        res.status(201).send({ success: true, uid });
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});

app.get('/admin/cameras', authenticate, requireRole('superadmin'), async (req, res) => {
    const cameras = await DeviceManagerAgent.getAllCameras();
    res.send(cameras);
});

app.post('/admin/cameras/bind', authenticate, requireRole('superadmin'), async (req, res) => {
    try {
        const { serial, org_id, site_id } = req.body;
        await DeviceManagerAgent.bindCamera(serial, org_id, site_id);
        res.send({ success: true });
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});

// Generate QR onboarding token for a site
app.post('/admin/sites/generate-token', authenticate, requireRole('superadmin'), async (req, res) => {
    try {
        const { site_id, org_id, valid_hours, max_uses } = req.body;
        if (!site_id || !org_id) {
            return res.status(400).send({ error: 'site_id and org_id are required' });
        }
        const tokenData = await HandshakeAgent.generateSiteToken(site_id, org_id, {
            validHours: valid_hours || 24,
            maxUses: max_uses || 10
        });
        res.status(201).send({ success: true, ...tokenData });
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});


// --- SUBADMIN ENDPOINTS ---

app.get('/subadmin/analytics', authenticate, requireRole('subadmin'), requireOrgAccess, async (req, res) => {
    try {
        const summary = await AnalyticsAgent.getOrgSummary(req.user.org_id);
        res.send(summary);
    } catch (e) {
        res.status(500).send({ error: e.message });
    }
});

app.get('/subadmin/cameras', authenticate, requireRole('subadmin'), requireOrgAccess, async (req, res) => {
    const cameras = await DeviceManagerAgent.getCamerasByOrg(req.user.org_id);
    res.send(cameras);
});


// Export the Cloud Function
exports.api = onRequest({
    memory: "256MiB",
    timeoutSeconds: 60,
    region: "us-central1"
}, app);

exports.ingestCounts = onRequest((req, res) => DataIngestAgent.handleIngest(req, res));

// Trigger for linking invited users
const { onUserCreate } = require('./src/triggers/onUserCreate');
exports.onUserCreate = onUserCreate;

