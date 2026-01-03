import React, { useState, useEffect } from 'react';
import io from 'socket.io-client';
import axios from 'axios';
import { 
  FiWifi, 
  FiWifiOff, 
  FiCamera, 
  FiRefreshCw, 
  FiPlus, 
  FiX,
  FiLoader,
  FiVideo,
  FiPlay,
  FiSquare,
  FiAlertCircle,
  FiCheckCircle,
  FiXCircle,
  FiMapPin,
  FiSearch,
  FiSettings,
  FiPackage
} from 'react-icons/fi';
import CameraView from './components/CameraView';
import TrialCameraView from './components/TrialCameraView';
import CampusMap from './components/CampusMap';
import DetectionList from './components/DetectionList';
import VehicleForm from './components/VehicleForm';
import AddCameraModal from './components/AddCameraModal';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5002';

function App() {
  const [socket, setSocket] = useState(null);
  const [cameras, setCameras] = useState({});
  const [nextCameraId, setNextCameraId] = useState(1);
  const [detections, setDetections] = useState({});
  const [vehicleRanges, setVehicleRanges] = useState({});
  const [activeTimers, setActiveTimers] = useState({});
  const [selectedPlate, setSelectedPlate] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [showAddCameraModal, setShowAddCameraModal] = useState(false);
  const [refreshingCameras, setRefreshingCameras] = useState(false);
  const [trialMode, setTrialMode] = useState(false);

  // Socket connection management
  const connectToServer = () => {
    if (socket && socket.connected) {
      console.log('Already connected');
      return;
    }

    setIsConnecting(true);
    console.log('🔄 Connecting to server...');

    // Close existing socket if any
    if (socket) {
      socket.close();
    }

    // Initialize socket connection with reconnection settings
    const newSocket = io(API_BASE_URL, {
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: Infinity,
      timeout: 20000,
      transports: ['websocket', 'polling']
    });
    setSocket(newSocket);

    newSocket.on('connect', () => {
      setIsConnected(true);
      setIsConnecting(false);
      console.log('✅ Connected to server');
      // Fetch cameras and ranges when connected
      fetchCameras();
      fetchRanges();
    });

    newSocket.on('disconnect', (reason) => {
      setIsConnected(false);
      setIsConnecting(false);
      console.log(`❌ Disconnected from server: ${reason}`);
      if (reason === 'io server disconnect') {
        // Server disconnected, don't auto-reconnect - let user manually reconnect
        console.log('Server disconnected. Click Connect to reconnect.');
      }
    });

    newSocket.on('connect_error', (error) => {
      console.error('⚠️ Connection error:', error.message);
      setIsConnected(false);
      setIsConnecting(false);
    });

    newSocket.on('reconnect', (attemptNumber) => {
      console.log(`🔄 Reconnected after ${attemptNumber} attempts`);
      setIsConnected(true);
      setIsConnecting(false);
      fetchCameras();
      fetchRanges();
    });

    newSocket.on('reconnect_attempt', (attemptNumber) => {
      console.log(`🔄 Reconnection attempt ${attemptNumber}...`);
      setIsConnecting(true);
    });

    newSocket.on('reconnect_error', (error) => {
      console.error('⚠️ Reconnection error:', error.message);
      setIsConnecting(false);
    });

    newSocket.on('reconnect_failed', () => {
      console.error('❌ Reconnection failed after all attempts');
      setIsConnecting(false);
    });

    // Set up frame handlers
    newSocket.on('frame_camera1', (data) => {
      if (data.detections && data.detections.length > 0) {
        updateDetections(data.detections, 'camera1');
      }
    });

    newSocket.on('frame_camera2', (data) => {
      if (data.detections && data.detections.length > 0) {
        updateDetections(data.detections, 'camera2');
      }
    });
  };

  const disconnectFromServer = () => {
    if (socket) {
      console.log('🔌 Disconnecting from server...');
      socket.close();
      setSocket(null);
      setIsConnected(false);
      setIsConnecting(false);
    }
  };

  // Fetch cameras when connected
  useEffect(() => {
    if (isConnected) {
      fetchCameras();
    }
  }, [isConnected]);

  // Set up periodic range fetching when connected
  useEffect(() => {
    if (!isConnected) return;

    const interval = setInterval(() => {
      fetchRanges();
      fetchTimers();
    }, 1000); // Every 1 second for timer updates

    return () => {
      clearInterval(interval);
    };
  }, [isConnected]);

  const fetchCameras = async (showLoading = false) => {
    if (showLoading) {
      setRefreshingCameras(true);
    }
    try {
      const response = await axios.get(`${API_BASE_URL}/api/cameras`);
      console.log('📡 Fetched cameras:', response.data);
      setCameras(response.data);
      // Update nextCameraId based on existing cameras
      const cameraIds = Object.keys(response.data).map(id => {
        const match = id.match(/camera(\d+)/);
        return match ? parseInt(match[1]) : 0;
      });
      if (cameraIds.length > 0) {
        setNextCameraId(Math.max(...cameraIds) + 1);
      }
      if (showLoading) {
        console.log('✅ Cameras refreshed successfully');
      }
    } catch (error) {
      console.error('❌ Error fetching cameras:', error);
      if (showLoading) {
        alert('Failed to refresh cameras. Please check if the server is running.');
      }
    } finally {
      if (showLoading) {
        setRefreshingCameras(false);
      }
    }
  };

  const handleRefreshCameras = () => {
    if (!isConnected) {
      alert('Please connect to the backend first');
      return;
    }
    fetchCameras(true);
  };

  const fetchRanges = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/ranges`);
      setVehicleRanges(response.data);
    } catch (error) {
      console.error('Error fetching ranges:', error);
    }
  };

  const fetchTimers = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/timers`);
      setActiveTimers(response.data);
    } catch (error) {
      console.error('Error fetching timers:', error);
    }
  };

  const updateDetections = (newDetections, cameraId) => {
    setDetections(prev => {
      const updated = { ...prev };
      newDetections.forEach(det => {
        if (!updated[det.plate_number]) {
          updated[det.plate_number] = [];
        }
        // Preserve all fields from detection including status
        const detectionWithStatus = {
          ...det,
          camera_id: cameraId,
          timestamp: det.timestamp || new Date().toISOString()
        };
        // Debug log to see if status is present
        if (det.status) {
          console.log(`✅ Detection with status: ${det.plate_number} - ${det.status} at ${det.location?.name || cameraId}`);
          
          // Log Telegram notification status based on status type
          if (det.status === 'entry') {
            console.log(`📱 Telegram: Entry notification should be sent for ${det.plate_number}`);
          } else if (det.status === 'movement') {
            console.log(`📱 Telegram: Movement detected for ${det.plate_number} - timer started (location notification will be sent after 30s)`);
          } else if (det.status === 'exit') {
            console.log(`📱 Telegram: Exit notification should be sent for ${det.plate_number}`);
          } else if (det.status === 'last_seen') {
            console.log(`📱 Telegram: Last seen notification should be sent for ${det.plate_number} with location`);
          }
        }
        updated[det.plate_number].push(detectionWithStatus);
      });
      return updated;
    });
  };


  const handleStartCamera = (cameraId, cameraIndex) => {
    if (socket) {
      socket.emit('start_camera', { camera_id: cameraId, camera_index: cameraIndex });
      setTimeout(fetchCameras, 500);
    }
  };

  const handleStopCamera = (cameraId) => {
    if (socket) {
      socket.emit('stop_camera', { camera_id: cameraId });
      setTimeout(fetchCameras, 500);
    }
  };

  const handleUpdateLocation = async (cameraId, location) => {
    try {
      console.log(`📍 Updating ${cameraId} location:`, location);
      
      // Check if backend is available
      if (!isConnected) {
        alert('Not connected to server. Please connect first.');
        return;
      }
      
      const response = await axios.post(`${API_BASE_URL}/api/cameras/${cameraId}/location`, location, {
        timeout: 5000 // 5 second timeout
      });
      console.log(`✅ Location updated successfully:`, response.data);
      
      // Update cameras state immediately for instant feedback
      setCameras(prev => ({
        ...prev,
        [cameraId]: {
          ...prev[cameraId],
          location: response.data.location || location
        }
      }));
      
      // Also fetch from server to ensure sync
      await fetchCameras();
    } catch (error) {
      console.error('❌ Error updating location:', error);
      if (error.code === 'ERR_NETWORK' || error.message.includes('Network Error')) {
        alert('Cannot connect to server. Please check if the backend is running on port 5002.');
      } else {
        alert(`Failed to update location: ${error.response?.data?.error || error.message}`);
      }
    }
  };

  const handleAddCamera = async (cameraData) => {
    const trialCameraCount = Object.keys(cameras).filter(id => cameras[id]?.is_trial === true).length;
    if (trialMode && trialCameraCount >= 5) {
      alert('Maximum 5 trial cameras allowed');
      return;
    }

    const newCameraId = `camera${nextCameraId}`;
    
    // Add camera to state first
    setCameras(prev => ({
      ...prev,
      [newCameraId]: {
        active: false,
        location: cameraData.location,
        image_url: cameraData.image_url,
        is_trial: trialMode
      }
    }));

    // Update location on server
    try {
      if (trialMode && cameraData.image_file) {
        // Upload image for trial mode
        const formData = new FormData();
        formData.append('image', cameraData.image_file);
        formData.append('camera_id', newCameraId);
        formData.append('name', cameraData.name);
        formData.append('lat', cameraData.location.lat);
        formData.append('lng', cameraData.location.lng);

        const response = await axios.post(`${API_BASE_URL}/api/trial/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 30000
        });
        console.log(`✅ Trial camera ${newCameraId} added successfully:`, response.data);
      } else {
        // Normal camera mode
        const response = await axios.post(`${API_BASE_URL}/api/cameras/${newCameraId}/location`, {
          ...cameraData.location,
          name: cameraData.name
        }, {
          timeout: 5000
        });
        console.log(`✅ Camera ${newCameraId} added successfully:`, response.data);
      }
      setNextCameraId(prev => prev + 1);
      await fetchCameras();
    } catch (error) {
      console.error('❌ Error adding camera:', error);
      // Remove from state if server update failed
      setCameras(prev => {
        const updated = { ...prev };
        delete updated[newCameraId];
        return updated;
      });
      alert(`Failed to add camera: ${error.response?.data?.error || error.message}`);
    }
  };

  const handleDeleteCamera = async (cameraId) => {
    const camera = cameras[cameraId];
    const isTrialCamera = camera?.is_trial === true;
    
    // Prevent deleting cameras that don't match the current mode
    if (trialMode && !isTrialCamera) {
      alert('Cannot delete regular camera in trial mode. Switch to camera mode to delete this camera.');
      return;
    }
    
    if (!trialMode && isTrialCamera) {
      alert('Cannot delete trial camera in camera mode. Switch to trial mode to delete this camera.');
      return;
    }
    
    if (!window.confirm(`Are you sure you want to delete ${camera?.location?.name || cameraId}?`)) {
      return;
    }

    // Stop camera if active (only for regular cameras)
    if (camera?.active && socket && !isTrialCamera) {
      handleStopCamera(cameraId);
    }

    // Delete from backend
    try {
      await axios.delete(`${API_BASE_URL}/api/cameras/${cameraId}`, {
        timeout: 5000
      });
      console.log(`✅ Camera ${cameraId} deleted from backend`);
    } catch (error) {
      console.error('❌ Error deleting camera:', error);
    }

    // Remove from state
    setCameras(prev => {
      const updated = { ...prev };
      delete updated[cameraId];
      return updated;
    });
  };

  const handleTrialDetection = async (cameraId) => {
    if (!isConnected) {
      alert('Please connect to the backend first');
      return;
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/api/trial/detect`, {
        camera_id: cameraId
      }, {
        timeout: 30000 // 30 seconds for processing
      });
      
      if (response.data.detections && response.data.detections.length > 0) {
        updateDetections(response.data.detections, cameraId);
        console.log(`✅ Trial detection completed for ${cameraId}:`, response.data.detections);
      } else {
        console.log(`ℹ️ No detections found in ${cameraId}`);
      }
    } catch (error) {
      console.error('❌ Error triggering trial detection:', error);
      alert(`Failed to process image: ${error.response?.data?.error || error.message}`);
    }
  };

  const handleResetDetections = async () => {
    if (!isConnected) {
      alert('Please connect to the backend first');
      return;
    }

    try {
      await axios.post(`${API_BASE_URL}/api/detections/reset`, {}, {
        timeout: 5000
      });
      console.log('✅ Detections reset successfully');
      // Clear local state
      setDetections({});
      setVehicleRanges({});
      setActiveTimers({});
      setSelectedPlate(null);
      // Refresh data
      fetchRanges();
      fetchTimers();
    } catch (error) {
      console.error('❌ Error resetting detections:', error);
      alert(`Failed to reset detections: ${error.response?.data?.error || error.message}`);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>SentriCam</h1>
        <div className="header-controls">
          <div className="connection-status">
            <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
            <span>{isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Disconnected'}</span>
          </div>
          <div className="connection-buttons">
            {!isConnected && !isConnecting && (
              <button 
                className="btn btn-connect"
                onClick={connectToServer}
                title="Connect to server"
              >
                <FiWifi /> Connect
              </button>
            )}
            {isConnecting && (
              <button 
                className="btn btn-connect" 
                disabled
                title="Connecting..."
              >
                <FiLoader className="spinner-small" /> Connecting...
              </button>
            )}
            {isConnected && (
              <button 
                className="btn btn-disconnect"
                onClick={disconnectFromServer}
                title="Disconnect from server"
              >
                <FiWifiOff /> Disconnect
              </button>
            )}
          </div>
        </div>
      </header>

      <VehicleForm onVehicleAdded={(vehicle) => {
        console.log('Vehicle added:', vehicle);
      }} />

      <AddCameraModal
        isOpen={showAddCameraModal}
        onClose={() => setShowAddCameraModal(false)}
        onAddCamera={handleAddCamera}
        isConnected={isConnected}
        trialMode={trialMode}
        existingCameraCount={Object.keys(cameras).length}
      />

      <div className="main-content">
        <div className="cameras-section">
          <div className="cameras-section-header">
            <div>
              <h2><FiCamera /> Cameras</h2>
              <p className="cameras-section-subtitle">
                {(() => {
                  const filteredCameras = trialMode 
                    ? Object.keys(cameras).filter(id => cameras[id]?.is_trial === true)
                    : Object.keys(cameras).filter(id => cameras[id]?.is_trial !== true);
                  const count = filteredCameras.length;
                  return count === 0 
                    ? 'No cameras configured' 
                    : `${count} ${count === 1 ? 'camera' : 'cameras'} configured`;
                })()}
              </p>
            </div>
            <div className="cameras-header-actions">
              <div className="trial-mode-toggle">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={trialMode}
                    onChange={(e) => setTrialMode(e.target.checked)}
                    disabled={!isConnected}
                  />
                  <span className="toggle-slider"></span>
                  <span className="toggle-text">{trialMode ? <><FiPackage /> Trial Mode</> : <><FiCamera /> Camera Mode</>}</span>
                </label>
              </div>
              {!trialMode && (
                <button
                  onClick={handleRefreshCameras}
                  disabled={!isConnected || refreshingCameras}
                  className="btn-refresh-cameras"
                  title={!isConnected ? 'Connect to backend first' : 'Refresh camera list'}
                >
                  {refreshingCameras ? (
                    <>
                      <FiLoader className="spinner-small" />
                      <span>Refreshing...</span>
                    </>
                  ) : (
                    <>
                      <FiRefreshCw />
                      <span>Refresh</span>
                    </>
                  )}
                </button>
              )}
              <button
                onClick={() => setShowAddCameraModal(true)}
                disabled={!isConnected || (trialMode && Object.keys(cameras).filter(id => cameras[id]?.is_trial === true).length >= 5)}
                className="btn-add-camera"
                title={
                  !isConnected 
                    ? 'Connect to backend first' 
                    : trialMode && Object.keys(cameras).filter(id => cameras[id]?.is_trial === true).length >= 5
                    ? 'Maximum 5 trial cameras allowed'
                    : trialMode
                    ? 'Add trial image (max 5)'
                    : 'Add new camera'
                }
              >
                <FiPlus />
                <span>{trialMode ? 'Add Trial Image' : 'Add Camera'}</span>
              </button>
            </div>
          </div>
          
          {(() => {
            const filteredCameras = trialMode 
              ? Object.keys(cameras).filter(id => cameras[id]?.is_trial === true)
              : Object.keys(cameras).filter(id => cameras[id]?.is_trial !== true);
            
            if (filteredCameras.length === 0) {
              return (
                <div className="no-cameras-container">
                  <div className="no-cameras-icon">{trialMode ? <FiPackage size={64} /> : <FiCamera size={64} />}</div>
                  <h3>No {trialMode ? 'Trial Cameras' : 'Cameras'} Added</h3>
                  <p>
                    {!isConnected 
                      ? 'Connect to the backend first, then add your first camera to get started.'
                      : trialMode
                      ? 'Add your first trial image to test the system. Click "Add Trial Image" to begin.'
                      : 'Add your first camera to start tracking vehicles. Click "Add Camera" to begin.'}
                  </p>
                  {isConnected && (
                    <button
                      onClick={() => setShowAddCameraModal(true)}
                      className="btn-add-first-camera"
                    >
                      <FiPlus /> Add Your First {trialMode ? 'Trial Image' : 'Camera'}
                    </button>
                  )}
                </div>
              );
            }
            
            return trialMode ? (
            <div className="cameras-grid">
              {Object.keys(cameras)
                .filter(cameraId => cameras[cameraId]?.is_trial === true)
                .sort((a, b) => {
                  // Sort by camera number if IDs are like camera1, camera2, etc.
                  const numA = parseInt(a.replace('camera', '')) || 0;
                  const numB = parseInt(b.replace('camera', '')) || 0;
                  return numA - numB;
                })
                .map((cameraId, index) => (
                  <TrialCameraView
                    key={cameraId}
                    cameraId={cameraId}
                    cameraName={cameras[cameraId]?.location?.name || cameraId}
                    cameraLocation={cameras[cameraId]?.location}
                    imageUrl={cameras[cameraId]?.image_url}
                    isConnected={isConnected}
                    onDetect={(cameraId) => handleTrialDetection(cameraId)}
                    onDeleteCamera={handleDeleteCamera}
                    onUpdateLocation={handleUpdateLocation}
                    cameraNumber={index + 1}
                  />
                ))}
            </div>
          ) : (
            <div className="cameras-grid">
              {Object.keys(cameras)
                .filter(cameraId => cameras[cameraId]?.is_trial !== true)
                .sort((a, b) => {
                  // Sort by camera number if IDs are like camera1, camera2, etc.
                  const numA = parseInt(a.replace('camera', '')) || 0;
                  const numB = parseInt(b.replace('camera', '')) || 0;
                  return numA - numB;
                })
                .map((cameraId, index) => (
                  <CameraView
                    key={cameraId}
                    cameraId={cameraId}
                    socket={socket}
                    cameraName={cameras[cameraId]?.location?.name || cameraId}
                    isActive={cameras[cameraId]?.active || false}
                    isConnected={isConnected}
                    onStartCamera={handleStartCamera}
                    onStopCamera={handleStopCamera}
                    onUpdateLocation={handleUpdateLocation}
                    onDeleteCamera={handleDeleteCamera}
                    cameraLocation={cameras[cameraId]?.location}
                    cameraNumber={index + 1}
                  />
                ))}
            </div>
            );
          })()}
        </div>

        <div className="tracking-section">
          <DetectionList
            detections={detections}
            vehicleRanges={vehicleRanges}
            activeTimers={activeTimers}
            selectedPlate={selectedPlate}
            onPlateSelect={setSelectedPlate}
            onReset={handleResetDetections}
          />
          <CampusMap
            cameras={cameras}
            vehicleRanges={vehicleRanges}
            selectedPlate={selectedPlate}
            onPlateSelect={setSelectedPlate}
          />
        </div>
      </div>
    </div>
  );
}

export default App;

