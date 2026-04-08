import React, { useState, useEffect } from 'react';
import { db } from '../firebase';
import { doc, setDoc, serverTimestamp } from 'firebase/firestore';
import { Scanner } from '@yudiel/react-qr-scanner';
import { QrCode, Wifi, ShieldCheck, Activity, Cpu, CheckCircle2, AlertCircle } from 'lucide-react';

const OnboardingPortal = () => {
    const [scannedData, setScannedData] = useState(null);
    const [hardwareId, setHardwareId] = useState('');
    const [status, setStatus] = useState('idle'); // idle, scanning, provisioned, error
    const [error, setError] = useState('');

    const handleScan = (result) => {
        if (result) {
            try {
                const data = JSON.parse(result[0].rawValue);
                if (data.org_id && data.site_id) {
                    setScannedData(data);
                    setStatus('provisioning');
                    autoProvision(data);
                } else {
                    setError('Invalid QR: Missing site metadata.');
                }
            } catch (err) {
                setError('Invalid QR format.');
            }
        }
    };

    const autoProvision = async (data) => {
        // In a real scenario, we'd GET the hardware ID from the RPi's local API.
        // For this demo/first-pass, we'll generate or ask for a mock hardware ID.
        const mockHwId = `RPi5-B827EB-${Math.random().toString(36).substring(7).toUpperCase()}`;
        setHardwareId(mockHwId);

        try {
            await setDoc(doc(db, 'handshakes', mockHwId), {
                hardware_id: mockHwId,
                org_id: data.org_id,
                site_id: data.site_id,
                status: 'pending',
                requested_at: serverTimestamp(),
                provisioning_key: data.provisioning_key
            });
            setStatus('provisioned');
        } catch (err) {
            console.error(err);
            setError('Handshake failed: Permission denied or network error.');
            setStatus('error');
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: '#0b0f19', color: 'white', display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2rem' }}>
            {/* Header */}
            <header style={{ textAlign: 'center', marginBottom: '3rem', marginTop: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: 'var(--accent)', justifyContent: 'center', marginBottom: '0.5rem' }}>
                    <ShieldCheck size={32} />
                    <h1 style={{ fontSize: '1.75rem', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>AIOD FIELD ONBOARDING</h1>
                </div>
                <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>Secure Hardware-to-Backend Binding Terminal</p>
            </header>

            <div style={{ width: '100%', maxWidth: '400px' }}>
                {status === 'idle' && (
                    <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                        <div style={{ width: '80px', height: '80px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                            <QrCode size={40} color="var(--accent)" />
                        </div>
                        <h2 style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>Initiate Handshake</h2>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', marginBottom: '2rem', lineHeight: 1.5 }}>
                            Scan the provisioning QR code from the SuperAdmin dashboard to bind this hardware.
                        </p>
                        <button onClick={() => setStatus('scanning')} className="btn btn-primary" style={{ width: '100%', padding: '1rem' }}>
                            Start QR Scanner
                        </button>
                    </div>
                )}

                {status === 'scanning' && (
                    <div style={{ borderRadius: '1.5rem', overflow: 'hidden', border: '2px solid var(--accent)', boxShadow: '0 0 30px rgba(56, 189, 248, 0.2)' }}>
                        <Scanner
                            onScan={handleScan}
                            onError={(err) => setError(err.message)}
                            styles={{ container: { width: '100%', aspectRatio: '1/1' } }}
                        />
                        <div style={{ padding: '1.5rem', textAlign: 'center', background: '#0b0f19' }}>
                            <p style={{ margin: 0, color: 'var(--accent)', fontWeight: 700, fontSize: '0.8rem', letterSpacing: '0.1em' }}>ALIGN QR WITHIN FRAME</p>
                        </div>
                    </div>
                )}

                {status === 'provisioning' && (
                    <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
                        <Activity className="pulse" size={48} color="var(--accent)" style={{ margin: '0 auto 2rem' }} />
                        <h3>Negotiating Handshake...</h3>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', marginTop: '1rem' }}>
                            Connecting to AIOD Global Command...
                        </p>
                    </div>
                )}

                {status === 'provisioned' && (
                    <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem', border: '1px solid var(--success)', background: 'rgba(34, 197, 94, 0.05)' }}>
                        <CheckCircle2 size={64} color="var(--success)" style={{ margin: '0 auto 2rem' }} />
                        <h2 style={{ fontSize: '1.5rem', color: 'white', marginBottom: '1rem' }}>Handshake Pending</h2>
                        <div style={{ background: 'rgba(255,255,255,0.03)', padding: '1rem', borderRadius: '0.75rem', border: '1px solid var(--border)', marginBottom: '2rem', textAlign: 'left' }}>
                            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                <Cpu size={16} color="var(--text-dim)" />
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>HW ID: {hardwareId}</span>
                            </div>
                            <div style={{ display: 'flex', gap: '0.75rem' }}>
                                <Wifi size={16} color="var(--text-dim)" />
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Local Wifi: <span style={{ color: 'var(--success)' }}>AIOD-RPi-CONF</span></span>
                            </div>
                        </div>
                        <p style={{ fontSize: '0.9rem', color: 'white', fontWeight: 600, marginBottom: '0.5rem' }}>Ready for Command Approval</p>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', lineHeight: 1.5 }}>
                            The SuperAdmin has been notified. This unit will start sending data once approved.
                        </p>
                    </div>
                )}

                {status === 'error' && (
                    <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem', border: '1px solid var(--danger)', background: 'rgba(239, 68, 68, 0.05)' }}>
                        <AlertCircle size={64} color="var(--danger)" style={{ margin: '0 auto 2rem' }} />
                        <h2 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>Handshake Failed</h2>
                        <p style={{ color: 'var(--text-dim)', fontSize: '0.85rem', marginBottom: '2rem' }}>{error}</p>
                        <button onClick={() => setStatus('idle')} className="btn btn-primary" style={{ width: '100%' }}>Retry Onboarding</button>
                    </div>
                )}
            </div>

            <footer style={{ marginTop: 'auto', paddingTop: '3rem', opacity: 0.5, fontSize: '0.7rem', display: 'flex', gap: '1.5rem' }}>
                <div>HW HANDSHAKE v2.1</div>
                <div>SECURE SESSION: ACTIVE</div>
            </footer>
        </div>
    );
};

export default OnboardingPortal;
