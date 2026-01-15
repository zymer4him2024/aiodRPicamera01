import React, { useState, useEffect } from 'react';
import { db } from '../firebase';
import { collection, onSnapshot } from 'firebase/firestore';
import { Building2, Camera, Activity, ShieldCheck, Database, Server, Cpu, Globe } from 'lucide-react';

const SuperAdminOverview = () => {
    const [systemStats, setSystemStats] = useState({
        totalOrgs: 0,
        totalUnits: 0,
        totalUsers: 0,
        activeSess: 1,
        systemUptime: '99.98%',
        agentStatus: 'READY'
    });

    useEffect(() => {
        const unsubscribeOrgs = onSnapshot(collection(db, 'organizations'), (snapshot) => {
            setSystemStats(prev => ({ ...prev, totalOrgs: snapshot.size }));
        });
        const unsubscribeUnits = onSnapshot(collection(db, 'cameras'), (snapshot) => {
            setSystemStats(prev => ({ ...prev, totalUnits: snapshot.size }));
        });
        const unsubscribeUsers = onSnapshot(collection(db, 'users'), (snapshot) => {
            setSystemStats(prev => ({ ...prev, totalUsers: snapshot.size }));
        });

        return () => {
            unsubscribeOrgs();
            unsubscribeUnits();
            unsubscribeUsers();
        };
    }, []);

    const StatusCard = ({ label, value, icon: Icon, color = 'var(--accent)' }) => (
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', background: 'rgba(21, 28, 44, 0.4)', transition: 'transform 0.2s', cursor: 'default' }}>
            <div style={{
                width: '56px', height: '56px', background: `${color}11`,
                borderRadius: '1.25rem', display: 'flex', alignItems: 'center',
                justifyContent: 'center', border: `1px solid ${color}33`
            }}>
                <Icon size={28} color={color} />
            </div>
            <div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.2rem' }}>{label}</div>
                <div style={{ fontSize: '1.8rem', fontWeight: 800, color: 'white', lineHeight: 1 }}>{value}</div>
            </div>
        </div>
    );

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2.5rem' }}>
            {/* Top Stats Grid */}
            <div className="stat-grid">
                <StatusCard label="Total Organizations" value={systemStats.totalOrgs} icon={Building2} />
                <StatusCard label="Registered Units" value={systemStats.totalUnits} icon={Camera} />
                <StatusCard label="Active Personnel" value={systemStats.totalUsers} icon={Globe} color="var(--success)" />
                <StatusCard label="Orchestrator Status" value={systemStats.agentStatus} icon={ShieldCheck} color="var(--success)" />
            </div>

            {/* System Health Section */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
                <div className="card" style={{ background: 'rgba(21, 28, 44, 0.3)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                            <Database size={24} color="var(--accent)" /> Global Infrastructure
                        </h3>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', background: 'var(--card)', padding: '0.4rem 0.8rem', borderRadius: '0.5rem' }}>LIVE TELEMETRY</span>
                    </div>

                    <div style={{ height: '300px', display: 'flex', flexDirection: 'column', gap: '1.5rem', justifyContent: 'center' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 10px var(--success)' }}></div>
                            <div style={{ flex: 1, color: 'white', fontWeight: 500 }}>API Gateway (Edge)</div>
                            <div style={{ color: 'var(--success)', fontSize: '0.85rem' }}>STABLE</div>
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 10px var(--success)' }}></div>
                            <div style={{ flex: 1, color: 'white', fontWeight: 500 }}>Inference Pipeline</div>
                            <div style={{ color: 'var(--success)', fontSize: '0.85rem' }}>92% OPTIMIZED</div>
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)', boxShadow: '0 0 10px var(--success)' }}></div>
                            <div style={{ flex: 1, color: 'white', fontWeight: 500 }}>Database Sync (Firestore)</div>
                            <div style={{ color: 'var(--success)', fontSize: '0.85rem' }}>CONNECTED</div>
                        </div>

                        <div style={{ marginTop: 'auto', padding: '1.5rem', borderRadius: '1rem', background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.1)', textAlign: 'center' }}>
                            <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-dim)' }}>
                                System Uptime: <span style={{ color: 'white', fontWeight: 600 }}>{systemStats.systemUptime}</span> •
                                Latency: <span style={{ color: 'white', fontWeight: 600 }}>42ms</span>
                            </p>
                        </div>
                    </div>
                </div>

                <div className="card" style={{ background: 'rgba(21, 28, 44, 0.3)' }}>
                    <h3 style={{ margin: '0 0 2rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                        <Server size={24} color="var(--accent)" /> Resource Load
                    </h3>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                                <span style={{ color: 'white' }}>CPU Intensity</span>
                                <span style={{ color: 'var(--text-dim)' }}>14%</span>
                            </div>
                            <div style={{ height: '6px', background: 'var(--card)', borderRadius: '3px', overflow: 'hidden' }}>
                                <div style={{ width: '14%', height: '100%', background: 'var(--accent)' }}></div>
                            </div>
                        </div>
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.75rem' }}>
                                <span style={{ color: 'white' }}>Storage Usage</span>
                                <span style={{ color: 'var(--text-dim)' }}>2.4 / 50 GB</span>
                            </div>
                            <div style={{ height: '6px', background: 'var(--card)', borderRadius: '3px', overflow: 'hidden' }}>
                                <div style={{ width: '5%', height: '100%', background: 'var(--success)' }}></div>
                            </div>
                        </div>
                        <div style={{ padding: '1rem', borderRadius: '0.75rem', background: '#0b0f19', border: '1px solid var(--border)', marginTop: '1rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                <Cpu size={16} color="var(--accent)" />
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>Processor Mode: <span style={{ color: 'white' }}>HAILO-8 ACCELERATED</span></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SuperAdminOverview;
