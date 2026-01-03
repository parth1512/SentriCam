import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { FiTruck, FiCheckCircle, FiXCircle, FiSmartphone } from 'react-icons/fi';
import './VehicleForm.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5002';

const VehicleForm = ({ onVehicleAdded }) => {
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState({ type: '', text: '' });

  // Fetch all vehicles on component mount and periodically
  useEffect(() => {
    fetchVehicles();
    // Refresh every 5 seconds to catch new registrations from Telegram
    const interval = setInterval(fetchVehicles, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchVehicles = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/vehicles`);
      if (response.data.status === 'success') {
        setVehicles(response.data.vehicles || []);
      }
      setLoading(false);
    } catch (error) {
      console.error('Error fetching vehicles:', error);
      setLoading(false);
    }
  };

  const handleDelete = async (vehicleId, vehicleNumber) => {
    if (!window.confirm(`Are you sure you want to delete vehicle ${vehicleNumber}?`)) {
      return;
    }

    try {
      const response = await axios.delete(`${API_BASE_URL}/api/vehicles/${vehicleId}`);
      if (response.data.status === 'success') {
        setMessage({ type: 'success', text: 'Vehicle deleted successfully!' });
        await fetchVehicles();
        setTimeout(() => {
          setMessage({ type: '', text: '' });
        }, 3000);
      }
    } catch (error) {
      const errorMessage = error.response?.data?.message || error.message || 'Failed to delete vehicle';
      setMessage({ type: 'error', text: errorMessage });
      setTimeout(() => {
        setMessage({ type: '', text: '' });
      }, 3000);
    }
  };

  if (loading) {
    return (
      <div className="vehicle-form-container">
        <div className="vehicle-form-header">
          <h2><FiTruck /> Registered Vehicles</h2>
        </div>
        <div className="loading-state">
          <p>Loading vehicles...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="vehicle-form-container">
      <div className="vehicle-form-header">
        <h2><FiTruck /> Registered Vehicles</h2>
        <div className="vehicle-count-badge">
          {vehicles.length} {vehicles.length === 1 ? 'vehicle' : 'vehicles'}
        </div>
      </div>

      {message.text && (
        <div className={`message ${message.type}`} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {message.type === 'success' ? <FiCheckCircle /> : <FiXCircle />} {message.text}
        </div>
      )}

      {vehicles.length === 0 ? (
        <div className="no-vehicles-container">
          <div className="no-vehicles-icon"><FiTruck size={64} /></div>
          <h3>No Registered Vehicles</h3>
          <p>Vehicles registered via Telegram will appear here automatically.</p>
          <div className="telegram-info">
            <p><FiSmartphone /> To register a vehicle:</p>
            <ol>
              <li>Open Telegram</li>
              <li>Search for <strong>@vehicle_tracker_sentricam_bot</strong></li>
              <li>Send <code>/register</code> and follow the prompts</li>
            </ol>
          </div>
        </div>
      ) : (
        <div className="vehicles-list">
          <div className="vehicles-grid">
            {vehicles.map(vehicle => (
              <div key={vehicle.id} className="vehicle-card">
                <div className="vehicle-card-header">
                  <div className="vehicle-number-badge">{vehicle.vehicle_number}</div>
                  <button
                    className="btn-delete-vehicle"
                    onClick={() => handleDelete(vehicle.id, vehicle.vehicle_number)}
                    title="Delete vehicle"
                  >
                    🗑️
                  </button>
                </div>
                <div className="vehicle-card-body">
                  <div className="vehicle-detail-row">
                    <span className="vehicle-label">👤 Owner:</span>
                    <span className="vehicle-value">{vehicle.name}</span>
                  </div>
                  <div className="vehicle-detail-row">
                    <span className="vehicle-label">📞 Phone:</span>
                    <span className="vehicle-value">{vehicle.phone_number}</span>
                  </div>
                  {vehicle.telegram_chat_id && (
                    <div className="vehicle-detail-row">
                      <span className="vehicle-label">📱 Telegram:</span>
                      <span className="vehicle-value telegram-linked">Linked</span>
                    </div>
                  )}
                  <div className="vehicle-detail-row">
                    <span className="vehicle-label">📅 Registered:</span>
                    <span className="vehicle-value">
                      {new Date(vehicle.created_at).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default VehicleForm;
