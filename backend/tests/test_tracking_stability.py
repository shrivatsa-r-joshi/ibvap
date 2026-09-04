"""
Tracking Stability and Consistency Test (Person 1)
IBVAP SIH 26187
"""

import sys
import unittest
from pathlib import Path
import cv2

# Add backend directory to sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.detection.detector import YOLOVideoDetector, get_detections


class TestTrackingStability(unittest.TestCase):
    """Verifies that objects maintain stable IDs across video frames."""

    @classmethod
    def setUpClass(cls):
        cls.video_path = str(_BACKEND_DIR / "sample_videos" / "demo_clip.mp4")
        cls.detector = YOLOVideoDetector(model_path="yolov8n.pt", conf_threshold=0.45)

    def test_track_id_persistence_on_video_stream(self):
        cap = cv2.VideoCapture(self.video_path)
        self.assertTrue(cap.isOpened(), f"Failed to open test video at {self.video_path}")

        frame_id = 0
        track_appearances = {}  # {track_id: count_of_frames_appeared}
        classes_seen = set()

        while True:
            if frame_id >= 100:
                break
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_id += 1
            detection_msg = self.detector.get_detections(frame, frame_id)

            self.assertEqual(detection_msg["type"], "detection")
            self.assertEqual(detection_msg["frame_id"], frame_id)
            self.assertIsInstance(detection_msg["timestamp"], str)

            for obj in detection_msg["objects"]:
                trk_id = obj["id"]
                cls_name = obj["class"]
                classes_seen.add(cls_name)

                # Schema validation
                self.assertTrue(trk_id.startswith("trk_"))
                self.assertIn(cls_name, ("person", "vehicle"))
                self.assertFalse(obj["crossed_fence"])
                self.assertEqual(len(obj["bbox"]), 4)

                track_appearances[trk_id] = track_appearances.get(trk_id, 0) + 1

        cap.release()

        # Check that we processed all frames (clip has at least 90 frames)
        self.assertGreaterEqual(frame_id, 90, f"Expected at least 90 frames, got {frame_id}")

        # Check that target classes were detected
        self.assertTrue(
            "person" in classes_seen or "vehicle" in classes_seen,
            f"Expected person or vehicle detected in clip, got: {classes_seen}",
        )

        # Check tracking persistence:
        # A good persistent tracker will track key objects across a significant majority of frames
        # without generating hundreds of new IDs.
        total_unique_tracks = len(track_appearances)
        max_persistence = max(track_appearances.values())

        print(
            f"\nTracking Stability Report:\n"
            f"  Frames Processed: {frame_id}\n"
            f"  Unique Tracks: {total_unique_tracks}\n"
            f"  Average FPS: {self.detector.current_fps:.1f}\n"
            f"  Track Lifespans: {track_appearances}"
        )

        # Major objects (like the bus and key pedestrians) should persist across >= 80% of frames
        self.assertGreaterEqual(
            max_persistence,
            70,
            f"Primary tracked object should persist across at least 70/90 frames, got {max_persistence}",
        )

        # Total unique tracks should be small and bounded (not creating a new track every frame)
        self.assertLess(
            total_unique_tracks,
            15,
            f"Tracker created too many IDs ({total_unique_tracks}) for a stable 90-frame scene",
        )


if __name__ == "__main__":
    unittest.main()
