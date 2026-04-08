import React, { useState, useEffect } from 'react';
import { db, storage } from '../firebase';
import { doc, updateDoc, serverTimestamp, getDoc } from 'firebase/firestore';
import { ref, getDownloadURL, listAll } from 'firebase/storage';
import { Camera, X, Loader } from 'lucide-react';
import { auth } from '../firebase';

const CrosslineModal = ({ camera, onClose }) => {
    const [loading, setLoading] = useState(true);
    const [snapshotUrl, setSnapshotUrl] = useState(null);
    const [selectedPoints, setSelectedPoints] = useState([]);
    const [existingCrossline, setExistingCrossline] = useState(null);
    const [saving, setSaving] = useState(false);

    // 9 predefined points (normalized 0-1 coordinates)
    const POINTS = [
        { id: 'tl', x: 0, y: 0, label: 'Top-Left' },
        { id: 'tc', x: 0.5, y: 0, label: 'Top-Center' },
        { id: 'tr', x: 1, y: 0, label: 'Top-Right' },
        { id: 'ml', x: 0, y: 0.5, label: 'Mid-Left' },
        { id: 'c', x: 0.5, y: 0.5, label: 'Center' },
        { id: 'mr', x: 1, y: 0.5, label: 'Mid-Right' },
        { id: 'bl', x: 0, y: 1, label: 'Bottom-Left' },
        { id: 'bc', x: 0.5, y: 1, label: 'Bottom-Center' },
        { id: 'br', x: 1, y: 1, label: 'Bottom-Right' }
    ];

    useEffect(() => {
        loadSnapshot();
        loadExistingCrossline();
    }, [camera]);

    const loadSnapshot = async () => {
        try {
            setLoading(true);
            // Try to get the latest snapshot from Firebase Storage
            const storagePath = `snapshots/${camera.org_id}/${camera.camera_id}/`;
            const storageRef = ref(storage, storagePath);

            const result = await listAll(storageRef);
            if (result.items.length > 0) {
                // Get the most recent snapshot (last item)
                const latestSnapshot = result.items[result.items.length - 1];
                const url = await getDownloadURL(latestSnapshot);
                setSnapshotUrl(url);
            } else {
                // No snapshots yet, trigger a new one
                alert('No snapshots available. Click the camera button to capture one first.');
                onClose();
            }
        } catch (error) {
            console.error('Error loading snapshot:', error);
            alert('Failed to load snapshot');
        } finally {
            setLoading(false);
        }
    };

    const loadExistingCrossline = async () => {
        try {
            const cameraDoc = await getDoc(doc(db, 'cameras', camera.id));
            if (cameraDoc.exists() && cameraDoc.data().crossline) {
                const crossline = cameraDoc.data().crossline;
                setExistingCrossline(crossline);

                // Pre-select points if they match predefined points
                const point1Match = POINTS.find(p => p.x === crossline.point1.x && p.y === crossline.point1.y);
                const point2Match = POINTS.find(p => p.x === crossline.point2.x && p.y === crossline.point2.y);

                if (point1Match && point2Match) {
                    setSelectedPoints([point1Match.id, point2Match.id]);
                }
            }
        } catch (error) {
            console.error('Error loading crossline:', error);
        }
    };

    const handlePointClick = (pointId) => {
        if (selectedPoints.includes(pointId)) {
            // Deselect if already selected
            setSelectedPoints(selectedPoints.filter(id => id !== pointId));
        } else if (selectedPoints.length < 2) {
            // Select if less than 2 points selected
            setSelectedPoints([...selectedPoints, pointId]);
        } else {
            // Replace second point if 2 already selected
            setSelectedPoints([selectedPoints[0], pointId]);
        }
    };

    const saveCrossline = async () => {
        if (selectedPoints.length !== 2) {
            alert('Please select exactly 2 points to create a crossline');
            return;
        }

        try {
            setSaving(true);
            const point1 = POINTS.find(p => p.id === selectedPoints[0]);
            const point2 = POINTS.find(p => p.id === selectedPoints[1]);

            const user = auth.currentUser;

            await updateDoc(doc(db, 'cameras', camera.id), {
                crossline: {
                    point1: { x: point1.x, y: point1.y },
                    point2: { x: point2.x, y: point2.y },
                    updated_at: serverTimestamp(),
                    updated_by: user?.email || 'unknown'
                }
            });

            alert('Crossline saved successfully!');
            onClose();
        } catch (error) {
            console.error('Error saving crossline:', error);
            alert('Failed to save crossline');
        } finally {
            setSaving(false);
        }
    };

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 9999
        }}>
            <div style={{
                background: 'var(--card)',
                borderRadius: '1rem',
                padding: '2rem',
                maxWidth: '900px',
                width: '90%',
                maxHeight: '90vh',
                overflow: 'auto',
                position: 'relative'
            }}>
                {/* Close button */}
                <button
                    onClick={onClose}
                    style={{
                        position: 'absolute',
                        top: '1rem',
                        right: '1rem',
                        background: 'transparent',
                        border: 'none',
                        cursor: 'pointer',
                        color: 'var(--text-dim)'
                    }}
                >
                    <X size={24} />
                </button>

                <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Camera size={28} color="var(--accent)" />
                    Crossline Editor - {camera.camera_id}
                </h2>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '4rem' }}>
                        <Loader size={48} color="var(--accent)" className="spinner" />
                        <p style={{ marginTop: '1rem', color: 'var(--text-dim)' }}>Loading snapshot...</p>
                    </div>
                ) : (
                    <>
                        <div style={{
                            position: 'relative',
                            width: '100%',
                            backgroundColor: '#000',
                            borderRadius: '0.5rem',
                            overflow: 'hidden'
                        }}>
                            <img
                                src={snapshotUrl}
                                alt="Camera snapshot"
                                style={{ width: '100%', display: 'block' }}
                                onLoad={(e) => {
                                    // Store image dimensions for point positioning
                                    const img = e.target;
                                    img.parentElement.style.height = `${img.offsetHeight}px`;
                                }}
                            />

                            {/* Overlay points */}
                            {POINTS.map(point => {
                                const isSelected = selectedPoints.includes(point.id);
                                return (
                                    <div
                                        key={point.id}
                                        onClick={() => handlePointClick(point.id)}
                                        style={{
                                            position: 'absolute',
                                            left: `${point.x * 100}%`,
                                            top: `${point.y * 100}%`,
                                            transform: 'translate(-50%, -50%)',
                                            width: '20px',
                                            height: '20px',
                                            borderRadius: '50%',
                                            backgroundColor: isSelected ? 'var(--accent)' : 'rgba(255, 255, 255, 0.5)',
                                            border: isSelected ? '3px solid white' : '2px solid var(--accent)',
                                            cursor: 'pointer',
                                            transition: 'all 0.2s',
                                            zIndex: isSelected ? 10 : 5
                                        }}
                                        title={point.label}
                                    />
                                );
                            })}

                            {/* Draw line between selected points */}
                            {selectedPoints.length === 2 && (() => {
                                const p1 = POINTS.find(p => p.id === selectedPoints[0]);
                                const p2 = POINTS.find(p => p.id === selectedPoints[1]);

                                const x1 = p1.x * 100;
                                const y1 = p1.y * 100;
                                const x2 = p2.x * 100;
                                const y2 = p2.y * 100;

                                const length = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2));
                                const angle = Math.atan2(y2 - y1, x2 - x1) * (180 / Math.PI);

                                return (
                                    <div
                                        style={{
                                            position: 'absolute',
                                            left: `${x1}%`,
                                            top: `${y1}%`,
                                            width: `${length}%`,
                                            height: '3px',
                                            backgroundColor: 'var(--accent)',
                                            transformOrigin: '0 0',
                                            transform: `rotate(${angle}deg)`,
                                            pointerEvents: 'none',
                                            boxShadow: '0 0 10px rgba(56, 189, 248, 0.5)'
                                        }}
                                    />
                                );
                            })()}
                        </div>

                        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>
                                {selectedPoints.length === 0 && 'Click 2 points to draw a counting line'}
                                {selectedPoints.length === 1 && 'Select one more point'}
                                {selectedPoints.length === 2 && 'Counting line ready. Click Save to apply.'}
                            </p>

                            <button
                                onClick={saveCrossline}
                                disabled={selectedPoints.length !== 2 || saving}
                                style={{
                                    padding: '0.75rem 2rem',
                                    backgroundColor: selectedPoints.length === 2 ? 'var(--accent)' : 'var(--border)',
                                    color: selectedPoints.length === 2 ? 'white' : 'var(--text-dim)',
                                    border: 'none',
                                    borderRadius: '0.5rem',
                                    cursor: selectedPoints.length === 2 ? 'pointer' : 'not-allowed',
                                    fontWeight: 600,
                                    opacity: saving ? 0.6 : 1
                                }}
                            >
                                {saving ? 'Saving...' : 'Save Crossline'}
                            </button>
                        </div>
                    </>
                )}
            </div>

            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                .spinner {
                    animation: spin 1s linear infinite;
                }
            `}</style>
        </div>
    );
};

export default CrosslineModal;
