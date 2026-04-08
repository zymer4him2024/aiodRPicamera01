const AuthModule = require('../modules/AuthModule');

class AdminAgent {
    /**
     * Placeholder for administrative task management.
     */
    async manageUsers(uid, role) {
        return await AuthModule.setUserRole(uid, role);
    }
}

module.exports = new AdminAgent();
