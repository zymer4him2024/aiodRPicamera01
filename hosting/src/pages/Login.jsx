import React, { useState } from 'react';
import { auth, googleProvider, db } from '../firebase';
import { signInWithPopup, signOut } from 'firebase/auth';
import { doc, getDoc, collection, query, where, getDocs, updateDoc, serverTimestamp } from 'firebase/firestore';
import { LogIn, ShieldAlert } from 'lucide-react';

const Login = () => {
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleGoogleLogin = async () => {
        setLoading(true);
        setError('');
        try {
            const result = await signInWithPopup(auth, googleProvider);
            const user = result.user;

            // 1. Check custom claims for SuperAdmin
            const tokenResult = await user.getIdTokenResult(true);
            const role = tokenResult.claims.role;

            if (role === 'superadmin') {
                setLoading(false);
                return; // Normal flow for SuperAdmin
            }

            // 2. For SubAdmins, we need to verify they are pre-authorized
            // First, try direct lookup by UID
            let userDoc = await getDoc(doc(db, 'users', user.uid));
            let userData = userDoc.data();

            // If UID doc doesn't exist, try lookup by email (to handle pre-authorizations)
            if (!userData) {
                const q = query(collection(db, 'users'), where('email', '==', user.email.toLowerCase()));
                const querySnapshot = await getDocs(q);

                if (!querySnapshot.empty) {
                    const invitationDoc = querySnapshot.docs[0];
                    userData = invitationDoc.data();

                    // If we found them by email, "migrate" the record to their real UID
                    if (userData.status === 'active') {
                        await updateDoc(doc(db, 'users', user.uid), {
                            ...userData,
                            full_name: user.displayName,
                            last_login: serverTimestamp()
                        });
                        // Optional: remove the invitation placeholder
                        if (invitationDoc.id.startsWith('invited-')) {
                            // Keep it or delete it—we'll keep it for now but the UID doc is the new master.
                        }
                    }
                }
            }

            // Final check on localized/fetched status
            if (!userData || userData.status !== 'active') {
                await signOut(auth);
                setError('Identity Denied: Your email has not been pre-registered by an enterprise administrator.');
                return;
            }

        } catch (err) {
            console.error(err);
            setError('System Access Failed: Unable to verify credentials with the secure gateway.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh',
            background: 'linear-gradient(135deg, #0b0f19 0%, #1a2a47 100%)',
            color: 'white'
        }}>
            <div className="card" style={{
                width: '450px',
                padding: '3.5rem',
                textAlign: 'center',
                background: 'rgba(21, 28, 44, 0.8)',
                backdropFilter: 'blur(10px)',
                border: '1px solid var(--border)',
                boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
            }}>
                <div style={{ marginBottom: '3rem' }}>
                    <div style={{
                        width: '80px', height: '80px', background: 'var(--accent-glow)',
                        borderRadius: '1.5rem', display: 'flex', alignItems: 'center',
                        justifyContent: 'center', margin: '0 auto 1.5rem',
                        border: '1px solid var(--accent)'
                    }}>
                        <LogIn size={40} color="var(--accent)" />
                    </div>
                    <h1 style={{ color: 'var(--text-main)', fontSize: '2.5rem', marginBottom: '0.5rem', letterSpacing: '-0.02em' }}>AIOD Intelligence</h1>
                    <p style={{ color: 'var(--text-dim)', fontSize: '1.1rem' }}>Enterprise Access Gateway</p>
                </div>

                <div style={{ marginBottom: '2.5rem' }}>
                    {error ? (
                        <div style={{
                            background: 'rgba(239, 68, 68, 0.1)', border: '1px solid var(--danger)',
                            padding: '1.25rem', borderRadius: '0.75rem', marginBottom: '2rem',
                            display: 'flex', gap: '1rem', alignItems: 'start', textAlign: 'left'
                        }}>
                            <ShieldAlert size={20} color="var(--danger)" style={{ flexShrink: 0, marginTop: '2px' }} />
                            <p style={{ color: 'var(--danger)', fontSize: '0.85rem', margin: 0, lineHeight: 1.5 }}>{error}</p>
                        </div>
                    ) : (
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', marginBottom: '2rem' }}>
                            Authorized Personnel Only. Please authenticate with your pre-registered Google identity.
                        </p>
                    )}

                    <button
                        onClick={handleGoogleLogin}
                        disabled={loading}
                        className="btn btn-primary"
                        style={{
                            width: '100%',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '1rem',
                            fontSize: '1.1rem',
                            padding: '1.25rem',
                            background: 'white',
                            color: '#0b0f19',
                            boxShadow: '0 4px 15px rgba(0,0,0,0.2)',
                            fontWeight: 700,
                            cursor: loading ? 'not-allowed' : 'pointer'
                        }}
                    >
                        <img src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" width="20" alt="Google" />
                        {loading ? 'Verifying Identity...' : 'Sign in with Google'}
                    </button>
                </div>

                <div style={{ marginTop: '2.5rem', paddingTop: '2rem', borderTop: '1px solid var(--border)' }}>
                    <p style={{ color: 'var(--text-dim)', fontSize: '0.7rem', opacity: 0.5, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                        Secured by Multi-Agent AI Core
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;
