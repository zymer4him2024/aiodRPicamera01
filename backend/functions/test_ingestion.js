const axios = require('axios');

async function testIngestion() {
    const url = 'http://localhost:5001/aiodcounterdemo/us-central1/api/ingest'; // Local emulator URL

    const payloads = [
        {
            name: 'Legacy Flat',
            data: {
                site_id: 'test-site-01',
                camera_id: 'test-cam-01',
                timestamp: new Date().toISOString(),
                counts: { person: 5, car: 2 }
            }
        },
        {
            name: 'Universal Nested',
            data: {
                identity: {
                    serial: 'SN12345',
                    camera_id: 'test-cam-02',
                    site_id: 'test-site-01'
                },
                environment: {
                    timestamp: new Date().toISOString(),
                    uptime: 100
                },
                data: {
                    type: 'object_counts',
                    counts: { bus: 1, truck: 3 }
                }
            }
        }
    ];

    for (const p of payloads) {
        try {
            console.log(`Testing ${p.name} payload...`);
            // Note: This requires the emulator to be running.
            // Since I cannot start a long-running process easily here, 
            // I'll just provide this as a script for the user.
            // const response = await axios.post(url, p.data);
            // console.log(`Result: ${response.status} - ${JSON.stringify(response.data)}`);
        } catch (e) {
            console.error(`Failed ${p.name}: ${e.message}`);
        }
    }
}

// testIngestion();
