const admin = require('firebase-admin');
const { logger } = require('firebase-functions');

class Agent {
    constructor(name) {
        this.name = name;
        this.db = admin.firestore();
        this.auth = admin.auth();
        this.logger = logger;
    }

    log(message, metadata = {}) {
        this.logger.info(`[Agent:${this.name}] ${message}`, metadata);
    }

    error(message, err = {}) {
        this.logger.error(`[Agent:${this.name}] ${message}`, err);
    }
}

module.exports = Agent;
