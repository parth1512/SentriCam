import React from 'react';
import { FiTruck, FiRefreshCw, FiMapPin } from 'react-icons/fi';
import './DetectionList.css';

const DetectionList = ({ detections, vehicleRanges, activeTimers, selectedPlate, onPlateSelect, onReset }) => {
  const formatTimestamp = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const formatDistance = (meters) => {
    if (meters < 1000) {
      return `${meters.toFixed(0)}m`;
    }
    return `${(meters / 1000).toFixed(2)}km`;
  };

  const sortedPlates = Object.keys(vehicleRanges).sort((a, b) => {
    const timeA = new Date(vehicleRanges[a].last_seen);
    const timeB = new Date(vehicleRanges[b].last_seen);
    return timeB - timeA;
  });

  return (
    <div className="detection-list">
      <div className="list-header">
        <h3><FiTruck /> Detected Vehicles</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span className="count-badge">{sortedPlates.length} vehicles</span>
          {sortedPlates.length > 0 && onReset && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm('Are you sure you want to reset all detections? This will clear all vehicle tracking data.')) {
                  onReset();
                }
              }}
              className="btn-reset-detections"
              title="Reset all detections"
            >
              <FiRefreshCw /> Reset
            </button>
          )}
        </div>
      </div>
      
      <div className="list-content">
        {sortedPlates.length === 0 ? (
          <div className="empty-state">
            <p>No vehicles detected yet</p>
            <p className="empty-hint">Start cameras to begin tracking</p>
          </div>
        ) : (
          sortedPlates.map(plateNumber => {
            const range = vehicleRanges[plateNumber];
            const plateDetections = detections[plateNumber] || [];
            const isSelected = selectedPlate === plateNumber;
            
            // Get the latest detection with status - search through all detections
            let latestDetection = null;
            let latestDetectionWithStatus = null;
            
            if (plateDetections.length > 0) {
              // Get the most recent detection
              latestDetection = plateDetections[plateDetections.length - 1];
              
              // Find the most recent detection that has a status
              for (let i = plateDetections.length - 1; i >= 0; i--) {
                if (plateDetections[i].status) {
                  latestDetectionWithStatus = plateDetections[i];
                  break;
                }
              }
            }
            
            // Use the detection with status if available, otherwise use the latest
            const detectionToUse = latestDetectionWithStatus || latestDetection;
            
            // Get status message
            let statusMessage = null;
            if (detectionToUse && detectionToUse.status) {
              const locationName = detectionToUse.location?.name || 
                                   detectionToUse.camera_id || 
                                   range?.camera1?.name || 
                                   range?.camera2?.name ||
                                   'Unknown Location';
              if (detectionToUse.status === 'entry') {
                statusMessage = `${plateNumber} entry successful at ${locationName}`;
              } else if (detectionToUse.status === 'exit') {
                statusMessage = `${plateNumber} exit successful at ${locationName}`;
              }
            }
            
            return (
              <div
                key={plateNumber}
                className={`detection-item ${isSelected ? 'selected' : ''}`}
                onClick={() => onPlateSelect(isSelected ? null : plateNumber)}
              >
                <div className="item-header">
                  <h4 className="plate-number">{plateNumber}</h4>
                  <span className="range-badge">
                    Range: {formatDistance(range.radius_meters)}
                  </span>
                </div>
                
                {activeTimers[plateNumber] && (
                  <div className="timer-display">
                    <span className="timer-label">⏱️ Timer:</span>
                    <span className="timer-value">{activeTimers[plateNumber].remaining_seconds.toFixed(1)}s</span>
                    <span className="timer-location">at {activeTimers[plateNumber].location?.name || activeTimers[plateNumber].camera_id}</span>
                  </div>
                )}
                
                {statusMessage && (
                  <div className="status-message">
                    <span className={`status-text ${detectionToUse?.status === 'entry' ? 'entry-status' : 'exit-status'}`}>
                      {statusMessage}
                    </span>
                  </div>
                )}
                
                <div className="item-details">
                  <div className="detail-row">
                    <span className="detail-label">First Seen:</span>
                    <span className="detail-value">{formatTimestamp(range.first_seen)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Last Seen:</span>
                    <span className="detail-value">{formatTimestamp(range.last_seen)}</span>
                  </div>
                  <div className="detail-row">
                    <span className="detail-label">Detections:</span>
                    <span className="detail-value">{plateDetections.length} sightings</span>
                  </div>
                  {range.camera1 && range.camera2 && (
                    <div className="detail-row">
                      <span className="detail-label">Route:</span>
                      <span className="detail-value">
                        {range.camera1.name || 'Camera 1'} → {range.camera2.name || 'Camera 2'}
                      </span>
                    </div>
                  )}
                </div>
                
                <div className="item-location">
                  <FiMapPin className="location-icon" />
                  <span className="location-text">
                    {range.center.lat.toFixed(6)}, {range.center.lng.toFixed(6)}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default DetectionList;


