import React, { useState, useEffect } from 'react';
import { db } from '../firebase';
import { collection, onSnapshot, doc, setDoc, serverTimestamp, deleteDoc, query, where, getDocs } from 'firebase/firestore';
import { Database, Plus, X, Building2, MapPin, Trash2, ShieldCheck } from 'lucide-react';

const SiteManagement = () => {
    const [sites, setSites] = useState([]);
    const [orgs, setOrgs] = useState([]);
    const [isAdding, setIsAdding] = useState(false);
    const [loading, setLoading] = useState(false);

    // Form State
    const [newSiteName, setNewSiteName] = useState('');
    const [selectedOrgId, setSelectedOrgId] = useState('');

    useEffect(() => {
        const unsubscribeOrgs = onSnapshot(collection(db, 'organizations'), (snapshot) => {
            setOrgs(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
        });
        const unsubscribeSites = onSnapshot(collection(db, 'sites'), (snapshot) => {
            setSites(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
        });
        return () => {
            unsubscribeOrgs();
            unsubscribeSites();
        };
    }, []);

    const handleCreateSite = async (e) => {
        e.preventDefault();
        if (!newSiteName || !selectedOrgId) return;
        setLoading(true);

        try {
            const siteSlug = `${selectedOrgId}-${newSiteName.toLowerCase().replace(/[^a-z0-9]/g, '-')}`;
            await setDoc(doc(db, 'sites', siteSlug), {
                name: newSiteName,
                org_id: selectedOrgId,
                status: 'active',
                created_at: serverTimestamp()
            });
            setNewSiteName('');
            setIsAdding(false);
        } catch (err) {
            console.error('Failed to create site', err);
            alert('Error establishing site infrastructure.');
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteSite = async (siteId, siteName) => {
        if (!window.confirm(`Delete site "${siteName}"? This will detach all associated hardware.`)) return;
        try {
            await deleteDoc(doc(db, 'sites', siteId));
        } catch (err) {
            console.error('Delete failed', err);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card" style={{ background: 'rgba(21, 28, 44, 0.4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isAdding ? '2rem' : '0' }}>
                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                        <Database size={24} color="var(--accent)" /> Site Infrastructure
                    </h3>
                    {!isAdding && (
                        <button onClick={() => setIsAdding(true)} className="btn btn-primary">
                            <Plus size={18} /> Provision New Site
                        </button>
                    )}
                </div>

                {isAdding && (
                    <div className="card" style={{ background: '#0b0f19', border: '1px solid var(--accent)', marginTop: '1rem', animation: 'slideDown 0.3s ease-out' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700 }}>
                                <MapPin size={18} color="var(--accent)" /> Location Specification
                            </div>
                            <button onClick={() => setIsAdding(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}><X size={20} /></button>
                        </div>

                        <form onSubmit={handleCreateSite} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    <label style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Site Name</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. North Gate Entrance"
                                        value={newSiteName}
                                        onChange={(e) => setNewSiteName(e.target.value)}
                                        required
                                        className="form-input"
                                        style={{ padding: '0.85rem', borderRadius: '0.5rem', background: 'var(--card)', border: '1px solid var(--border)', color: 'white' }}
                                    />
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    <label style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Parent Organization</label>
                                    <select
                                        value={selectedOrgId}
                                        onChange={(e) => setSelectedOrgId(e.target.value)}
                                        required
                                        style={{ padding: '0.85rem', borderRadius: '0.5rem', background: 'var(--card)', border: '1px solid var(--border)', color: 'white' }}
                                    >
                                        <option value="">Select Organization...</option>
                                        {orgs.filter(o => o.status === 'active').map(org => (
                                            <option key={org.id} value={org.id}>{org.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                                <button type="button" onClick={() => setIsAdding(false)} className="btn" style={{ background: 'transparent', color: 'var(--text-dim)' }}>Cancel</button>
                                <button type="submit" disabled={loading} className="btn btn-primary" style={{ padding: '0 2rem' }}>
                                    {loading ? 'Provisioning...' : 'Establish Site'}
                                </button>
                            </div>
                        </form>
                    </div>
                )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1.25rem' }}>
                {sites.map(site => {
                    const parentOrg = orgs.find(o => o.id === site.org_id);
                    return (
                        <div key={site.id} className="card" style={{ padding: '1.5rem', background: '#0b0f19', border: '1px solid var(--border)', position: 'relative', overflow: 'hidden' }}>
                            <div style={{ position: 'absolute', top: 0, right: 0, width: '4px', height: '100%', background: 'var(--accent)' }}></div>

                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1.25rem' }}>
                                <div>
                                    <div style={{ fontWeight: 700, color: 'white', fontSize: '1.1rem' }}>{site.name}</div>
                                    <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '0.4rem', marginTop: '0.2rem' }}>
                                        <Building2 size={10} /> {parentOrg?.name || 'Unknown Entity'}
                                    </div>
                                </div>
                                <button onClick={() => handleDeleteSite(site.id, site.name)} className="btn" style={{ padding: '5px', background: 'transparent', color: 'var(--danger)', opacity: 0.4 }}><Trash2 size={14} /></button>
                            </div>

                            <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', background: 'rgba(255,255,255,0.03)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)', marginBottom: '1rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                    <span>SITE ID</span>
                                    <span style={{ color: 'white', fontFamily: 'monospace' }}>{site.id.toUpperCase()}</span>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>STATUS</span>
                                    <span style={{ color: 'var(--success)', fontWeight: 700 }}>OPERATIONAL</span>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default SiteManagement;
