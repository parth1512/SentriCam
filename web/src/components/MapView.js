import React, { useMemo } from 'react';
import { GoogleMap, LoadScript, Circle, Marker, InfoWindow } from '@react-google-maps/api';
import './MapView.css';

const GOOGLE_MAPS_API_KEY = process.env.REACT_APP_GOOGLE_MAPS_API_KEY || 'YOUR_API_KEY_HERE';

const MapView = ({ cameras, vehicleRanges, selectedPlate, onPlateSelect }) => {
  const mapCenter = useMemo(() => {
    if (cameras.camera1?.location && cameras.camera2?.location) {
      const lat = (cameras.camera1.location.lat + cameras.camera2.location.lat) / 2;
      const lng = (cameras.camera1.location.lng + cameras.camera2.location.lng) / 2;
      return { lat, lng };
    }
    return cameras.camera1?.location || { lat: 40.7128, lng: -74.0060 };
  }, [cameras]);

  const mapContainerStyle = {
    width: '100%',
    height: '500px',
    borderRadius: '8px'
  };

  const defaultOptions = {
    zoomControl: true,
    streetViewControl: false,
    mapTypeControl: false,
    fullscreenControl: true,
  };

  return (
    <div className="map-view">
      <div className="map-header">
        <h3>📍 Vehicle Location Tracking</h3>
        <p className="map-subtitle">Real-time vehicle position estimates based on camera detections</p>
      </div>
      
      {GOOGLE_MAPS_API_KEY === 'YOUR_API_KEY_HERE' ? (
        <div className="map-placeholder">
          <p>⚠️ Google Maps API key required</p>
          <p className="placeholder-hint">
            Set REACT_APP_GOOGLE_MAPS_API_KEY in your .env file
          </p>
          <p className="placeholder-hint">
            Get your API key from{' '}
            <a 
              href="https://console.cloud.google.com/google/maps-apis" 
              target="_blank" 
              rel="noopener noreferrer"
            >
              Google Cloud Console
            </a>
          </p>
        </div>
      ) : (
        <LoadScript googleMapsApiKey={GOOGLE_MAPS_API_KEY}>
          <GoogleMap
            mapContainerStyle={mapContainerStyle}
            center={mapCenter}
            zoom={13}
            options={defaultOptions}
          >
            {/* Camera markers */}
            {cameras.camera1?.location && (
              <Marker
                position={cameras.camera1.location}
                label="C1"
                icon={{
                  url: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
                }}
              />
            )}
            {cameras.camera2?.location && (
              <Marker
                position={cameras.camera2.location}
                label="C2"
                icon={{
                  url: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png'
                }}
              />
            )}

            {/* Vehicle range circles */}
            {Object.entries(vehicleRanges).map(([plateNumber, range]) => {
              const isSelected = selectedPlate === plateNumber;
              return (
                <React.Fragment key={plateNumber}>
                  <Circle
                    center={range.center}
                    radius={range.radius_meters}
                    options={{
                      fillColor: isSelected ? '#ff0000' : '#667eea',
                      fillOpacity: isSelected ? 0.4 : 0.2,
                      strokeColor: isSelected ? '#ff0000' : '#667eea',
                      strokeOpacity: isSelected ? 0.8 : 0.5,
                      strokeWeight: isSelected ? 3 : 2,
                      clickable: true,
                    }}
                    onClick={() => onPlateSelect(plateNumber)}
                  />
                  <Marker
                    position={range.center}
                    label={plateNumber}
                    icon={{
                      url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                      scaledSize: window.google?.maps?.Size ? new window.google.maps.Size(32, 32) : { width: 32, height: 32 },
                    }}
                    onClick={() => onPlateSelect(plateNumber)}
                  />
                  {isSelected && (
                    <InfoWindow
                      position={range.center}
                      onCloseClick={() => onPlateSelect(null)}
                    >
                      <div className="info-window">
                        <h4>Vehicle: {plateNumber}</h4>
                        <p><strong>Estimated Range:</strong> {range.radius_meters.toFixed(0)}m</p>
                        {range.camera1 && range.camera2 && (
                          <>
                            <p><strong>Camera 1:</strong> {range.camera1.name || 'Unknown'}</p>
                            <p><strong>Camera 2:</strong> {range.camera2.name || 'Unknown'}</p>
                          </>
                        )}
                        <p><strong>First Seen:</strong> {new Date(range.first_seen).toLocaleString()}</p>
                        <p><strong>Last Seen:</strong> {new Date(range.last_seen).toLocaleString()}</p>
                      </div>
                    </InfoWindow>
                  )}
                </React.Fragment>
              );
            })}
          </GoogleMap>
        </LoadScript>
      )}
    </div>
  );
};

export default MapView;

