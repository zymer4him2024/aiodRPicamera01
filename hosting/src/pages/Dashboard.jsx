import React, { useState, useEffect } from 'react';
import { db, auth } from '../firebase';
import { doc, onSnapshot, updateDoc, serverTimestamp, collection, query, where, orderBy, limit } from 'firebase/firestore';
import {
    Users, Car, Bus, Truck, Bike, LogOut, LayoutDashboard,
    ShieldCheck, Settings, Activity, Clock, ShieldAlert,
    Building2, Camera, Database, BarChart3, ListChecks
} from 'lucide-react';
import OrgManagement from '../components/OrgManagement';
import SuperAdminOverview from '../components/SuperAdminOverview';
import UserApproval from '../components/UserApproval';
import SiteManagement from '../components/SiteManagement';
import FleetManagement from '../components/FleetManagement';

const Dashboard = ({ user }) => {
    const [stats, setStats] = useState({ person: 0, car: 0, bus: 0, truck: 0, motorcycle: 0 });
    const [role, setRole] = useState(null);
    const [orgId, setOrgId] = useState(null);
    const [status, setStatus] = useState('active');
    const [activeTab, setActiveTab] = useState('overview'); // 'overview', 'users', 'orgs', 'fleet'

    useEffect(() => {
        let isMounted = true;
        let unsubscribeStatus = null;
        let unsubscribeCounts = null;

        const initAuth = async () => {
            try {
                const u = auth.currentUser;
                if (!u) return;

                const result = await u.getIdTokenResult(true);
                if (!isMounted) return;

                const userRole = result.claims.role || 'subadmin';
                const userOrg = result.claims.org_id;
                setRole(userRole);
                setOrgId(userOrg);

                // User Status Listener
                unsubscribeStatus = onSnapshot(doc(db, 'users', u.uid), (snapshot) => {
                    if (!isMounted) return;
                    if (snapshot.exists()) {
                        const data = snapshot.data();
                        setStatus(data.status || 'pending');
                        if (data.status === 'pending' && userRole === 'superadmin') {
                            updateDoc(doc(db, 'users', u.uid), { status: 'active' });
                            setStatus('active');
                        }
                    }
                });

                // Real-time Counts Listener
                if (userOrg || userRole === 'superadmin') {
                    const countsRef = collection(db, 'counts');
                    let q;

                    if (userRole === 'superadmin') {
                        // Global latest count for SuperAdmin debugging
                        q = query(
                            countsRef,
                            orderBy('timestamp', 'desc'),
                            limit(1)
                        );
                    } else {
                        // Org specific latest count
                        q = query(
                            countsRef,
                            where('org_id', '==', userOrg),
                            orderBy('timestamp', 'desc'),
                            limit(1)
                        );
                    }

                    unsubscribeCounts = onSnapshot(q,
                        (snapshot) => {
                            if (!isMounted || snapshot.empty) {
                                console.log('Counts snapshot empty or unmounted');
                                return;
                            }
                            const latest = snapshot.docs[0].data();
                            console.log('Received counts:', latest);
                            if (latest.counts) {
                                setStats({
                                    person: latest.counts.Pedestrians || 0,
                                    car: latest.counts.Cars || 0,
                                    bus: latest.counts.Buses || 0,
                                    truck: latest.counts.Trucks || 0,
                                    motorcycle: latest.counts.Motorcycles || 0
                                });
                            }
                        },
                        (error) => {
                            console.error('Firestore counts listener error:', error);
                            console.error('Error code:', error.code);
                            console.error('Error message:', error.message);
                        }
                    );
                }

            } catch (err) {
                if (isMounted) console.error("Auth Refresh Error", err);
            }
        };

        initAuth();

        return () => {
            isMounted = false;
            if (unsubscribeStatus) unsubscribeStatus();
            if (unsubscribeCounts) unsubscribeCounts();
        };
    }, []);

    const NavItem = ({ id, label, icon: Icon }) => (
        <button
            onClick={() => setActiveTab(id)}
            className="btn"
            style={{
                display: 'flex', alignItems: 'center', gap: '0.75rem',
                color: activeTab === id ? 'var(--accent)' : 'var(--text-dim)',
                background: activeTab === id ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
                border: activeTab === id ? '1px solid rgba(56, 189, 248, 0.2)' : '1px solid transparent',
                width: '100%', textAlign: 'left', marginBottom: '0.25rem'
            }}
        >
            <Icon size={18} /> {label}
        </button>
    );

    if (!role) return (
        <div className="main-content" style={{ display: 'flex', height: '100vh', alignItems: 'center', justifyContent: 'center', background: '#0b0f19', color: 'white' }}>
            <div style={{ textAlign: 'center' }}>
                <Activity className="spin" size={48} color="var(--accent)" style={{ marginBottom: '1rem' }} />
                <p>Initializing Secure Session...</p>
            </div>
        </div>
    );

    return (
        <div className="dashboard-container">
            <div className="sidebar">
                <div style={{ marginBottom: '3.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--accent)', marginBottom: '0.25rem' }}>
                        <div style={{ width: '32px', height: '32px', background: 'var(--accent)', borderRadius: '0.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <ShieldCheck size={20} color="#0b0f19" />
                        </div>
                        <h2 style={{ fontSize: '1.25rem', fontWeight: 800, margin: 0 }}>AIOD</h2>
                    </div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', letterSpacing: '0.15em', fontWeight: 600 }}>ENTERPRISE COMMAND</div>
                </div>

                <nav style={{ flex: 1 }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginBottom: '1rem', letterSpacing: '0.05em', paddingLeft: '0.5rem' }}>CORE ENGINE</div>
                    <NavItem id="overview" label="Overview" icon={LayoutDashboard} />

                    {role === 'superadmin' ? (
                        <>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', margin: '2rem 0 1rem', letterSpacing: '0.05em', paddingLeft: '0.5rem' }}>MANAGEMENT</div>
                            <NavItem id="users" label="User Access" icon={ListChecks} />
                            <NavItem id="orgs" label="Organizations" icon={Building2} />
                            <NavItem id="sites" label="Site Infrastructure" icon={Database} />
                            <NavItem id="hardware" label="Hardware Fleet" icon={Camera} />

                            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', margin: '2rem 0 1rem', letterSpacing: '0.05em', paddingLeft: '0.5rem' }}>ANALYTICS</div>
                            <NavItem id="stats" label="Data Intelligence" icon={BarChart3} />
                        </>
                    ) : (
                        <>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', margin: '2rem 0 1rem', letterSpacing: '0.05em', paddingLeft: '0.5rem' }}>OPERATIONS</div>
                            <NavItem id="telemetry" label="Real-time Stream" icon={Activity} />
                        </>
                    )}
                </nav>

                <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border)', paddingTop: '1.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', padding: '0 0.5rem' }}>
                        <div style={{ width: '32px', height: '32px', background: 'var(--card)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border)' }}>
                            <Users size={16} color="var(--text-dim)" />
                        </div>
                        <div>
                            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'white', maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.email.split('@')[0]}</div>
                            <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>{role.toUpperCase()}</div>
                        </div>
                    </div>
                    <button onClick={() => auth.signOut()} className="btn" style={{ background: 'rgba(239, 68, 68, 0.05)', color: 'var(--danger)', width: '100%', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <LogOut size={18} /> Sign Out
                    </button>
                </div>
            </div>

            <div className="main-content">
                <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                        <h1 style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: '0.5rem', letterSpacing: '-0.03em' }}>
                            {activeTab === 'overview' ? 'Global Command' : activeTab.charAt(0).toUpperCase() + activeTab.slice(1).replace(/([A-Z])/g, ' $1')}
                        </h1>
                        <p style={{ color: 'var(--text-dim)', fontSize: '1.1rem' }}>
                            {status === 'active' ? 'Operational Status: SECURE' : 'Access Policy: RESTRICTED'}
                        </p>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <div style={{ background: 'rgba(21, 28, 44, 0.6)', padding: '0.6rem 1.25rem', borderRadius: '2rem', border: '1px solid var(--border)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                            <Activity size={14} color="var(--success)" className="pulse" />
                            <span style={{ color: 'var(--text-dim)' }}>Orchestrator v1.0.4</span>
                        </div>
                    </div>
                </header>

                {status !== 'active' && role !== 'superadmin' ? (
                    <div className="card" style={{ textAlign: 'center', padding: '5rem 2rem', background: 'rgba(239, 68, 68, 0.05)', border: '1px dashed var(--danger)' }}>
                        <ShieldAlert size={48} color="var(--danger)" style={{ margin: '0 auto 2rem' }} />
                        <h2 style={{ fontSize: '2rem', fontWeight: 800 }}>Shield Lock Active</h2>
                        <p style={{ color: 'var(--text-dim)', maxWidth: '500px', margin: '0 auto 2.5rem', fontSize: '1.1rem', lineHeight: 1.6 }}>
                            Your terminal has been flagged as unauthorized. Please coordinate with an enterprise administrator to establish membership.
                        </p>
                        <button onClick={() => auth.signOut()} className="btn" style={{ background: 'var(--danger)', color: 'white', padding: '1rem 3rem' }}>
                            Release Control
                        </button>
                    </div>
                ) : (
                    <div style={{ animation: 'fadeIn 0.4s ease-out' }}>
                        {activeTab === 'overview' && role === 'superadmin' && <SuperAdminOverview />}
                        {activeTab === 'users' && role === 'superadmin' && <UserApproval />}
                        {activeTab === 'orgs' && role === 'superadmin' && <OrgManagement />}
                        {activeTab === 'sites' && role === 'superadmin' && <SiteManagement />}
                        {activeTab === 'hardware' && role === 'superadmin' && <FleetManagement userRole={role} />}
                        {activeTab === 'stats' && role === 'superadmin' && (
                            <div className="stat-grid">
                                <div className="card stat-card"><Users size={24} color="var(--accent)" /><div className="stat-value">{stats.person}</div><div className="stat-label">People</div></div>
                                <div className="card stat-card"><Car size={24} color="var(--accent)" /><div className="stat-value">{stats.car}</div><div className="stat-label">Cars</div></div>
                                <div className="card stat-card"><Bus size={24} color="var(--accent)" /><div className="stat-value">{stats.bus}</div><div className="stat-label">Buses</div></div>
                                <div className="card stat-card"><Truck size={24} color="var(--accent)" /><div className="stat-value">{stats.truck}</div><div className="stat-label">Trucks</div></div>
                                <div className="card stat-card"><Bike size={24} color="var(--accent)" /><div className="stat-value">{stats.motorcycle}</div><div className="stat-label">Motorcycles</div></div>
                            </div>
                        )}

                        {/* SubAdmin Views */}
                        {role !== 'superadmin' && (
                            <div className="stat-grid">
                                <div className="card stat-card"><Users size={24} color="var(--accent)" /><div className="stat-value">{stats.person}</div><div className="stat-label">People</div></div>
                                <div className="card stat-card"><Car size={24} color="var(--accent)" /><div className="stat-value">{stats.car}</div><div className="stat-label">Cars</div></div>
                                <div className="card stat-card"><Bus size={24} color="var(--accent)" /><div className="stat-value">{stats.bus}</div><div className="stat-label">Buses</div></div>
                                <div className="card stat-card"><Truck size={24} color="var(--accent)" /><div className="stat-value">{stats.truck}</div><div className="stat-label">Trucks</div></div>
                                <div className="card stat-card"><Bike size={24} color="var(--accent)" /><div className="stat-value">{stats.motorcycle}</div><div className="stat-label">Motorcycles</div></div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Dashboard;
