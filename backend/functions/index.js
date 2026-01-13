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

// Import Middleware
const { authenticate, requireRole, requireOrgAccess } = require('./src/middleware/auth');

const app = express();
app.use(express.json());

// Register all agents with Orchestrator
OrchestratorAgent.registerAgent(DataIngestAgent);
OrchestratorAgent.registerAgent(DeviceManagerAgent);
OrchestratorAgent.registerAgent(UserManagementAgent);
OrchestratorAgent.registerAgent(AnalyticsAgent);

// --- PUBLIC ENDPOINTS ---

/**
 * Health check & status
 */
app.get('/status', async (req, res) => {
    const status = await OrchestratorAgent.getSystemStatus();
    res.status(200).send(status);
});

/**
 * HW Ingestion Endpoint
 */
app.post('/ingest', (req, res) => DataIngestAgent.handleIngest(req, res));


// --- SUPERADMIN ENDPOINTS ---

/**
 * Organization and SubAdmin management
 */
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

/**
 * Fleet Management
 */
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


// --- SUBADMIN ENDPOINTS (Filtered by Org) ---

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

// Individual direct functions if needed (Legacy Support)
exports.ingestCounts = onRequest((req, res) => DataIngestAgent.handleIngest(req, res));
