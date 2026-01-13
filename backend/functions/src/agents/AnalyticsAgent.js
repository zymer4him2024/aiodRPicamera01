const Agent = require('./Agent');
const admin = require('firebase-admin');

class AnalyticsAgent extends Agent {
    constructor() {
        super('Analytics');
    }

    /**
     * Aggregates counts for a specific organization.
     */
    async getOrgSummary(org_id, dateRange = 'today') {
        let query = this.db.collection('counts').where('org_id', '==', org_id);

        if (dateRange === 'today') {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            query = query.where('timestamp', '>=', admin.firestore.Timestamp.fromDate(today));
        }

        const snapshot = await query.orderBy('timestamp', 'desc').get();

        const summary = {
            total_counts: 0,
            camera_breakdown: {},
            object_breakdown: {}
        };

        snapshot.forEach(doc => {
            const data = doc.data();
            summary.total_counts += (data.total || 0);

            // Per Camera
            summary.camera_breakdown[data.camera_id] = (summary.camera_breakdown[data.camera_id] || 0) + (data.total || 0);

            // Per Object Type
            for (const [key, val] of Object.entries(data.counts || {})) {
                summary.object_breakdown[key] = (summary.object_breakdown[key] || 0) + val;
            }
        });

        return summary;
    }

    /**
     * Future: Scheduled hourly aggregation jobs.
     */
    async runHourlyJob() {
        this.log('Running hourly aggregation job (Placeholder)');
    }
}

module.exports = new AnalyticsAgent();
