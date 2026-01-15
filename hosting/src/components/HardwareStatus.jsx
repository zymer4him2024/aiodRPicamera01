import React, { useState, useEffect } from 'react';
import { db } from '../firebase';
import { collection, query, where, orderBy, limit, onSnapshot } from 'firebase/firestore';
import { Camera, Thermometer, Cpu, Activity } from 'lucide-react';

const HardwareStatus = ({ cameraId, orgId }) => {
    const [hwData, setHwData] = useState({
        cpu_temp: null,
        hailo_temp: null,
        hailo_load: null,
        fps: null,
        status: 'offline'
    });

    useEffect(() => {
        if (!cameraId && !orgId) return;

        const countsRef = collection(db, 'counts');
        let q;

        if (cameraId) {
            // Query by specific camera
            q = query(
                countsRef,
                where('camera_id', '==', cameraId),
                orderBy('timestamp', 'desc'),
                limit(1)
            );
        } else if (orgId) {
            // Query by org (latest from any camera)
            q = query(
                countsRef,
                where('org_id', '==', orgId),
                orderBy('timestamp', 'desc'),
                limit(1)
            );
        }

        const unsubscribe = onSnapshot(q, (snapshot) => {
            if (!snapshot.empty) {
                const latest = snapshot.docs[0].data();
                const hw = latest.hardware || {};
                setHwData({
                    cpu_temp: hw.cpu_temp,
                    hailo_temp: hw.hailo_temp,
                    hailo_load: hw.hailo_load,
                    fps: hw.fps,
                    status: 'online',
                    camera_id: latest.camera_id,
                    site_id: latest.site_id
                });
            } else {
                setHwData(prev => ({ ...prev, status: 'offline' }));
            }
        }, (error) => {
            console.error('Hardware status listener error:', error);
        });

        return () => unsubscribe();
    }, [cameraId, orgId]);

    const MetricCard = ({ label, value, unit, icon: Icon, color = 'var(--accent)' }) => (
        <div style={{
            background: 'rgba(21, 28, 44, 0.4)',
            border: '1px solid var(--border)',
            borderRadius: '1rem',
            padding: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem'
        }}>
            <div style={{
                width: '40px',
                height: '40px',
                background: `${color}11`,
                borderRadius: '0.75rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: `1px solid ${color}33`
            }}>
                <Icon size={20} color={color} />
            </div>
            <div style={{ flex: 1 }}>
                <div style={{
                    fontSize: '0.7rem',
                    color: 'var(--text-dim)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: '0.25rem'
                }}>{label}</div>
                <div style={{
                    fontSize: '1.5rem',
                    fontWeight: 700,
                    color: 'white'
                }}>
                    {value !== null && value !== undefined ? `${value}${unit}` : '--'}
                </div>
            </div>
        </div>
    );

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '0.5rem'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Camera size={20} color="var(--accent)" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>
                        {hwData.camera_id || 'Hardware Status'}
                    </h3>
                </div>
                <div style={{
                    padding: '0.4rem 0.8rem',
                    borderRadius: '0.5rem',
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    background: hwData.status === 'online' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    color: hwData.status === 'online' ? 'var(--success)' : 'var(--danger)',
                    border: `1px solid ${hwData.status === 'online' ? 'var(--success)' : 'var(--danger)'}33`
                }}>
                    {hwData.status}
                </div>
            </div>

            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                gap: '1rem'
            }}>
                <MetricCard
                    label="TEMP"
                    value={hwData.cpu_temp}
                    unit="°C"
                    icon={Thermometer}
                    color="#f59e0b"
                />
                <MetricCard
                    label="HAILO LOAD"
                    value={hwData.hailo_load}
                    unit="%"
                    icon={Cpu}
                    color="var(--accent)"
                />
                <MetricCard
                    label="FPS"
                    value={hwData.fps}
                    unit=""
                    icon={Activity}
                    color="var(--success)"
                />
            </div>

            {hwData.site_id && (
                <div style={{
                    fontSize: '0.75rem',
                    color: 'var(--text-dim)',
                    marginTop: '0.5rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem'
                }}>
                    <div style={{
                        width: '6px',
                        height: '6px',
                        borderRadius: '50%',
                        background: 'var(--accent)'
                    }} />
                    {hwData.site_id}
                </div>
            )}
        </div>
    );
};

export default HardwareStatus;
