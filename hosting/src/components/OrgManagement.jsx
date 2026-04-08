import React, { useState, useEffect } from 'react';
import { db } from '../firebase';
import { collection, onSnapshot, doc, serverTimestamp, deleteDoc, query, where, getDocs } from 'firebase/firestore';
import { Users, Building2, Trash2, Clock } from 'lucide-react';

const OrgManagement = () => {
    const [orgs, setOrgs] = useState([]);

    useEffect(() => {
        const unsubscribe = onSnapshot(collection(db, 'organizations'), (snapshot) => {
            setOrgs(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
        });
        return unsubscribe;
    }, []);

    const handleDeleteOrg = async (orgId, orgName) => {
        if (!window.confirm(`Are you sure you want to PERMANENTLY DELETE "${orgName}"? \n\nThis will ALSO DELETE all associated SITES and CAMERAS. This action cannot be undone.`)) return;

        try {
            // 1. Delete associated Cameras
            const camerasQuery = query(collection(db, 'cameras'), where('org_id', '==', orgId));
            const cameraSnaps = await getDocs(camerasQuery);
            const deleteCamerasPromises = cameraSnaps.docs.map(doc => deleteDoc(doc.ref));
            await Promise.all(deleteCamerasPromises);

            // 2. Delete associated Sites
            const sitesQuery = query(collection(db, 'sites'), where('org_id', '==', orgId));
            const siteSnaps = await getDocs(sitesQuery);
            const deleteSitesPromises = siteSnaps.docs.map(doc => deleteDoc(doc.ref));
            await Promise.all(deleteSitesPromises);

            // 3. Delete the Organization itself
            await deleteDoc(doc(db, 'organizations', orgId));

            // Success is handled by onSnapshot update
        } catch (err) {
            console.error('Delete failed', err);
            alert(`Failed to delete organization: ${err.message}`);
        }
    };

    return (
        <div className="card" style={{ background: 'rgba(21, 28, 44, 0.4)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                    <Building2 size={24} color="var(--accent)" /> Managed Organizations
                </h3>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', background: 'var(--card)', padding: '0.4rem 0.75rem', borderRadius: '1rem', border: '1px solid var(--border)' }}>
                    {orgs.length} TOTAL UNITS
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.25rem' }}>
                {orgs.map(org => (
                    <div key={org.id} className="card" style={{ padding: '1.5rem', background: '#0b0f19', border: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '1.5rem' }}>
                            <div>
                                <div style={{ fontWeight: 700, color: 'white', fontSize: '1.1rem' }}>{org.name}</div>
                                <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'monospace', marginTop: '0.2rem' }}>{org.id.toUpperCase()}</div>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <div style={{
                                    padding: '0.25rem 0.6rem', borderRadius: '0.4rem',
                                    background: org.status === 'active' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                    color: org.status === 'active' ? 'var(--success)' : 'var(--danger)',
                                    fontSize: '0.6rem', fontWeight: 800, border: '1px solid currentColor', opacity: 0.8
                                }}>
                                    {org.status?.toUpperCase() || 'PENDING'}
                                </div>
                                <button onClick={() => handleDeleteOrg(org.id, org.name)} className="btn" style={{ padding: '5px', background: 'transparent', color: 'var(--danger)', opacity: 0.6 }}><Trash2 size={14} /></button>
                            </div>
                        </div>
                        <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <Clock size={14} color="var(--text-dim)" />
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{org.status === 'active' ? 'Node Operational' : 'Awaiting Approval'}</div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default OrgManagement;
