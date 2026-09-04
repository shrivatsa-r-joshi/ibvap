import React, { useEffect } from 'react';
import { ShieldAlertIcon, CloseIcon } from './Icons';

export default function AlertNotificationPopup({ alert, onDismiss, onAcknowledge }) {
  useEffect(() => {
    if (!alert) return;
    const timer = setTimeout(() => {
      onDismiss?.();
    }, 7000); // Auto-dismiss after 7 seconds
    return () => clearTimeout(timer);
  }, [alert, onDismiss]);

  if (!alert) return null;

  const severity = (alert.severity || 'high').toLowerCase();
  const isCritical = severity === 'critical' || severity === 'high';
  const alertTime = alert.timestamp
    ? new Date(alert.timestamp).toLocaleTimeString()
    : new Date().toLocaleTimeString();

  return (
    <div className={`apple-alert-popup ${isCritical ? 'critical' : 'warning'}`}>
      <div className="alert-popup-glow" />
      <div className="alert-popup-content">
        <div className="alert-popup-header">
          <div className="alert-popup-badge">
            <span className="emergency-beacon" />
            <ShieldAlertIcon size={16} className="popup-shield-icon" />
            <span className="popup-severity-text">
              {isCritical ? 'CRITICAL PERIMETER BREACH' : 'SECURITY ANOMALY'}
            </span>
          </div>
          <div className="alert-popup-right">
            <span className="alert-popup-time">{alertTime}</span>
            <button
              type="button"
              className="popup-close-btn"
              onClick={onDismiss}
              title="Dismiss alert"
            >
              <CloseIcon size={14} />
            </button>
          </div>
        </div>

        <div className="alert-popup-body">
          <p className="popup-message">{alert.message || 'Perimeter fence wire breach detected.'}</p>
          <div className="popup-meta-row">
            <span className="popup-meta-pill target">
              Target: <b>{alert.object_id || 'trk_unknown'}</b> ({alert.class || 'person'})
            </span>
            <span className="popup-meta-pill location">
              📍 {alert.location || 'Perimeter Sector A'}
            </span>
          </div>
        </div>

        <div className="alert-popup-footer">
          <span className="popup-hint">Live Tri-Vision Sensor Alert</span>
          <button
            type="button"
            className="popup-ack-btn"
            onClick={() => {
              onAcknowledge?.(alert);
              onDismiss?.();
            }}
          >
            Acknowledge Breach
          </button>
        </div>
      </div>
    </div>
  );
}
