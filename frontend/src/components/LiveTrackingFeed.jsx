import React, { useState } from 'react';
import {
  PersonIcon,
  VehicleIcon,
  ShieldAlertIcon,
  ActivityIcon,
  RadarIcon,
  SparklesIcon,
} from './Icons';

export default function LiveTrackingFeed({
  detections,
  alerts = [],
  onSimulateAlert,
  onClearAlerts,
}) {
  const [activeTab, setActiveTab] = useState('tracking'); // 'tracking' | 'alerts'

  const objects = detections?.objects || [];
  const activeCount = objects.length;
  const alertCount = alerts.length;

  const personCount = objects.filter((o) => o.class === 'person').length;
  const vehicleCount = objects.filter((o) => o.class === 'vehicle').length;
  const otherCount = activeCount - personCount - vehicleCount;

  return (
    <div className="apple-sidebar-card">
      {/* Segmented Header Tab */}
      <div className="sidebar-tab-header">
        <button
          type="button"
          className={`sidebar-tab ${activeTab === 'tracking' ? 'active' : ''}`}
          onClick={() => setActiveTab('tracking')}
        >
          <ActivityIcon size={14} />
          <span>Active Targets</span>
          <span className={`count-pill ${activeCount > 0 ? 'highlight' : ''}`}>
            {activeCount}
          </span>
        </button>

        <button
          type="button"
          className={`sidebar-tab ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          <ShieldAlertIcon size={14} />
          <span>Alerts Log</span>
          {alertCount > 0 && (
            <span className="count-pill alert-pill">
              {alertCount}
            </span>
          )}
        </button>
      </div>

      <div className="sidebar-content-scroll">
        {activeTab === 'tracking' ? (
          /* Active Tracked Objects View */
          <div className="targets-container">
            {/* Target Breakdown Summary Bar */}
            <div className="target-breakdown-bar">
              <span className="breakdown-tag person">
                <span className="dot" /> {personCount} {personCount === 1 ? 'Person' : 'Persons'}
              </span>
              <span className="breakdown-tag vehicle">
                <span className="dot" /> {vehicleCount} {vehicleCount === 1 ? 'Vehicle' : 'Vehicles'}
              </span>
              {otherCount > 0 && (
                <span className="breakdown-tag other">
                  <span className="dot" /> {otherCount} {otherCount === 1 ? 'Object' : 'Objects'}
                </span>
              )}
            </div>

            {activeCount === 0 ? (
              <div className="empty-tracking-state">
                <div className="radar-sweep-anim">
                  <RadarIcon size={44} className="sweep-icon" />
                </div>
                <h4>Perimeter Clear</h4>
                <p>YOLOv8 persistent tracking scanner active. No targets currently detected in surveillance sector.</p>
              </div>
            ) : (
              objects.map((obj) => {
                const isPerson = obj.class === "person";
                const isVehicle = obj.class === "vehicle";
                const isBreach = obj.crossed_fence;
                const confPercent = Math.round(obj.confidence * 100);

                return (
                  <div
                    key={obj.id}
                    className={`target-item-card ${isPerson ? 'person' : (isVehicle ? 'vehicle' : 'object')} ${isBreach ? 'breach' : ''}`}
                  >
                    <div className="target-item-top">
                      <div className="target-id-badge">
                        <span className="id-tag">{obj.id}</span>
                        <span className={`class-chip ${isPerson ? 'person' : (isVehicle ? 'vehicle' : 'object')}`}>
                          {isPerson && <PersonIcon size={13} />}
                          {isVehicle && <VehicleIcon size={13} />}
                          {!isPerson && !isVehicle && <SparklesIcon size={12} />}
                          <span>{obj.class}</span>
                        </span>
                      </div>

                      <div className="target-conf-badge">
                        <span className="conf-value">{confPercent}%</span>
                      </div>
                    </div>

                    {/* Confidence Progress Bar */}
                    <div className="conf-bar-track">
                      <div
                        className={`conf-bar-fill ${isPerson ? 'person' : (isVehicle ? 'vehicle' : 'object')} ${isBreach ? 'breach' : ''}`}
                        style={{ width: `${confPercent}%` }}
                      />
                    </div>

                    <div className="target-item-bottom">
                      <span className="bbox-coords">
                        bbox: [{obj.bbox.map((v) => Number(v).toFixed(2)).join(', ')}]
                      </span>

                      <span className={`status-tag ${isBreach ? 'breach' : 'stable'}`}>
                        {isBreach ? '⚡ FENCE BREACH' : 'STABLE TRACK'}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        ) : (
          /* Alerts Feed View */
          <div className="alerts-container">
            {/* Alerts Action Bar with Simulate Threat Button */}
            <div className="alerts-action-bar">
              <span className="alerts-count-label">
                {alertCount} Recorded {alertCount === 1 ? 'Incident' : 'Incidents'}
              </span>
              <div className="alerts-action-btns">
                <button
                  type="button"
                  className="simulate-threat-btn"
                  onClick={onSimulateAlert}
                  title="Trigger a simulated perimeter intrusion breach"
                >
                  <span className="red-pulse" />
                  <span>Simulate Threat</span>
                </button>
                {alertCount > 0 && (
                  <button
                    type="button"
                    className="clear-alerts-btn"
                    onClick={onClearAlerts}
                    title="Clear alert feed in dashboard"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            {alertCount === 0 ? (
              <div className="empty-alerts-state">
                <ShieldAlertIcon size={40} className="shield-empty-icon" />
                <h4>No Intrusion Breaches</h4>
                <p>Virtual perimeter fence line is secure. Crossings will trigger automated real-time alerts.</p>
                <button
                  type="button"
                  className="simulate-threat-btn large"
                  onClick={onSimulateAlert}
                >
                  <span className="red-pulse" />
                  <span>Test Breach Alert</span>
                </button>
              </div>
            ) : (
              alerts.map((alert, idx) => {
                const sev = (alert.severity || 'high').toLowerCase();
                const alertTime = alert.timestamp
                  ? new Date(alert.timestamp).toLocaleTimeString()
                  : new Date().toLocaleTimeString();

                return (
                  <div key={alert.alert_id || idx} className={`alert-card severity-${sev}`}>
                    <div className="alert-card-header">
                      <div className="alert-title">
                        <span className="alert-beacon" />
                        <span className="alert-type">
                          {sev === 'high' ? 'CRITICAL BREACH' : 'PERIMETER INTRUSION'}
                        </span>
                      </div>
                      <span className="alert-time">{alertTime}</span>
                    </div>

                    <p className="alert-message">
                      {alert.message || `Object ${alert.object_id} crossed virtual perimeter fence.`}
                    </p>

                    <div className="alert-footer">
                      <span className="alert-object">
                        Target: <b>{alert.object_id || 'trk_sim'}</b> ({alert.class || 'target'})
                      </span>
                      <span className="alert-location">{alert.location || 'Perimeter Sector A'}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
