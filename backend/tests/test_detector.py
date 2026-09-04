"""
Tests for AI Detection and Tracking Layer (Person 1)
IBVAP SIH 26187
"""

import os
import sys
import unittest
from datetime import datetime
from pathlib import Path

import numpy as np

# Add backend directory to sys.path
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.detection import detector, tracking


class TestTrackingUtils(unittest.TestCase):
    """Test tracking helper functions and schema formatting."""

    def test_normalize_bbox(self):
        # 640x480 frame
        w, h = 640, 480
        # Box from (64, 48) to (320, 240) -> [0.1, 0.1, 0.5, 0.5]
        norm = tracking.normalize_bbox([64, 48, 320, 240], w, h)
        self.assertEqual(norm, [0.1, 0.1, 0.5, 0.5])

        # Clamping test: coordinates outside bounds
        clamped = tracking.normalize_bbox([-50, -20, 800, 600], w, h)
        self.assertEqual(clamped, [0.0, 0.0, 1.0, 1.0])

        # Zero/negative dimensions
        zero_dim = tracking.normalize_bbox([10, 10, 50, 50], 0, 0)
        self.assertEqual(zero_dim, [0.0, 0.0, 0.0, 0.0])

    def test_unnormalize_bbox(self):
        w, h = 640, 480
        bbox = [0.1, 0.1, 0.5, 0.5]
        px = tracking.unnormalize_bbox(bbox, w, h)
        self.assertEqual(px, (64, 48, 320, 240))

    def test_format_track_id(self):
        self.assertEqual(tracking.format_track_id(17), "trk_17")
        self.assertEqual(tracking.format_track_id("trk_17"), "trk_17")
        self.assertEqual(tracking.format_track_id("abc"), "trk_abc")

    def test_map_class(self):
        # People
        self.assertEqual(tracking.map_class(class_name="person"), "person")
        self.assertEqual(tracking.map_class(class_id=0), "person")

        # Vehicles
        for v_name in ["car", "motorcycle", "bus", "truck", "bicycle"]:
            self.assertEqual(tracking.map_class(class_name=v_name), "vehicle")

        for v_id in [1, 2, 3, 5, 7]:
            self.assertEqual(tracking.map_class(class_id=v_id), "vehicle")

        # Ignored classes
        self.assertIsNone(tracking.map_class(class_name="dog"))
        self.assertIsNone(tracking.map_class(class_name="traffic light"))
        self.assertIsNone(tracking.map_class(class_id=16))  # dog

    def test_iso_timestamp_format(self):
        ts = tracking.get_iso_timestamp()
        self.assertTrue(ts.endswith("Z"), f"Timestamp '{ts}' must end with 'Z'")
        self.assertIn("T", ts)
        # Parse ISO 8601 (replace Z with +00:00 for fromisoformat)
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        self.assertIsNotNone(parsed)

    def test_fps_counter(self):
        fps_counter = tracking.FPSCounter(window_size=5)
        self.assertEqual(fps_counter.fps, 0.0)
        for _ in range(5):
            fps_counter.tick()
        self.assertGreaterEqual(fps_counter.fps, 0.0)
        fps_counter.reset()
        self.assertEqual(fps_counter.fps, 0.0)

    def test_schema_structure(self):
        obj = tracking.create_tracked_object(
            track_id=17,
            class_name="person",
            bbox=[0.32, 0.41, 0.39, 0.68],
            confidence=0.9123,
        )
        self.assertEqual(
            obj,
            {
                "id": "trk_17",
                "class": "person",
                "bbox": [0.32, 0.41, 0.39, 0.68],
                "confidence": 0.91,
                "crossed_fence": False,
            },
        )
        self.assertFalse(obj["crossed_fence"])

        msg = tracking.create_detection_message(
            frame_id=1042,
            objects=[obj],
            timestamp="2026-09-05T10:14:32.501Z",
        )
        self.assertEqual(msg["type"], "detection")
        self.assertEqual(msg["frame_id"], 1042)
        self.assertEqual(msg["timestamp"], "2026-09-05T10:14:32.501Z")
        self.assertEqual(len(msg["objects"]), 1)


class TestYOLOVideoDetector(unittest.TestCase):
    """Test YOLOVideoDetector model inference, tracking, and edge cases."""

    @classmethod
    def setUpClass(cls):
        # Instantiate a detector instance using yolov8n.pt (fast nano model)
        cls.detector = detector.YOLOVideoDetector(model_path="yolov8n.pt", conf_threshold=0.3)

    def test_invalid_and_empty_frames(self):
        # 1. None frame
        msg_none = self.detector.get_detections(None, frame_id=1)
        self.assertEqual(msg_none["type"], "detection")
        self.assertEqual(msg_none["frame_id"], 1)
        self.assertEqual(msg_none["objects"], [])
        self.assertTrue(isinstance(msg_none["timestamp"], str))

        # 2. Empty numpy array
        empty_frame = np.empty((0, 0, 3), dtype=np.uint8)
        msg_empty = self.detector.get_detections(empty_frame, frame_id=2)
        self.assertEqual(msg_empty["type"], "detection")
        self.assertEqual(msg_empty["frame_id"], 2)
        self.assertEqual(msg_empty["objects"], [])

    def test_blank_frame_inference(self):
        # Solid black 640x480 frame
        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        msg = self.detector.get_detections(black_frame, frame_id=10)

        self.assertEqual(msg["type"], "detection")
        self.assertEqual(msg["frame_id"], 10)
        self.assertIsInstance(msg["objects"], list)
        self.assertTrue(msg["timestamp"].endswith("Z"))
        self.assertGreaterEqual(self.detector.current_fps, 0.0)

    def test_module_get_detections_interface(self):
        # Test Person 2's direct entrypoint: detector.get_detections(frame, frame_id)
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        msg = detector.get_detections(test_frame, frame_id=42)

        self.assertEqual(msg["type"], "detection")
        self.assertEqual(msg["frame_id"], 42)
        self.assertIsInstance(msg["objects"], list)

    def test_schema_contract_compliance(self):
        # Verify schema rules strictly:
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        msg = self.detector.get_detections(test_frame, frame_id=100)

        # Keys in root message
        self.assertSetEqual(set(msg.keys()), {"type", "frame_id", "timestamp", "objects"})
        self.assertEqual(msg["type"], "detection")
        self.assertIsInstance(msg["frame_id"], int)
        self.assertIsInstance(msg["timestamp"], str)

        for obj in msg["objects"]:
            self.assertSetEqual(
                set(obj.keys()),
                {"id", "class", "bbox", "confidence", "crossed_fence"},
            )
            self.assertTrue(obj["id"].startswith("trk_"))
            self.assertIn(obj["class"], {"person", "vehicle"})
            self.assertEqual(len(obj["bbox"]), 4)
            for coord in obj["bbox"]:
                self.assertGreaterEqual(coord, 0.0)
                self.assertLessEqual(coord, 1.0)
            self.assertGreaterEqual(obj["confidence"], 0.0)
            self.assertLessEqual(obj["confidence"], 1.0)
            self.assertFalse(obj["crossed_fence"])

    def test_reset_tracker(self):
        self.detector.reset_tracker()
        self.assertEqual(self.detector.current_fps, 0.0)


if __name__ == "__main__":
    unittest.main()
