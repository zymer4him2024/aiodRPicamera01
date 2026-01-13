const Agent = require('./Agent');

class OrchestratorAgent extends Agent {
    constructor() {
        super('Orchestrator');
        this.agents = new Map();
    }

    registerAgent(agent) {
        this.agents.set(agent.name, agent);
        this.log(`Agent registered: ${agent.name}`);
    }

    async getSystemStatus() {
        return {
            status: 'operational',
            uptime: process.uptime(),
            agents: Array.from(this.agents.keys()),
            timestamp: new Date().toISOString()
        };
    }

    /**
     * Executes a high-level workflow.
     */
    async executeWorkflow(workflowName, params) {
        this.log(`Executing workflow: ${workflowName}`, params);
        // Workflows will be implemented separately in src/workflows/
        try {
            const Workflow = require(`../workflows/${workflowName}`);
            const workflow = new Workflow(this);
            return await workflow.execute(params);
        } catch (error) {
            this.error(`Workflow ${workflowName} failed`, error);
            throw error;
        }
    }
}

module.exports = new OrchestratorAgent();
