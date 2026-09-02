/**
 * Owner: Frontend
 *
 * Renders the live video feed with bounding boxes drawn from incoming
 * `detection` messages (docs/schema.md). bbox values are fractions of
 * frame width/height (0-1) — multiply by the rendered video's pixel
 * width/height to position boxes correctly, don't assume raw pixels.
 *
 * Props:
 *   detections: the latest `detection` message object (or null)
 */
export default function VideoPanel({ detections }) {
  // TODO: render <video>/<canvas> feed + draw boxes from detections.objects
  return (
    <div className="video-panel">
      {/* TODO: implement */}
    </div>
  );
}
