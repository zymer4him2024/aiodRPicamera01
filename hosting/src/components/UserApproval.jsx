import React, { useState, useEffect } from 'react';
import { db, auth } from '../firebase';
import { collection, onSnapshot, doc, updateDoc, query, where, deleteDoc, getDocs, writeBatch, setDoc, serverTimestamp } from 'firebase/firestore';
import { UserCheck, UserX, Clock, Building2, User, ShieldAlert, Plus, X } from 'lucide-react';

const UserApproval = () => {
    const [pendingOrgs, setPendingOrgs] = useState([]);
    const [isAddingOrg, setIsAddingOrg] = useState(false);
    const [newOrgName, setNewOrgName] = useState('');
    const [subAdminEmail, setSubAdminEmail] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const unsubscribeOrgs = onSnapshot(
            query(collection(db, 'organizations'), where('status', '==', 'pending')),
            (snapshot) => {
                setPendingOrgs(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
            }
        );

        return () => {
            unsubscribeOrgs();
        };
    }, []);

    const handleCreateOrg = async (e) => {
        e.preventDefault();
        if (!newOrgName) return;
        setLoading(true);

        try {
            const orgSlug = newOrgName.toLowerCase().replace(/[^a-z0-9]/g, '-');

            await setDoc(doc(db, 'organizations', orgSlug), {
                name: newOrgName,
                created_at: serverTimestamp(),
                status: 'pending'
            });

            if (subAdminEmail) {
                const userSlug = subAdminEmail.replace(/[@.]/g, '-');
                await setDoc(doc(db, 'users', `invited-${userSlug}`), {
                    email: subAdminEmail.toLowerCase(),
                    role: 'subadmin',
                    org_id: orgSlug,
                    status: 'pending',
                    created_at: serverTimestamp()
                });
            }

            setNewOrgName('');
            setSubAdminEmail('');
            setIsAddingOrg(false);
            alert(`Organization "${newOrgName}" registered. It will appear in the queue below for final approval.`);
        } catch (err) {
            console.error('Failed to create org', err);
            alert('Failed to register organization.');
        } finally {
            setLoading(false);
        }
    };

    const handleApproveOrg = async (orgId) => {
        try {
            const q = query(collection(db, 'users'), where('org_id', '==', orgId), where('status', '==', 'pending'));
            const userSnapshot = await getDocs(q);

            const batch = writeBatch(db);

            batch.update(doc(db, 'organizations', orgId), {
                status: 'active',
                approved_at: serverTimestamp()
            });

            userSnapshot.forEach(userDoc => {
                batch.update(userDoc.ref, {
                    status: 'active',
                    approved_at: serverTimestamp()
                });
            });

            await batch.commit();
            alert(`Organization and associated SubAdmins have been granted access.`);
        } catch (err) {
            console.error('Approval failed', err);
            alert('Failed to process approval.');
        }
    };

    const handleRejectOrg = async (orgId) => {
        if (!window.confirm('Reject and delete this organization request?')) return;
        try {
            await deleteDoc(doc(db, 'organizations', orgId));
        } catch (err) {
            console.error('Rejection failed', err);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* 1. Register New Organization Section */}
            <div className="card" style={{ background: 'rgba(21, 28, 44, 0.4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isAddingOrg ? '1.5rem' : '0' }}>
                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                        <Plus size={24} color="var(--accent)" /> Identity Registration
                    </h3>
                    {!isAddingOrg && (
                        <button onClick={() => setIsAddingOrg(true)} className="btn btn-primary" style={{ padding: '0.6rem 1.25rem', fontSize: '0.85rem' }}>
                            <Plus size={18} /> New Organization
                        </button>
                    )}
                </div>

                {isAddingOrg && (
                    <div className="card" style={{ background: '#0b0f19', border: '1px solid var(--accent)', marginTop: '1rem', animation: 'slideDown 0.3s ease-out' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700 }}>
                                <Building2 size={18} color="var(--accent)" /> Register Enterprise Unit
                            </div>
                            <button onClick={() => setIsAddingOrg(false)} style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}>
                                <X size={20} />
                            </button>
                        </div>

                        <form onSubmit={handleCreateOrg} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    <label style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Organization Name</label>
                                    <input
                                        type="text"
                                        placeholder="e.g. Gotham City Traffic"
                                        value={newOrgName}
                                        onChange={(e) => setNewOrgName(e.target.value)}
                                        required
                                        style={{ padding: '0.85rem', borderRadius: '0.5rem', background: 'var(--card)', border: '1px solid var(--border)', color: 'white' }}
                                    />
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    <label style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>SubAdmin Email</label>
                                    <input
                                        type="email"
                                        placeholder="e.g. admin@gotham.com"
                                        value={subAdminEmail}
                                        onChange={(e) => setSubAdminEmail(e.target.value)}
                                        style={{ padding: '0.85rem', borderRadius: '0.5rem', background: 'var(--card)', border: '1px solid var(--border)', color: 'white' }}
                                    />
                                </div>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem' }}>
                                <button type="button" onClick={() => setIsAddingOrg(false)} className="btn" style={{ background: 'transparent', color: 'var(--text-dim)' }}>Cancel</button>
                                <button type="submit" disabled={loading} className="btn btn-primary" style={{ padding: '0 2rem' }}>
                                    {loading ? 'Registering...' : 'Confirm Registration'}
                                </button>
                            </div>
                        </form>
                    </div>
                )}
            </div>

            {/* 2. Company Approval Queue Section */}
            <div className="card" style={{ background: 'rgba(21, 28, 44, 0.4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                        <Clock size={24} color="var(--accent)" /> Company Approval Queue
                    </h3>
                    <span style={{ background: 'var(--accent-glow)', color: 'var(--accent)', padding: '0.25rem 0.75rem', borderRadius: '1rem', fontSize: '0.7rem', fontWeight: 700 }}>
                        {pendingOrgs.length} PENDING
                    </span>
                </div>

                {pendingOrgs.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '3rem', border: '1px dashed var(--border)', borderRadius: '1rem' }}>
                        <p style={{ color: 'var(--text-dim)', margin: 0 }}>No pending organization requests found.</p>
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {pendingOrgs.map(org => (
                            <div key={org.id} className="card" style={{ background: '#0b0f19', border: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1.5rem 2rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                                    <div style={{ width: '44px', height: '44px', background: 'var(--card)', borderRadius: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border)' }}>
                                        <Building2 size={22} color="var(--accent)" />
                                    </div>
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: '1.1rem', color: 'white' }}>{org.name}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>ID: {org.id.toUpperCase()}</div>
                                    </div>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <button onClick={() => handleRejectOrg(org.id)} className="btn" style={{ background: 'rgba(239, 68, 68, 0.05)', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>Reject</button>
                                    <button onClick={() => handleApproveOrg(org.id)} className="btn btn-primary" style={{ padding: '0 1.5rem' }}>Grant & Activate</button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default UserApproval;
