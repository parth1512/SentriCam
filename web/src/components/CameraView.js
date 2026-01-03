import React, { useEffect, useRef, useState, useCallback } from 'react';
import axios from 'axios';
import { FiMapPin, FiEdit2, FiX, FiTrash2, FiPlay, FiSquare, FiAlertCircle, FiRefreshCw, FiLoader, FiVideo } from 'react-icons/fi';
import './CameraView.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5002';

const CameraView = ({ cameraId, socket, cameraName, isActive, onStartCamera, onStopCamera, cameraLocation, isConnected, onUpdateLocation, onDeleteCamera, cameraNumber }) => {
  const videoRef = useRef(null);
  const [detections, setDetections] = useState([]);
  const [fps, setFps] = useState(0);
  const [availableCameras, setAvailableCameras] = useState([]);
  const [selectedCameraIndex, setSelectedCameraIndex] = useState(0);
  const [activeCameraIndex, setActiveCameraIndex] = useState(null); // Track which camera is actually active
  const [loading, setLoading] = useState(false);
  const [showLocationForm, setShowLocationForm] = useState(false);
  const [locationName, setLocationName] = useState(cameraLocation?.name || '');
  const [manualLatitude, setManualLatitude] = useState(cameraLocation?.lat?.toString() || '');
  const [manualLongitude, setManualLongitude] = useState(cameraLocation?.lng?.toString() || '');
  const [coordinatesInput, setCoordinatesInput] = useState(''); // Combined lat,lng input
  const [gettingLocation, setGettingLocation] = useState(false);
  const [refreshingAvailableCameras, setRefreshingAvailableCameras] = useState(false);
  const frameCountRef = useRef(0);
  const lastTimeRef = useRef(Date.now());

  const fetchAvailableCameras = useCallback(async (showLoading = false) => {
    if (showLoading) {
      setRefreshingAvailableCameras(true);
    }
    try {
      const response = await axios.get(`${API_BASE_URL}/api/cameras/available`);
      const cameras = [];
      
      // Use all_cameras if available, otherwise fall back to builtin/external
      if (response.data.all_cameras && response.data.all_cameras.length > 0) {
        // Sort: built-in first, then external
        const sorted = response.data.all_cameras.sort((a, b) => {
          if (a.type === 'Built-in' && b.type !== 'Built-in') return -1;
          if (a.type !== 'Built-in' && b.type === 'Built-in') return 1;
          return a.index - b.index;
        });
        cameras.push(...sorted);
      } else {
        // Fallback: add built-in camera if available
        if (response.data.builtin) {
          cameras.push(response.data.builtin);
        }
        
        // Add ALL external cameras (now it's an array)
        if (response.data.external && Array.isArray(response.data.external)) {
          cameras.push(...response.data.external);
        } else if (response.data.external) {
          // Handle legacy single external camera format
          cameras.push(response.data.external);
        }
      }
      
      if (cameras.length > 0) {
        console.log(`📷 Found ${cameras.length} camera(s):`, cameras);
        setAvailableCameras(cameras);
        // Only update selected index if it's not already set or if current selection is invalid
        setSelectedCameraIndex(prevIndex => {
          const currentSelectionValid = cameras.some(c => c.index === prevIndex);
          if (!currentSelectionValid && cameras.length > 0) {
            return cameras[0].index;
          }
          return prevIndex;
        });
        if (showLoading) {
          console.log(`✅ Refreshed: ${cameras.length} camera(s) available`);
        }
      } else {
        // Fallback to default if API fails
        console.warn('⚠️ No cameras found, using default');
        setAvailableCameras([
          { index: 0, type: 'Built-in', display_name: 'Built-in Camera (Index 0)' }
        ]);
        setSelectedCameraIndex(0);
      }
    } catch (error) {
      console.error('❌ Error fetching available cameras:', error);
      // Fallback
      setAvailableCameras([
        { index: 0, type: 'Built-in', display_name: 'Built-in Camera (Index 0)' }
      ]);
      setSelectedCameraIndex(0);
      if (showLoading) {
        alert('Failed to refresh available cameras. Please check server connection.');
      }
    } finally {
      if (showLoading) {
        setRefreshingAvailableCameras(false);
      }
    }
  }, []); // Empty dependency array since this function doesn't depend on any props or state

  // Sync manual input fields when cameraLocation changes
  useEffect(() => {
    if (cameraLocation?.lat && cameraLocation?.lng) {
      setManualLatitude(cameraLocation.lat.toString());
      setManualLongitude(cameraLocation.lng.toString());
      setCoordinatesInput(`${cameraLocation.lat}, ${cameraLocation.lng}`);
    }
  }, [cameraLocation]);

  // Handle combined coordinates input (e.g., "12.968145, 79.155902")
  const handleCoordinatesInput = (value) => {
    setCoordinatesInput(value);
    
    // Try to parse lat,lng format
    const trimmed = value.trim();
    if (trimmed.includes(',')) {
      const parts = trimmed.split(',').map(p => p.trim());
      if (parts.length === 2) {
        const lat = parseFloat(parts[0]);
        const lng = parseFloat(parts[1]);
        
        if (!isNaN(lat) && !isNaN(lng)) {
          setManualLatitude(lat.toString());
          setManualLongitude(lng.toString());
        }
      }
    }
  };

  useEffect(() => {
    // Fetch available cameras on mount
    fetchAvailableCameras();
    
    // Refresh cameras periodically (every 10 seconds) to catch newly connected cameras
    const interval = setInterval(() => {
      fetchAvailableCameras();
    }, 10000);
    
    return () => clearInterval(interval);
  }, [isConnected, fetchAvailableCameras]); // Include fetchAvailableCameras in dependencies

  // Update locationName when cameraLocation changes
  useEffect(() => {
    if (cameraLocation?.name) {
      setLocationName(cameraLocation.name);
    }
  }, [cameraLocation]);

  useEffect(() => {
    if (!socket) return;

    const handleFrame = (data) => {
      if (videoRef.current) {
        const img = new Image();
        img.src = `data:image/jpeg;base64,${data.frame}`;
        img.onload = () => {
          const canvas = videoRef.current;
          if (canvas) {
            const ctx = canvas.getContext('2d');
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);

            // Draw detections
            if (data.detections) {
              setDetections(data.detections);
              data.detections.forEach(det => {
                const [x1, y1, x2, y2] = det.bbox;
                ctx.strokeStyle = '#00ff00';
                ctx.lineWidth = 3;
                ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
                
                ctx.fillStyle = '#00ff00';
                ctx.font = 'bold 20px Arial';
                ctx.fillText(
                  `${det.plate_number} (${(det.confidence * 100).toFixed(1)}%)`,
                  x1,
                  Math.max(20, y1 - 10)
                );
              });
            }
          }
        };

        // Calculate FPS
        frameCountRef.current++;
        const now = Date.now();
        const elapsed = (now - lastTimeRef.current) / 1000;
        if (elapsed >= 1) {
          setFps(Math.round(frameCountRef.current / elapsed));
          frameCountRef.current = 0;
          lastTimeRef.current = now;
        }
      }
    };

    socket.on(`frame_${cameraId}`, handleFrame);

    return () => {
      socket.off(`frame_${cameraId}`, handleFrame);
    };
  }, [socket, cameraId]);

  const handleStart = () => {
    if (socket && !isActive && isConnected) {
      setLoading(true);
      if (onStartCamera) {
        onStartCamera(cameraId, selectedCameraIndex);
      } else {
        socket.emit('start_camera', { camera_id: cameraId, camera_index: selectedCameraIndex });
      }
      setTimeout(() => setLoading(false), 1000);
    }
  };

  const handleStop = () => {
    if (socket && isActive) {
      if (onStopCamera) {
        onStopCamera(cameraId);
      } else {
        socket.emit('stop_camera', { camera_id: cameraId });
      }
    }
  };

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser');
      return;
    }

    setGettingLocation(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        if (onUpdateLocation) {
          onUpdateLocation(cameraId, {
            lat: latitude,
            lng: longitude,
            name: locationName || cameraLocation?.name || `Camera ${cameraId}`
          });
        }
        // Update manual input fields with geolocation values
        setManualLatitude(latitude.toString());
        setManualLongitude(longitude.toString());
        setGettingLocation(false);
        setShowLocationForm(false);
        alert(`Location updated: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}`);
      },
      (error) => {
        console.error('Error getting location:', error);
        alert('Failed to get location. Please allow location access or enter manually.');
        setGettingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
  };

  const handleUpdateLocation = () => {
    // Try to use manual input first, then fall back to geolocation
    let lat, lng;
    
    if (manualLatitude && manualLongitude) {
      lat = parseFloat(manualLatitude);
      lng = parseFloat(manualLongitude);
      
      if (isNaN(lat) || isNaN(lng)) {
        alert('Please enter valid latitude and longitude values');
        return;
      }
      
      if (lat < -90 || lat > 90) {
        alert('Latitude must be between -90 and 90');
        return;
      }
      
      if (lng < -180 || lng > 180) {
        alert('Longitude must be between -180 and 180');
        return;
      }
    } else if (cameraLocation && cameraLocation.lat && cameraLocation.lng) {
      lat = cameraLocation.lat;
      lng = cameraLocation.lng;
    } else {
      alert('Please enter latitude and longitude, or get your location first');
      return;
    }
    
    if (onUpdateLocation) {
      onUpdateLocation(cameraId, {
        lat: lat,
        lng: lng,
        name: locationName || cameraLocation?.name || `Camera ${cameraId}`
      });
      setShowLocationForm(false);
    }
  };

  // Listen for socket errors
  const [errorMessage, setErrorMessage] = useState(null);

  useEffect(() => {
    if (!socket) return;
    
    const handleError = (error) => {
      const errorMsg = error.message || error;
      console.error('❌ Camera error:', errorMsg);
      setLoading(false);
      setErrorMessage(errorMsg);
      // Clear error after 5 seconds
      setTimeout(() => setErrorMessage(null), 5000);
    };

    socket.on('error', handleError);
    socket.on('camera_started', (data) => {
      if (data.camera_id === cameraId) {
        setLoading(false);
        setErrorMessage(null); // Clear any previous errors
        // Store the active camera index
        if (data.camera_index !== undefined) {
          setActiveCameraIndex(data.camera_index);
        }
        console.log('✅ Camera started:', data);
      }
    });

    socket.on('camera_stopped', (data) => {
      if (data.camera_id === cameraId) {
        setLoading(false);
        setActiveCameraIndex(null); // Clear active camera when stopped
        console.log('🛑 Camera stopped:', data);
      }
    });

    return () => {
      socket.off('error', handleError);
      socket.off('camera_started');
      socket.off('camera_stopped');
    };
  }, [socket, cameraId]);

  // Format location coordinates
  const formatLocation = () => {
    if (!cameraLocation) return 'No location set';
    const lat = cameraLocation.lat?.toFixed(6) || 'N/A';
    const lng = cameraLocation.lng?.toFixed(6) || 'N/A';
    return `${lat}, ${lng}`;
  };

  return (
    <div className="camera-view">
      <div className="camera-header">
        <div className="camera-info">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            {cameraNumber && (
              <span className="camera-number" style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '28px',
                height: '28px',
                borderRadius: '50%',
                backgroundColor: '#00ff88',
                color: '#000000',
                fontSize: '14px',
                fontWeight: 'bold',
                flexShrink: 0,
                boxShadow: '0 0 10px rgba(0, 255, 136, 0.5)'
              }}>
                {cameraNumber}
              </span>
            )}
            <h3 className="camera-name-display">{cameraLocation?.name || cameraId.toUpperCase()}</h3>
            {onDeleteCamera && (
              <button
                onClick={() => {
                  if (window.confirm(`Delete ${cameraLocation?.name || cameraId}?`)) {
                    onDeleteCamera(cameraId);
                  }
                }}
                className="btn-delete-camera"
                title="Delete camera"
              >
                <FiTrash2 />
              </button>
            )}
          </div>
          <div className="camera-location-display">
            <FiMapPin /> {formatLocation()}
            <button
              onClick={() => setShowLocationForm(!showLocationForm)}
              className="btn-edit-location"
              title="Edit location"
            >
              {showLocationForm ? <FiX /> : <FiEdit2 />}
            </button>
          </div>
        </div>
        <div className="camera-status">
          <span className={`status-badge ${isActive ? 'active' : 'inactive'}`}>
            {isActive ? '● Live' : '○ Offline'}
          </span>
          {isActive && <span className="fps-indicator">FPS: {fps}</span>}
          {!isConnected && (
            <span className="status-badge" style={{ background: '#ff9800', color: 'white' }}>
              <FiAlertCircle /> Not Connected
            </span>
          )}
        </div>
      </div>

      {showLocationForm && (
        <div className="location-form-inline">
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <input
              type="text"
              placeholder="Camera name"
              value={locationName}
              onChange={(e) => setLocationName(e.target.value)}
              className="location-input"
            />
            <input
              type="text"
              placeholder="Coordinates (e.g., 12.968145, 79.155902) or paste lat,lng"
              value={coordinatesInput}
              onChange={(e) => handleCoordinatesInput(e.target.value)}
              className="location-input"
              style={{ fontFamily: 'monospace' }}
            />
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="number"
                placeholder="Latitude"
                value={manualLatitude}
                onChange={(e) => {
                  setManualLatitude(e.target.value);
                  if (e.target.value && manualLongitude) {
                    setCoordinatesInput(`${e.target.value}, ${manualLongitude}`);
                  }
                }}
                step="any"
                min="-90"
                max="90"
                className="location-input"
                style={{ flex: '1', minWidth: '120px' }}
              />
              <input
                type="number"
                placeholder="Longitude"
                value={manualLongitude}
                onChange={(e) => {
                  setManualLongitude(e.target.value);
                  if (manualLatitude && e.target.value) {
                    setCoordinatesInput(`${manualLatitude}, ${e.target.value}`);
                  }
                }}
                step="any"
                min="-180"
                max="180"
                className="location-input"
                style={{ flex: '1', minWidth: '120px' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={handleGetLocation}
                disabled={gettingLocation}
                className="btn-get-location"
              >
                {gettingLocation ? <><FiLoader className="spinner-small" /> Getting...</> : <><FiMapPin /> Get My Location</>}
              </button>
              <button
                onClick={handleUpdateLocation}
                className="btn-save-location"
              >
                Save
              </button>
              <button
                onClick={() => {
                  setShowLocationForm(false);
                  setManualLatitude(cameraLocation?.lat?.toString() || '');
                  setManualLongitude(cameraLocation?.lng?.toString() || '');
                  setCoordinatesInput(cameraLocation?.lat && cameraLocation?.lng 
                    ? `${cameraLocation.lat}, ${cameraLocation.lng}` 
                    : '');
                }}
                className="btn-cancel-location"
              >
                Cancel
              </button>
            </div>
          </div>
          {cameraLocation && (cameraLocation.lat || cameraLocation.lng) && (
            <div style={{ marginTop: '8px', fontSize: '12px', color: '#666' }}>
              Current: {cameraLocation.lat?.toFixed(6)}, {cameraLocation.lng?.toFixed(6)}
            </div>
          )}
        </div>
      )}
      
              {!isActive && (
        <div className="camera-controls">
          <div className="camera-selector">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <label>Select Camera:</label>
              <button
                type="button"
                onClick={() => fetchAvailableCameras(true)}
                disabled={refreshingAvailableCameras || !isConnected}
                className="btn-refresh-available-cameras"
                title={!isConnected ? 'Connect to backend first' : 'Refresh available cameras'}
              >
                {refreshingAvailableCameras ? (
                  <FiLoader className="spinner-tiny" />
                ) : (
                  <FiRefreshCw />
                )}
              </button>
            </div>
            <select 
              value={selectedCameraIndex} 
              onChange={(e) => setSelectedCameraIndex(parseInt(e.target.value))}
              disabled={loading}
            >
              {availableCameras.length === 0 ? (
                <option value="">No cameras available</option>
              ) : (
                availableCameras.map(cam => (
                  <option key={cam.index} value={cam.index}>
                    {cam.display_name || `${cam.type} Camera (Index ${cam.index})`}
                  </option>
                ))
              )}
            </select>
            {availableCameras.length > 0 && (
              <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                {availableCameras.length} camera{availableCameras.length > 1 ? 's' : ''} available
              </div>
            )}
          </div>
          <button
            className="btn btn-start-camera"
            onClick={handleStart}
            disabled={loading || !isConnected}
            title={!isConnected ? 'Connect to backend first' : 'Start camera'}
          >
            {loading ? <><FiLoader className="spinner-small" /> Starting...</> : !isConnected ? <><FiAlertCircle /> Connect First</> : <><FiPlay /> Start Camera</>}
          </button>
        </div>
      )}

      {isActive && (
        <div className="camera-controls">
          <button
            className="btn btn-stop-camera"
            onClick={handleStop}
          >
            <FiSquare /> Stop Camera
          </button>
        </div>
      )}

      {errorMessage && (
        <div style={{
          padding: '10px',
          margin: '10px 0',
          background: '#ffebee',
          border: '1px solid #f44336',
          borderRadius: '6px',
          color: '#c62828',
          fontSize: '13px',
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <FiAlertCircle /> {errorMessage}
        </div>
      )}

      <div className="camera-container">
        <canvas ref={videoRef} className="camera-canvas" />
        {!isActive && (
          <div className="camera-placeholder">
            <p><FiVideo /> Camera not active</p>
            <p className="placeholder-hint">Select a camera and click Start</p>
          </div>
        )}
      </div>
      {detections.length > 0 && (
        <div className="detections-overlay">
          <strong>Detected Plates:</strong>
          {detections.map((det, idx) => (
            <span key={idx} className="detection-tag">
              {det.plate_number}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

export default CameraView;


