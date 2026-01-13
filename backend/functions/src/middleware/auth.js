const admin = require('firebase-admin');

/**
 * Middleware to verify Firebase Auth token and attach user to request.
 */
async function authenticate(req, res, next) {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).send({ error: 'Unauthorized: No token provided' });
    }

    const idToken = authHeader.split('Bearer ')[1];
    try {
        const decodedToken = await admin.auth().verifyIdToken(idToken);
        req.user = decodedToken;
        next();
    } catch (error) {
        return res.status(401).send({ error: 'Unauthorized: Invalid token' });
    }
}

/**
 * Middleware to restrict access to specific roles.
 */
function requireRole(role) {
    return (req, res, next) => {
        if (!req.user || req.user.role !== role) {
            return res.status(403).send({ error: `Forbidden: Requires ${role} role` });
        }
        next();
    };
}

/**
 * Middleware to ensure SubAdmin only accesses their own organization's data.
 */
function requireOrgAccess(req, res, next) {
    if (req.user.role === 'superadmin') {
        return next(); // SuperAdmin can access anything
    }

    const requestedOrgId = req.params.orgId || req.query.orgId || req.body.org_id;
    if (requestedOrgId && requestedOrgId !== req.user.org_id) {
        return res.status(403).send({ error: 'Forbidden: Access to this organization is denied' });
    }

    // Force organization ID from user token to prevent spoofing
    req.org_id = req.user.org_id;
    next();
}

module.exports = {
    authenticate,
    requireRole,
    requireOrgAccess
};
