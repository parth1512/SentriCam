import React, { useState } from 'react';
import { FiMapPin, FiSearch, FiImage, FiEdit2, FiTrash2 } from 'react-icons/fi';
import './TrialCameraView.css';

const TrialCameraView = ({ cameraId, cameraName, cameraLocation, imageUrl, isConnected, onDetect, onDeleteCamera, onUpdateLocation, cameraNumber }) => {
  const [showEditForm, setShowEditForm] = useState(false);
  const [editLatitude, setEditLatitude] = useState(cameraLocation?.lat?.toString() || '');
  const [editLongitude, setEditLongitude] = useState(cameraLocation?.lng?.toString() || '');
  const [editCoordinates, setEditCoordinates] = useState(
    cameraLocation?.lat && cameraLocation?.lng 
      ? `${cameraLocation.lat}, ${cameraLocation.lng}` 
      : ''
  );
  const [editName, setEditName] = useState(cameraLocation?.name || cameraName || '');
  const [editError, setEditError] = useState('');

  const handleDetect = () => {
    if (!isConnected) {
      alert('Please connect to the backend first');
      return;
    }
    onDetect(cameraId);
  };

  const handleEditLocation = () => {
    setShowEditForm(true);
    setEditLatitude(cameraLocation?.lat?.toString() || '');
    setEditLongitude(cameraLocation?.lng?.toString() || '');
    setEditCoordinates(
      cameraLocation?.lat && cameraLocation?.lng 
        ? `${cameraLocation.lat}, ${cameraLocation.lng}` 
        : ''
    );
    setEditName(cameraLocation?.name || cameraName || '');
    setEditError('');
  };

  // Handle combined coordinates input (e.g., "12.968145, 79.155902")
  const handleCoordinatesInput = (value) => {
    setEditCoordinates(value);
    
    // Try to parse lat,lng format
    const trimmed = value.trim();
    if (trimmed.includes(',')) {
      const parts = trimmed.split(',').map(p => p.trim());
      if (parts.length === 2) {
        const lat = parseFloat(parts[0]);
        const lng = parseFloat(parts[1]);
        
        if (!isNaN(lat) && !isNaN(lng)) {
          setEditLatitude(lat.toString());
          setEditLongitude(lng.toString());
        }
      }
    }
  };

  const handleSaveLocation = () => {
    // Validate inputs
    const lat = parseFloat(editLatitude);
    const lng = parseFloat(editLongitude);

    if (isNaN(lat) || isNaN(lng)) {
      setEditError('Please enter valid latitude and longitude values');
      return;
    }

    if (lat < -90 || lat > 90) {
      setEditError('Latitude must be between -90 and 90');
      return;
    }

    if (lng < -180 || lng > 180) {
      setEditError('Longitude must be between -180 and 180');
      return;
    }

    if (!editName.trim()) {
      setEditError('Please enter a location name');
      return;
    }

    if (onUpdateLocation) {
      onUpdateLocation(cameraId, {
        lat: lat,
        lng: lng,
        name: editName.trim()
      });
      setShowEditForm(false);
      setEditError('');
    }
  };

  const handleCancelEdit = () => {
    setShowEditForm(false);
    setEditError('');
    setEditLatitude(cameraLocation?.lat?.toString() || '');
    setEditLongitude(cameraLocation?.lng?.toString() || '');
    setEditCoordinates(
      cameraLocation?.lat && cameraLocation?.lng 
        ? `${cameraLocation.lat}, ${cameraLocation.lng}` 
        : ''
    );
    setEditName(cameraLocation?.name || cameraName || '');
  };

  return (
    <div className="trial-camera-view">
      <div className="trial-camera-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
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
          <h3>{cameraName}</h3>
        </div>
        <div className="trial-camera-actions">
          <button
            className="btn-edit-trial-camera"
            onClick={handleEditLocation}
            title="Edit location"
          >
            <FiEdit2 />
          </button>
          <button
            className="btn-delete-trial-camera"
            onClick={() => onDeleteCamera(cameraId)}
            title="Delete trial camera"
          >
            <FiTrash2 />
          </button>
        </div>
      </div>

      <div className="trial-camera-image-container">
        {imageUrl ? (
          <img src={imageUrl} alt={cameraName} className="trial-camera-image" />
        ) : (
          <div className="trial-camera-placeholder">
            <span><FiImage /> No Image</span>
          </div>
        )}
      </div>

      {showEditForm ? (
        <div className="trial-camera-edit-form">
          <div className="edit-form-group">
            <label>Location Name</label>
            <input
              type="text"
              value={editName}
              onChange={(e) => {
                setEditName(e.target.value);
                setEditError('');
              }}
              placeholder="Location name"
              className="edit-form-input"
            />
          </div>
          <div className="edit-form-group">
            <label>Coordinates (paste: lat, lng)</label>
            <input
              type="text"
              value={editCoordinates}
              onChange={(e) => {
                handleCoordinatesInput(e.target.value);
                setEditError('');
              }}
              placeholder="e.g., 12.968145, 79.155902 or paste coordinates"
              className="edit-form-input"
              style={{ fontFamily: 'monospace' }}
            />
          </div>
          <div className="edit-form-group">
            <label>Latitude</label>
            <input
              type="number"
              value={editLatitude}
              onChange={(e) => {
                setEditLatitude(e.target.value);
                if (e.target.value && editLongitude) {
                  setEditCoordinates(`${e.target.value}, ${editLongitude}`);
                }
                setEditError('');
              }}
              placeholder="e.g., 12.968194"
              step="any"
              min="-90"
              max="90"
              className="edit-form-input"
            />
          </div>
          <div className="edit-form-group">
            <label>Longitude</label>
            <input
              type="number"
              value={editLongitude}
              onChange={(e) => {
                setEditLongitude(e.target.value);
                if (editLatitude && e.target.value) {
                  setEditCoordinates(`${editLatitude}, ${e.target.value}`);
                }
                setEditError('');
              }}
              placeholder="e.g., 79.155917"
              step="any"
              min="-180"
              max="180"
              className="edit-form-input"
            />
          </div>
          {editError && (
            <div className="edit-form-error">{editError}</div>
          )}
          <div className="edit-form-actions">
            <button
              className="btn-cancel-edit"
              onClick={handleCancelEdit}
            >
              Cancel
            </button>
            <button
              className="btn-save-edit"
              onClick={handleSaveLocation}
            >
              Save
            </button>
          </div>
        </div>
      ) : (
        <div className="trial-camera-info">
          {cameraLocation && (
            <div className="trial-camera-location">
              <FiMapPin className="location-label" />
              <span className="location-text">
                {cameraLocation.name || cameraId}
              </span>
            </div>
          )}
          {cameraLocation && cameraLocation.lat && cameraLocation.lng && (
            <div className="trial-camera-coordinates">
              <span className="coordinates-text">
                {cameraLocation.lat.toFixed(6)}, {cameraLocation.lng.toFixed(6)}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="trial-camera-controls">
        <button
          className="btn-detect-trial"
          onClick={handleDetect}
          disabled={!isConnected}
          title={!isConnected ? 'Connect to backend first' : 'Process image for vehicle detection'}
        >
          <FiSearch /> Detect Vehicle
        </button>
      </div>
    </div>
  );
};

export default TrialCameraView;

