import React, { useState } from 'react';
import { FiPackage, FiCamera, FiAlertCircle, FiPlus, FiX } from 'react-icons/fi';
import './AddCameraModal.css';

const AddCameraModal = ({ isOpen, onClose, onAddCamera, isConnected, trialMode = false, existingCameraCount = 0 }) => {
  const [cameraName, setCameraName] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [coordinatesInput, setCoordinatesInput] = useState(''); // Combined lat,lng input
  const [error, setError] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!cameraName.trim()) {
      setError('Please enter a camera name');
      return;
    }

    // Validate and parse coordinates
    const lat = parseFloat(latitude);
    const lng = parseFloat(longitude);

    if (isNaN(lat) || isNaN(lng)) {
      setError('Please enter valid latitude and longitude values');
      return;
    }

    if (lat < -90 || lat > 90) {
      setError('Latitude must be between -90 and 90');
      return;
    }

    if (lng < -180 || lng > 180) {
      setError('Longitude must be between -180 and 180');
      return;
    }

    // Trial mode validation
    if (trialMode) {
      if (!imageFile) {
        setError('Please select an image file for trial mode');
        return;
      }
      if (existingCameraCount >= 5) {
        setError('Maximum 5 trial cameras allowed');
        return;
      }
    }

    const cameraData = {
      name: cameraName.trim(),
      location: {
        lat: lat,
        lng: lng,
        name: cameraName.trim()
      }
    };

    if (trialMode && imageFile) {
      cameraData.image_file = imageFile;
      cameraData.image_url = imagePreview;
    }

    onAddCamera(cameraData);

    // Reset form
    setCameraName('');
    setLatitude('');
    setLongitude('');
    setCoordinatesInput('');
    setError('');
    setImageFile(null);
    setImagePreview(null);
    onClose();
  };

  const handleClose = () => {
    setCameraName('');
    setLatitude('');
    setLongitude('');
    setCoordinatesInput('');
    setError('');
    setImageFile(null);
    setImagePreview(null);
    onClose();
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (file.size > 10 * 1024 * 1024) {
        setError('Image size must be less than 10MB');
        return;
      }
      if (!file.type.startsWith('image/')) {
        setError('Please select a valid image file');
        return;
      }
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
      setError('');
    }
  };

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
          setLatitude(lat.toString());
          setLongitude(lng.toString());
        }
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{trialMode ? <><FiPackage /> Add Trial Image</> : <><FiCamera /> Add New Camera</>}</h2>
          <button className="modal-close" onClick={handleClose}><FiX /></button>
        </div>

        <form onSubmit={handleSubmit} className="add-camera-form">
          {trialMode && (
            <div className="form-group">
              <label htmlFor="image-upload">
                Car Image <span className="required">*</span>
              </label>
              <input
                type="file"
                id="image-upload"
                accept="image/*"
                onChange={handleImageChange}
                className="form-input-file"
              />
              {imagePreview && (
                <div className="image-preview">
                  <img src={imagePreview} alt="Preview" />
                </div>
              )}
              <p className="input-hint">Upload an image of a car with visible license plate (max 10MB)</p>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="camera-name">
              {trialMode ? 'Location Name' : 'Camera Name'} <span className="required">*</span>
            </label>
            <input
              type="text"
              id="camera-name"
              value={cameraName}
              onChange={(e) => {
                setCameraName(e.target.value);
                setError('');
              }}
              placeholder={trialMode ? "e.g., Main Entrance, Parking Lot A" : "e.g., Main Entrance, Parking Lot A"}
              className="form-input"
              autoFocus
            />
          </div>

          <div className="form-group">
            <label htmlFor="coordinates">
              Coordinates (paste: lat, lng) <span className="required">*</span>
            </label>
            <input
              type="text"
              id="coordinates"
              value={coordinatesInput}
              onChange={(e) => {
                handleCoordinatesInput(e.target.value);
                setError('');
              }}
              placeholder="e.g., 12.968145, 79.155902 or paste coordinates"
              className="form-input"
              style={{ fontFamily: 'monospace' }}
            />
            <p className="input-hint">Paste coordinates in format: latitude, longitude (e.g., 12.968145, 79.155902)</p>
          </div>

          <div className="form-group">
            <label htmlFor="latitude">
              Latitude <span className="required">*</span>
            </label>
            <input
              type="number"
              id="latitude"
              value={latitude}
              onChange={(e) => {
                setLatitude(e.target.value);
                if (e.target.value && longitude) {
                  setCoordinatesInput(`${e.target.value}, ${longitude}`);
                }
                setError('');
              }}
              placeholder="e.g., 12.968194"
              step="any"
              min="-90"
              max="90"
              className="form-input"
            />
            <p className="input-hint">Enter latitude between -90 and 90 (decimal format)</p>
          </div>

          <div className="form-group">
            <label htmlFor="longitude">
              Longitude <span className="required">*</span>
            </label>
            <input
              type="number"
              id="longitude"
              value={longitude}
              onChange={(e) => {
                setLongitude(e.target.value);
                if (latitude && e.target.value) {
                  setCoordinatesInput(`${latitude}, ${e.target.value}`);
                }
                setError('');
              }}
              placeholder="e.g., 79.155917"
              step="any"
              min="-180"
              max="180"
              className="form-input"
            />
            <p className="input-hint">Enter longitude between -180 and 180 (decimal format)</p>
          </div>

          {error && (
            <div className="error-message" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FiAlertCircle /> {error}
            </div>
          )}

          {!isConnected && (
            <div className="warning-message" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FiAlertCircle /> Please connect to the backend first
            </div>
          )}

          <div className="modal-actions">
            <button
              type="button"
              onClick={handleClose}
              className="btn-cancel-modal"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!cameraName.trim() || !latitude || !longitude || !isConnected || (trialMode && !imageFile)}
              className="btn-add-modal"
            >
              <FiPlus /> {trialMode ? 'Add Trial Image' : 'Add Camera'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AddCameraModal;

