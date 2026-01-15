import React, { useState, useEffect } from 'react';
import { db, auth } from '../firebase';
import { collection, onSnapshot, doc, query, where, getDocs, deleteDoc, addDoc, serverTimestamp } from 'firebase/firestore';
import { Camera, QrCode, Wifi, Activity, ShieldCheck, Building2, MapPin, Search, Trash2, Play, Square, X } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

const FleetManagement = ({ userRole = 'subadmin' }) => {
    const [cameras, setCameras] = useState([]);
    const [sites, setSites] = useState([]);
    const [orgs, setOrgs] = useState([]);
    const [selectedSiteForQR, setSelectedSiteForQR] = useState(null);
    const [hardwareData, setHardwareData] = useState({});
    const [snapshots, setSnapshots] = useState({});
    const [selectedSnapshot, setSelectedSnapshot] = useState(null);
    const [snapshotLoading, setSnapshotLoading] = useState({});

    const isSuperAdmin = userRole === 'superadmin';

    useEffect(() => {
        const unsubscribeCameras = onSnapshot(collection(db, 'cameras'), (snapshot) => {
            const cams = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
            console.log('Cameras loaded:', cams);
            setCameras(cams);
        });
        const unsubscribeSites = onSnapshot(collection(db, 'sites'), (snapshot) => {
            setSites(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
        });
        const unsubscribeOrgs = onSnapshot(collection(db, 'organizations'), (snapshot) => {
            setOrgs(snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() })));
        });

        // Listen to counts collection for hardware data
        const unsubscribeCounts = onSnapshot(collection(db, 'counts'), (snapshot) => {
            const hwMap = {};
            console.log('Processing counts snapshot, docs:', snapshot.docs.length);

            snapshot.docs.forEach(doc => {
                const data = doc.data();
                const serial = data.serial;

                console.log('Count doc:', {
                    serial,
                    hasHardware: !!data.hardware,
                    hardware: data.hardware,
                    timestamp: data.timestamp
                });

                if (serial) {
                    const timestamp = data.timestamp?.toMillis ? data.timestamp.toMillis() : 0;

                    // Keep only the latest data per camera using Serial
                    if (!hwMap[serial] || timestamp > hwMap[serial].ts) {
                        hwMap[serial] = {
                            cpu_temp: data.hardware?.cpu_temp || null,
                            hailo_load: data.hardware?.hailo_load || null,
                            fps: data.hardware?.fps || null,
                            ts: timestamp
                        };
                    }
                }
            });

            console.log('Hardware data map:', hwMap);
            setHardwareData(hwMap);
        });

        return () => {
            unsubscribeCameras();
            unsubscribeSites();
            unsubscribeOrgs();
            unsubscribeCounts();
        };
    }, []);

    const generateQRCodeValue = (site) => {
        return `http://10.42.0.1:8080/onboard?site_id=${site.id}&org_id=${site.org_id}`;
    };

    const handleDeleteCamera = async (cameraId) => {
        if (window.confirm('Are you sure you want to delete this camera unit? This action cannot be undone.')) {
            try {
                await deleteDoc(doc(db, 'cameras', cameraId));
            } catch (error) {
                console.error("Error deleting camera:", error);
                alert("Failed to delete camera.");
            }
        }
    };

    const sendCommand = async (camera, action) => {
        try {
            await addDoc(collection(db, 'commands'), {
                serial: camera.serial,
                camera_id: camera.camera_id,
                action: action, // 'start' or 'stop'
                status: 'pending',
                created_at: serverTimestamp()
            });
            console.log(`Command '${action}' sent to ${camera.camera_id}`);
        } catch (error) {
            console.error('Failed to send command:', error);
            alert('Failed to send command to device');
        }
    };

    const getDeviceStatus = (camera) => {
        const hwData = hardwareData[camera.serial];
        if (!hwData || !hwData.ts) return 'offline';

        const now = Date.now();
        const timeSinceLastData = now - hwData.ts;

        // Green if data received < 30 seconds ago
        return timeSinceLastData < 30000 ? 'online' : 'offline';
    };

    const captureSnapshot = async (camera) => {
        if (!isSuperAdmin) {
            alert('Snapshot capture is restricted to superadmins only');
            return;
        }

        try {
            setSnapshotLoading(prev => ({ ...prev, [camera.serial]: true }));

            const user = auth.currentUser;
            await addDoc(collection(db, 'commands'), {
                serial: camera.serial,
                camera_id: camera.camera_id,
                action: 'snapshot',
                status: 'pending',
                requested_by: user?.email || 'unknown',
                created_at: serverTimestamp()
            });

            console.log(`Snapshot command sent to ${camera.camera_id}`);
        } catch (error) {
            console.error('Failed to capture snapshot:', error);
            alert('Failed to capture snapshot');
        } finally {
            setTimeout(() => {
                setSnapshotLoading(prev => ({ ...prev, [camera.serial]: false }));
            }, 2000);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* 1. Onboarding Section */}
            <div className="card" style={{ background: 'rgba(56, 189, 248, 0.05)', border: '1px solid rgba(56, 189, 248, 0.2)' }}>
                <h3 style={{ margin: '0 0 1.5rem 0', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem', color: 'var(--accent)' }}>
                    <QrCode size={24} /> Hardware Handshake Terminal
                </h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', marginBottom: '2rem', maxWidth: '600px' }}>
                    Generate a provisioning QR code to onboard a new RPi Edge Unit.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '2rem', alignItems: 'start' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        <label style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontWeight: 700, textTransform: 'uppercase' }}>Target Site for Deployment</label>
                        <div style={{ maxHeight: '300px', overflowY: 'auto', border: '1px solid var(--border)', borderRadius: '0.5rem', background: 'var(--card)' }}>
                            {sites.length === 0 ? (
                                <div style={{ padding: '1rem', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-dim)' }}>No sites provisioned yet.</div>
                            ) : (
                                sites.map(site => (
                                    <button
                                        key={site.id}
                                        onClick={() => setSelectedSiteForQR(site)}
                                        style={{
                                            width: '100%', padding: '1rem', textAlign: 'left', background: selectedSiteForQR?.id === site.id ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
                                            border: 'none', borderBottom: '1px solid var(--border)', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '0.2rem'
                                        }}
                                    >
                                        <div style={{ fontWeight: 600, color: selectedSiteForQR?.id === site.id ? 'var(--accent)' : 'white', fontSize: '0.85rem' }}>{site.name}</div>
                                        <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>{orgs.find(o => o.id === site.org_id)?.name}</div>
                                    </button>
                                ))
                            )}
                        </div>
                    </div>

                    <div style={{ background: '#0b0f19', border: '2px dashed var(--border)', borderRadius: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem', minHeight: '300px' }}>
                        {selectedSiteForQR ? (
                            <div style={{ textAlign: 'center', animation: 'fadeIn 0.5s ease-out' }}>
                                <div style={{ background: 'white', padding: '1.5rem', borderRadius: '1rem', display: 'inline-block', marginBottom: '1.5rem', boxShadow: '0 0 40px rgba(56, 189, 248, 0.2)' }}>
                                    <QRCodeSVG value={generateQRCodeValue(selectedSiteForQR)} size={200} level="H" includeMargin={false} />
                                </div>
                                <div style={{ color: 'white', fontWeight: 700, fontSize: '1rem' }}>{selectedSiteForQR.name}</div>
                                <div style={{ color: 'var(--accent)', fontSize: '0.7rem', fontWeight: 800, marginTop: '0.5rem', letterSpacing: '0.1em' }}>SCAN TO ONBOARD</div>
                            </div>
                        ) : (
                            <div style={{ textAlign: 'center', opacity: 0.3 }}>
                                <QrCode size={64} style={{ marginBottom: '1rem' }} />
                                <p>Select a site to generate handshake QR</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* 2. Active Fleet Section */}
            <div className="card" style={{ background: 'rgba(21, 28, 44, 0.4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.25rem' }}>
                        <Camera size={24} color="var(--accent)" /> Hardware Fleet Monitor
                    </h3>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', background: 'var(--card)', padding: '0.4rem 0.75rem', borderRadius: '1rem', border: '1px solid var(--border)' }}>
                            {cameras.length} DISCOVERED UNITS
                        </div>
                    </div>
                </div>

                {cameras.length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '4rem', opacity: 0.5 }}>
                        <Wifi size={48} color="var(--accent)" style={{ marginBottom: '1.5rem' }} />
                        <p>No active units reported to command yet.</p>
                    </div>
                ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '1.25rem' }}>
                        {cameras.map(cam => {
                            const site = sites.find(s => s.id === cam.site_id);
                            // Detect hardware data using serial (best) or camera_id (fallback)
                            const hw = hardwareData[cam.serial] || hardwareData[cam.id] || hardwareData[cam.camera_id];

                            return (
                                <div key={cam.id} className="card" style={{ padding: '1.5rem', background: '#0b0f19', border: '1px solid var(--border)', display: 'flex', gap: '1.5rem', position: 'relative' }}>
                                    <button
                                        onClick={() => handleDeleteCamera(cam.id)}
                                        style={{
                                            position: 'absolute', top: '10px', right: '10px',
                                            background: 'transparent', border: 'none', cursor: 'pointer', color: '#ef4444', opacity: 0.6
                                        }}
                                        title="Delete Camera"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                    <div style={{ width: '60px', height: '60px', background: 'var(--card)', borderRadius: '1rem', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px solid var(--border)', position: 'relative' }}>
                                        <Camera size={24} color="var(--accent)" />
                                        <div style={{ position: 'absolute', bottom: '-4px', right: '-4px', width: '12px', height: '12px', background: getDeviceStatus(cam) === 'online' ? 'var(--success)' : '#ef4444', borderRadius: '50%', border: '2px solid #0b0f19' }}></div>

                                        {/* Control Buttons */}
                                        <div style={{ display: 'flex', gap: '0.25rem', marginTop: '0.5rem', position: 'absolute', bottom: '-30px' }}>
                                            <button
                                                onClick={() => isSuperAdmin && sendCommand(cam, 'start')}
                                                disabled={!isSuperAdmin}
                                                style={{
                                                    background: isSuperAdmin ? 'rgba(34, 197, 94, 0.1)' : 'rgba(100, 100, 100, 0.1)',
                                                    border: `1px solid ${isSuperAdmin ? 'rgba(34, 197, 94, 0.3)' : 'rgba(100, 100, 100, 0.3)'}`,
                                                    borderRadius: '0.4rem',
                                                    padding: '0.3rem',
                                                    cursor: isSuperAdmin ? 'pointer' : 'not-allowed',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    opacity: isSuperAdmin ? 1 : 0.5
                                                }}
                                                title={isSuperAdmin ? "Start Detection" : "Superadmin only"}
                                            >
                                                <Play size={12} color={isSuperAdmin ? "var(--success)" : "#888"} />
                                            </button>
                                            <button
                                                onClick={() => isSuperAdmin && sendCommand(cam, 'stop')}
                                                disabled={!isSuperAdmin}
                                                style={{
                                                    background: isSuperAdmin ? 'rgba(239, 68, 68, 0.1)' : 'rgba(100, 100, 100, 0.1)',
                                                    border: `1px solid ${isSuperAdmin ? 'rgba(239, 68, 68, 0.3)' : 'rgba(100, 100, 100, 0.3)'}`,
                                                    borderRadius: '0.4rem',
                                                    padding: '0.3rem',
                                                    cursor: isSuperAdmin ? 'pointer' : 'not-allowed',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    opacity: isSuperAdmin ? 1 : 0.5
                                                }}
                                                title={isSuperAdmin ? "Stop Detection" : "Superadmin only"}
                                            >
                                                <Square size={12} color={isSuperAdmin ? "#ef4444" : "#888"} />
                                            </button>
                                            <button
                                                onClick={() => isSuperAdmin && captureSnapshot(cam)}
                                                disabled={!isSuperAdmin || snapshotLoading[cam.serial]}
                                                style={{
                                                    background: isSuperAdmin ? 'rgba(56, 189, 248, 0.1)' : 'rgba(100, 100, 100, 0.1)',
                                                    border: `1px solid ${isSuperAdmin ? 'rgba(56, 189, 248, 0.3)' : 'rgba(100, 100, 100, 0.3)'}`,
                                                    borderRadius: '0.4rem',
                                                    padding: '0.3rem',
                                                    cursor: isSuperAdmin && !snapshotLoading[cam.serial] ? 'pointer' : 'not-allowed',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    opacity: isSuperAdmin && !snapshotLoading[cam.serial] ? 1 : 0.5
                                                }}
                                                title={isSuperAdmin ? (snapshotLoading[cam.serial] ? "Capturing..." : "Capture Snapshot") : "Superadmin only"}
                                            >
                                                <Camera size={12} color={isSuperAdmin ? "var(--accent)" : "#888"} />
                                            </button>
                                        </div>
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                                            <div style={{ fontWeight: 700, color: 'white' }}>{cam.camera_id || `UNIT-${(cam.serial || cam.id).slice(-4).toUpperCase()}`}</div>
                                            <div style={{ fontSize: '0.6rem', fontWeight: 800, color: 'var(--success)', marginRight: '20px' }}>ONLINE</div>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.75rem', color: 'var(--text-dim)', marginBottom: '1rem' }}>
                                            <MapPin size={12} /> {site?.name || 'Unassigned Site'}
                                        </div>

                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            <div style={{ flex: 1, padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.4rem', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                                <span style={{ fontSize: '0.55rem', color: 'var(--text-dim)', fontWeight: 700 }}>TEMP</span>
                                                <span style={{ fontSize: '0.8rem', color: 'white', fontWeight: 600 }}>
                                                    {hw && hw.cpu_temp != null ? `${hw.cpu_temp}°C` : '--'}
                                                </span>
                                            </div>
                                            <div style={{ flex: 1, padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.4rem', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                                <span style={{ fontSize: '0.55rem', color: 'var(--text-dim)', fontWeight: 700 }}>HAILO LOAD</span>
                                                <span style={{ fontSize: '1.1rem', color: 'white', fontWeight: 600 }}>
                                                    {hw && hw.hailo_load != null ? `${hw.hailo_load}%` : '--'}
                                                </span>
                                            </div>
                                            <div style={{ flex: 1, padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.4rem', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
                                                <span style={{ fontSize: '0.55rem', color: 'var(--text-dim)', fontWeight: 700 }}>FPS</span>
                                                <span style={{ fontSize: '0.8rem', color: 'white', fontWeight: 600 }}>
                                                    {hw && hw.fps != null ? hw.fps : '--'}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default FleetManagement;
