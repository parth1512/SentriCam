import React, { useState, useEffect } from 'react';
import './ControlPanel.css';
import { decimalToDMS, dmsToDecimal, parseDMSString, formatDMSString } from '../utils/coordinateConverter';

const ControlPanel = ({ cameras, onStartCamera, onStopCamera, onUpdateLocation }) => {
  const [expandedCamera, setExpandedCamera] = useState(null);
  const [locationInputs, setLocationInputs] = useState({});
  const [coordinateFormat, setCoordinateFormat] = useState({}); // 'decimal' or 'dms' per camera

  // Initialize location inputs with current camera values
  useEffect(() => {
    const newInputs = {};
    const newFormats = {};
    ['camera1', 'camera2'].forEach(cameraId => {
      const camera = cameras[cameraId];
      if (camera?.location) {
        // Default to decimal format, but can be changed
        newFormats[cameraId] = coordinateFormat[cameraId] || 'decimal';
        
        if (newFormats[cameraId] === 'dms') {
          // Convert to DMS format
          const latDMS = decimalToDMS(camera.location.lat, true);
          const lngDMS = decimalToDMS(camera.location.lng, false);
          newInputs[cameraId] = {
            lat_deg: latDMS.degrees,
            lat_min: latDMS.minutes,
            lat_sec: latDMS.seconds,
            lat_dir: latDMS.direction,
            lng_deg: lngDMS.degrees,
            lng_min: lngDMS.minutes,
            lng_sec: lngDMS.seconds,
            lng_dir: lngDMS.direction,
            name: camera.location.name || `Camera ${cameraId.slice(-1)}`
          };
        } else {
          // Decimal format
          newInputs[cameraId] = {
            lat: camera.location.lat?.toString() || '',
            lng: camera.location.lng?.toString() || '',
            name: camera.location.name || `Camera ${cameraId.slice(-1)}`
          };
        }
      }
    });
    setLocationInputs(prev => ({ ...prev, ...newInputs }));
    setCoordinateFormat(prev => {
      const updated = { ...prev };
      Object.keys(newFormats).forEach(key => {
        if (!updated[key]) {
          updated[key] = newFormats[key];
        }
      });
      return updated;
    });
  }, [cameras]);

  const handleLocationChange = (cameraId, field, value) => {
    setLocationInputs(prev => ({
      ...prev,
      [cameraId]: {
        ...prev[cameraId],
        [field]: value
      }
    }));
  };

  const handleFormatChange = (cameraId, format) => {
    setCoordinateFormat(prev => ({ ...prev, [cameraId]: format }));
    
    const camera = cameras[cameraId];
    if (camera?.location) {
      if (format === 'dms') {
        // Convert decimal to DMS
        const latDMS = decimalToDMS(camera.location.lat, true);
        const lngDMS = decimalToDMS(camera.location.lng, false);
        setLocationInputs(prev => ({
          ...prev,
          [cameraId]: {
            ...prev[cameraId],
            lat_deg: latDMS.degrees,
            lat_min: latDMS.minutes,
            lat_sec: latDMS.seconds,
            lat_dir: latDMS.direction,
            lng_deg: lngDMS.degrees,
            lng_min: lngDMS.minutes,
            lng_sec: lngDMS.seconds,
            lng_dir: lngDMS.direction,
            lat: undefined,
            lng: undefined
          }
        }));
      } else {
        // Convert DMS to decimal
        setLocationInputs(prev => ({
          ...prev,
          [cameraId]: {
            ...prev[cameraId],
            lat: camera.location.lat?.toString() || '',
            lng: camera.location.lng?.toString() || '',
            lat_deg: undefined,
            lat_min: undefined,
            lat_sec: undefined,
            lat_dir: undefined,
            lng_deg: undefined,
            lng_min: undefined,
            lng_sec: undefined,
            lng_dir: undefined
          }
        }));
      }
    }
  };

  const handlePasteDMS = (cameraId, type, value) => {
    // Try to parse DMS string like "12°58'05.5"N"
    const parsed = parseDMSString(value);
    if (parsed) {
      if (type === 'lat') {
        setLocationInputs(prev => ({
          ...prev,
          [cameraId]: {
            ...prev[cameraId],
            lat_deg: parsed.degrees,
            lat_min: parsed.minutes,
            lat_sec: parsed.seconds,
            lat_dir: parsed.direction
          }
        }));
      } else {
        setLocationInputs(prev => ({
          ...prev,
          [cameraId]: {
            ...prev[cameraId],
            lng_deg: parsed.degrees,
            lng_min: parsed.minutes,
            lng_sec: parsed.seconds,
            lng_dir: parsed.direction
          }
        }));
      }
    }
  };

  const handleUpdateLocation = (cameraId) => {
    const inputs = locationInputs[cameraId];
    if (!inputs) return;

    const format = coordinateFormat[cameraId] || 'decimal';
    let lat, lng;

    if (format === 'dms') {
      // Convert DMS to decimal
      lat = dmsToDecimal(
        inputs.lat_deg,
        inputs.lat_min,
        inputs.lat_sec,
        inputs.lat_dir
      );
      lng = dmsToDecimal(
        inputs.lng_deg,
        inputs.lng_min,
        inputs.lng_sec,
        inputs.lng_dir
      );

      // Validate DMS inputs
      if (!inputs.lat_deg || !inputs.lat_min || !inputs.lat_sec || !inputs.lat_dir) {
        alert('Please enter complete latitude in DMS format');
        return;
      }
      if (!inputs.lng_deg || !inputs.lng_min || !inputs.lng_sec || !inputs.lng_dir) {
        alert('Please enter complete longitude in DMS format');
        return;
      }
    } else {
      // Decimal format
      lat = parseFloat(inputs.lat);
      lng = parseFloat(inputs.lng);

      // Validate coordinates
      if (isNaN(lat) || isNaN(lng)) {
        alert('Please enter valid latitude and longitude values');
        return;
      }
    }

    // Validate final decimal values
    if (isNaN(lat) || isNaN(lng)) {
      alert('Invalid coordinate values. Please check your input.');
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

    const location = {
      lat: lat,
      lng: lng,
      name: inputs.name || cameras[cameraId]?.location?.name || `Camera ${cameraId.slice(-1)}`
    };

    onUpdateLocation(cameraId, location);
    setExpandedCamera(null);
  };

  return (
    <div className="control-panel">
      <h2>🎮 Control Panel</h2>
      
      <div className="cameras-controls">
        {['camera1', 'camera2'].map(cameraId => {
          const camera = cameras[cameraId];
          const isExpanded = expandedCamera === cameraId;
          
          return (
            <div key={cameraId} className="camera-control">
              <div className="control-header">
                <div>
                  <h3>{camera?.location?.name || cameraId}</h3>
                  <p className="camera-location-text">
                    📍 {camera?.location?.lat?.toFixed(6) || 'Not set'}, {camera?.location?.lng?.toFixed(6) || 'Not set'}
                  </p>
                </div>
                <div className="control-buttons">
                  <button
                    className="btn btn-location"
                    onClick={() => setExpandedCamera(isExpanded ? null : cameraId)}
                  >
                    {isExpanded ? '✕ Close' : '📍 Edit Location'}
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="location-form">
                  <div className="form-group">
                    <label>Camera Name:</label>
                    <input
                      type="text"
                      placeholder={camera?.location?.name || `Camera ${cameraId.slice(-1)}`}
                      value={locationInputs[cameraId]?.name || ''}
                      onChange={(e) => handleLocationChange(cameraId, 'name', e.target.value)}
                      className="form-input"
                    />
                  </div>
                  
                  <div className="format-selector">
                    <label>Coordinate Format:</label>
                    <div className="format-buttons">
                      <button
                        type="button"
                        className={`format-btn ${(coordinateFormat[cameraId] || 'decimal') === 'decimal' ? 'active' : ''}`}
                        onClick={() => handleFormatChange(cameraId, 'decimal')}
                      >
                        Decimal Degrees
                      </button>
                      <button
                        type="button"
                        className={`format-btn ${coordinateFormat[cameraId] === 'dms' ? 'active' : ''}`}
                        onClick={() => handleFormatChange(cameraId, 'dms')}
                      >
                        DMS (Degrees° Minutes' Seconds")
                      </button>
                    </div>
                  </div>

                  {(coordinateFormat[cameraId] || 'decimal') === 'decimal' ? (
                    <div className="coordinates-group">
                      <div className="form-row">
                        <label htmlFor={`${cameraId}-lat`}>
                          <strong>Latitude:</strong>
                          <span className="input-hint">(-90 to 90)</span>
                        </label>
                        <input
                          id={`${cameraId}-lat`}
                          type="number"
                          step="any"
                          min="-90"
                          max="90"
                          placeholder={camera?.location?.lat?.toString() || "19.9975"}
                          value={locationInputs[cameraId]?.lat || ''}
                          onChange={(e) => handleLocationChange(cameraId, 'lat', e.target.value)}
                          className="form-input coordinate-input"
                        />
                      </div>
                      <div className="form-row">
                        <label htmlFor={`${cameraId}-lng`}>
                          <strong>Longitude:</strong>
                          <span className="input-hint">(-180 to 180)</span>
                        </label>
                        <input
                          id={`${cameraId}-lng`}
                          type="number"
                          step="any"
                          min="-180"
                          max="180"
                          placeholder={camera?.location?.lng?.toString() || "73.7898"}
                          value={locationInputs[cameraId]?.lng || ''}
                          onChange={(e) => handleLocationChange(cameraId, 'lng', e.target.value)}
                          className="form-input coordinate-input"
                        />
                      </div>
                    </div>
                  ) : (
                    <div className="dms-coordinates">
                      <div className="dms-group">
                        <label><strong>Latitude (DMS):</strong></label>
                        <div className="dms-inputs">
                          <div className="dms-field">
                            <label>Degrees</label>
                            <input
                              type="number"
                              min="0"
                              max="90"
                              placeholder="12"
                              value={locationInputs[cameraId]?.lat_deg || ''}
                              onChange={(e) => handleLocationChange(cameraId, 'lat_deg', e.target.value)}
                              className="form-input dms-input"
                            />
                          </div>
                          <span className="dms-separator">°</span>
                          <div className="dms-field">
                            <label>Minutes</label>
                            <input
                              type="number"
                              min="0"
                              max="59"
                              placeholder="58"
                              value={locationInputs[cameraId]?.lat_min || ''}
                              onChange={(e) => handleLocationChange(cameraId, 'lat_min', e.target.value)}
                              className="form-input dms-input"
                            />
                          </div>
                          <span className="dms-separator">'</span>
                          <div className="dms-field">
                            <label>Seconds</label>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              max="59.9"
                              placeholder="05.5"
                              value={locationInputs[cameraId]?.lat_sec || ''}
                              onChange={(e) => handleLocationChange(cameraId, 'lat_sec', e.target.value)}
                              className="form-input dms-input"
                            />
                          </div>
                          <span className="dms-separator">"</span>
                          <div className="dms-field">
                            <label>Direction</label>
                            <select
                              value={locationInputs[cameraId]?.lat_dir || 'N'}
                              onChange={(e) => handleLocationChange(cameraId, 'lat_dir', e.target.value)}
                              className="form-input dms-direction"
                            >
                              <option value="N">N</option>
                              <option value="S">S</option>
                            </select>
                          </div>
                        </div>
                        <div className="dms-paste">
                          <label>Or paste DMS string:</label>
                          <input
                            type="text"
                            placeholder="e.g., 12°58'05.5N"
                            onPaste={(e) => {
                              const pasted = e.clipboardData.getData('text');
                              handlePasteDMS(cameraId, 'lat', pasted);
                              e.preventDefault();
                            }}
                            className="form-input dms-paste-input"
                          />
                        </div>
                      </div>

                      <div className="dms-group">
                        <label><strong>Longitude (DMS):</strong></label>
                        <div className="dms-inputs">
                          <div className="dms-field">
                            <label>Degrees</label>
                            <input
                              type="number"
                              min="0"
                              max="180"
                              placeholder="79"
                              value={locationInputs[cameraId]?.lng_deg || ''}
                              onChange={(e) => handleLocationChange(cameraId, 'lng_deg', e.target.value)}
                              className="form-input dms-input"
                            />
                          </div>
                          <span className="dms-separator">°</span>
                          <div className="dms-field">
                            <label>Minutes</label>
                            <input
                              type="number"
                              min="0"
                              max="59"
                              placeholder="09"
                              value={locationInputs[cameraId]?.lng_min || ''}
                              onChange={(e) => handleLocationChange(cameraId, 'lng_min', e.target.value)}
                              className="form-input dms-input"
                            />
                          </div>
                          <span className="dms-separator">'</span>
                          <div className="dms-field">
                            <label>Seconds</label>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              max="59.9"
                              placeholder="21.3"
                              value={locationInputs[cameraId]?.lng_sec || ''}
                              onChange={(e) => handleLocationChange(cameraId, 'lng_sec', e.target.value)}
                              className="form-input dms-input"
                            />
                          </div>
                          <span className="dms-separator">"</span>
                          <div className="dms-field">
                            <label>Direction</label>
                            <select
                              value={locationInputs[cameraId]?.lng_dir || 'E'}
                              onChange={(e) => handleLocationChange(cameraId, 'lng_dir', e.target.value)}
                              className="form-input dms-direction"
                            >
                              <option value="E">E</option>
                              <option value="W">W</option>
                            </select>
                          </div>
                        </div>
                        <div className="dms-paste">
                          <label>Or paste DMS string:</label>
                          <input
                            type="text"
                            placeholder="e.g., 79°09'21.3E"
                            onPaste={(e) => {
                              const pasted = e.clipboardData.getData('text');
                              handlePasteDMS(cameraId, 'lng', pasted);
                              e.preventDefault();
                            }}
                            className="form-input dms-paste-input"
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="form-actions">
                    <button
                      className="btn btn-save"
                      onClick={() => handleUpdateLocation(cameraId)}
                      disabled={
                        (coordinateFormat[cameraId] || 'decimal') === 'decimal'
                          ? (!locationInputs[cameraId]?.lat || !locationInputs[cameraId]?.lng)
                          : (!locationInputs[cameraId]?.lat_deg || !locationInputs[cameraId]?.lng_deg)
                      }
                    >
                      💾 Save & Update Map
                    </button>
                    <button
                      className="btn btn-cancel"
                      onClick={() => {
                        setExpandedCamera(null);
                        // Reset inputs to current camera values
                        const camera = cameras[cameraId];
                        if (camera?.location) {
                          setLocationInputs(prev => ({
                            ...prev,
                            [cameraId]: {
                              lat: camera.location.lat?.toString() || '',
                              lng: camera.location.lng?.toString() || '',
                              name: camera.location.name || `Camera ${cameraId.slice(-1)}`
                            }
                          }));
                        }
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                  
                  {locationInputs[cameraId]?.lat && locationInputs[cameraId]?.lng && (
                    <div className="coordinate-preview">
                      <p>📍 Preview: {parseFloat(locationInputs[cameraId].lat)?.toFixed(6)}, {parseFloat(locationInputs[cameraId].lng)?.toFixed(6)}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ControlPanel;



