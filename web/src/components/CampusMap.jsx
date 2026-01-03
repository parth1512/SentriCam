import React, { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import './MapView.css';

// Component to update map center when cameras change
function MapUpdater({ center, zoom }) {
  const map = useMap();
  
  useEffect(() => {
    if (center && center[0] && center[1]) {
      map.setView(center, zoom);
      console.log('🗺️ Map view updated to:', center);
    }
  }, [center, zoom, map]);
  
  return null;
}

const CampusMap = ({ cameras, vehicleRanges, selectedPlate, onPlateSelect }) => {
  const [isClient, setIsClient] = useState(false);

  // Ensure we're on the client side (not SSR)
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Fix for default marker icon issue in React Leaflet
  // This is a known issue where Leaflet can't find the default icon images
  useEffect(() => {
    if (!isClient) return;
    
    try {
      if (L && L.Icon && L.Icon.Default) {
        delete L.Icon.Default.prototype._getIconUrl;
        L.Icon.Default.mergeOptions({
          iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
          iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
          shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
        });
      }
    } catch (error) {
      console.error('Error setting up Leaflet icons:', error);
    }
  }, [isClient]);

  // Default center coordinates (midpoint between the two cameras)
  const defaultCenter = [(12.968194 + 12.968806) / 2, (79.155917 + 79.155306) / 2];
  
  // Calculate map center based on all camera locations
  const mapCenter = React.useMemo(() => {
    try {
      // Get all cameras with valid locations
      const validCameras = Object.entries(cameras || {}).filter(([id, cam]) => 
        cam?.location?.lat && cam?.location?.lng
      );
      
      if (validCameras.length === 0) {
        console.log('📍 Map center (default - no cameras):', defaultCenter);
        return defaultCenter;
      }
      
      // Calculate center of all cameras
      const totalLat = validCameras.reduce((sum, [id, cam]) => sum + cam.location.lat, 0);
      const totalLng = validCameras.reduce((sum, [id, cam]) => sum + cam.location.lng, 0);
      const avgLat = totalLat / validCameras.length;
      const avgLng = totalLng / validCameras.length;
      
      console.log(`📍 Map center (${validCameras.length} cameras):`, [avgLat, avgLng]);
      return [avgLat, avgLng];
    } catch (error) {
      console.error('Error calculating map center:', error);
      return defaultCenter;
    }
  }, [cameras]);

  // Debug: Log camera locations
  useEffect(() => {
    const cameraLocations = {};
    Object.entries(cameras || {}).forEach(([id, cam]) => {
      if (cam?.location) {
        cameraLocations[id] = cam.location;
      }
    });
    console.log('🗺️ Camera locations updated:', cameraLocations);
  }, [cameras]);

  if (!isClient) {
    return (
      <div className="map-view">
        <div className="map-header">
          <h3>Vehicle Location Tracking</h3>
          <p className="map-subtitle">Loading map...</p>
        </div>
        <div className="leaflet-container" style={{ height: '500px', width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <p>Loading map...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="map-view">
      <div className="map-header">
        <h3>Vehicle Location Tracking</h3>
        <p className="map-subtitle">Real-time vehicle position estimates based on camera detections</p>
      </div>
      
      <div className="leaflet-container" style={{ height: '500px', width: '100%' }}>
        <MapContainer
          key={`map-${Object.keys(cameras || {}).length}-${JSON.stringify(Object.values(cameras || {}).map(c => c?.location))}`}
          center={mapCenter}
          zoom={16}
          style={{ width: '100%', height: '100%', borderRadius: '8px' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          <MapUpdater center={mapCenter} zoom={16} />

          {/* Camera markers - dynamically render all cameras */}
          {Object.entries(cameras || {}).map(([cameraId, camera]) => {
            if (!camera?.location?.lat || !camera?.location?.lng) {
              return null;
            }
            
            const isTrial = camera.is_trial || false;
            const iconColor = isTrial ? 'red' : 'green';
            
            return (
              <Marker 
                key={`${cameraId}-${camera.location.lat}-${camera.location.lng}`}
                position={[camera.location.lat, camera.location.lng]}
                icon={L.icon({
                  iconUrl: `https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-${iconColor}.png`,
                  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
                  iconSize: [25, 41],
                  iconAnchor: [12, 41],
                  popupAnchor: [1, -34],
                  shadowSize: [41, 41]
                })}
              >
                <Popup>
                  <div className="camera-popup">
                    <strong>{camera.location.name || cameraId}</strong>
                    {isTrial && <p><em>Trial Camera</em></p>}
                    <p>Lat: {camera.location.lat.toFixed(6)}</p>
                    <p>Lng: {camera.location.lng.toFixed(6)}</p>
                  </div>
                </Popup>
              </Marker>
            );
          })}

          {/* Vehicle range circles and markers */}
          {Object.entries(vehicleRanges || {}).map(([plateNumber, range]) => {
            const isSelected = selectedPlate === plateNumber;
            const center = [range.center.lat, range.center.lng];
            
            return (
              <React.Fragment key={plateNumber}>
                <Circle
                  center={center}
                  radius={range.radius_meters}
                  pathOptions={{
                    fillColor: isSelected ? '#ff0000' : '#667eea',
                    fillOpacity: isSelected ? 0.4 : 0.2,
                    color: isSelected ? '#ff0000' : '#667eea',
                    weight: isSelected ? 3 : 2,
                    opacity: isSelected ? 0.8 : 0.5,
                  }}
                  eventHandlers={{
                    click: () => onPlateSelect && onPlateSelect(plateNumber),
                  }}
                />
                <Marker
                  position={center}
                  eventHandlers={{
                    click: () => onPlateSelect && onPlateSelect(plateNumber),
                  }}
                >
                  <Popup>
                    <div className="info-window">
                      <h4>Vehicle: {plateNumber}</h4>
                      <p><strong>Estimated Range:</strong> {range.radius_meters?.toFixed(0) || 0}m</p>
                      {range.camera1 && range.camera2 && (
                        <>
                          <p><strong>Camera 1:</strong> {range.camera1.name || 'Unknown'}</p>
                          <p><strong>Camera 2:</strong> {range.camera2.name || 'Unknown'}</p>
                        </>
                      )}
                      {range.first_seen && (
                        <p><strong>First Seen:</strong> {new Date(range.first_seen).toLocaleString()}</p>
                      )}
                      {range.last_seen && (
                        <p><strong>Last Seen:</strong> {new Date(range.last_seen).toLocaleString()}</p>
                      )}
                    </div>
                  </Popup>
                </Marker>
              </React.Fragment>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
};

export default CampusMap;

