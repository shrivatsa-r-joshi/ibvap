/**
 * Owner: Frontend
 *
 * Scrolling feed of incoming `alert` messages (docs/schema.md). Newest first.
 */
import React from 'react';
import { ShieldAlertIcon } from './Icons';

export default function AlertsFeed({ alerts = [] }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="alerts-feed empty">
        <ShieldAlertIcon size={24} className="alert-empty-icon" />
        <span className="empty-text">No active perimeter alerts</span>
      </div>
    );
  }

  return (
    <div className="alerts-feed">
      <div className="alerts-feed-header">
        <h4>Intrusion Alerts ({alerts.length})</h4>
      </div>
      <div className="alerts-list">
        {alerts.map((alert, i) => (
          <div key={alert.alert_id || i} className={`alert-row ${alert.severity || 'high'}`}>
            <div className="alert-row-left">
              <span className="alert-indicator" />
              <div className="alert-row-info">
                <span className="alert-row-msg">{alert.message}</span>
                <span className="alert-row-meta">
                  Target: {alert.object_id} · {alert.location}
                </span>
              </div>
            </div>
            <span className="alert-row-time">
              {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString() : ''}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
