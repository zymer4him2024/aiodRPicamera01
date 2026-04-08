const admin = require('firebase-admin');

/**
 * Middleware to require superadmin role for protected endpoints
 * Returns 403 Forbidden if user is not a superadmin
 */
async function requireSuperAdmin(req, res, next) {
    try {
        // Extract token from Authorization header
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
                error: 'Unauthorized',
                message: 'Missing or invalid authorization header'
            });
        }

        const token = authHeader.split('Bearer ')[1];

        // Verify the token
        const decodedToken = await admin.auth().verifyIdToken(token);

        // Check if user has superadmin role
        const role = decodedToken.role || decodedToken.claims?.role;

        if (role !== 'superadmin') {
            return res.status(403).json({
                error: 'Forbidden',
                message: 'This action requires superadmin privileges'
            });
        }

        // Attach user info to request for downstream use
        req.user = {
            uid: decodedToken.uid,
            email: decodedToken.email,
            role: role,
            org_id: decodedToken.org_id
        };

        next();
    } catch (error) {
        console.error('Auth middleware error:', error);

        if (error.code === 'auth/id-token-expired') {
            return res.status(401).json({
                error: 'Unauthorized',
                message: 'Token expired'
            });
        }

        return res.status(401).json({
            error: 'Unauthorized',
            message: 'Invalid token'
        });
    }
}

/**
 * Middleware to require any authenticated user
 */
async function requireAuth(req, res, next) {
    try {
        const authHeader = req.headers.authorization;
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return res.status(401).json({
                error: 'Unauthorized',
                message: 'Missing or invalid authorization header'
            });
        }

        const token = authHeader.split('Bearer ')[1];
        const decodedToken = await admin.auth().verifyIdToken(token);

        req.user = {
            uid: decodedToken.uid,
            email: decodedToken.email,
            role: decodedToken.role || decodedToken.claims?.role,
            org_id: decodedToken.org_id
        };

        next();
    } catch (error) {
        console.error('Auth middleware error:', error);
        return res.status(401).json({
            error: 'Unauthorized',
            message: 'Invalid token'
        });
    }
}

module.exports = {
    requireSuperAdmin,
    requireAuth
};
