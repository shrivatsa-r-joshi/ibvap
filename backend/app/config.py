"""
Owner: Backend

Loads settings from .env (see .env.example at repo root for every key this reads).
Every other module should import config values from here rather than reading
os.environ directly, so there's one place to look when something's misconfigured.
"""
import os
from dotenv import load_dotenv

from pathlib import Path

load_dotenv()

def resolve_video_path(path_str: str) -> str:
    """
    Robustly resolves video paths whether executed from the project root
    or inside the backend directory.
    """
    if not path_str or str(path_str).isdigit() or str(path_str).startswith(("rtsp://", "http://", "https://")):
        return path_str

    p = Path(path_str)
    if p.exists():
        return str(p.resolve())

    # Candidate 1: relative to backend root
    backend_root = Path(__file__).resolve().parent.parent
    if (backend_root / path_str).exists():
        return str((backend_root / path_str).resolve())

    # Candidate 2: strip leading 'backend/'
    if str(path_str).startswith("backend/"):
        stripped = str(path_str)[len("backend/"):]
        if Path(stripped).exists():
            return str(Path(stripped).resolve())
        if (backend_root / stripped).exists():
            return str((backend_root / stripped).resolve())

    # Candidate 3: relative to repo root
    repo_root = backend_root.parent
    if (repo_root / path_str).exists():
        return str((repo_root / path_str).resolve())

    # Candidate 4: check sample_videos/demo_clip.mp4 directly
    if (backend_root / "sample_videos" / "demo_clip.mp4").exists():
        return str((backend_root / "sample_videos" / "demo_clip.mp4").resolve())
    if (repo_root / "backend" / "sample_videos" / "demo_clip.mp4").exists():
        return str((repo_root / "backend" / "sample_videos" / "demo_clip.mp4").resolve())

    return path_str


VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "sample")
SAMPLE_VIDEO_PATH = resolve_video_path(os.getenv("SAMPLE_VIDEO_PATH", "backend/sample_videos/getty_border_migrants.mp4"))
RTSP_URL = os.getenv("RTSP_URL", "")

# "x1,y1,x2,y2" as fractions of frame size -> tuple of 4 floats
FENCE_LINE_COORDS = tuple(
    float(v) for v in os.getenv("FENCE_LINE_COORDS", "0.1,0.6,0.9,0.6").split(",")
)

DATABASE_PATH = os.getenv("DATABASE_PATH", "backend/app/db/events.db")

# --- Multi-Camera CCTV Channels ---
CAMERA_FEEDS = {
    "cam1": {
        "id": "cam1",
        "name": "CAM-01",
        "sector": "Perimeter Sector A (Fence Wire Tampering)",
        "source": "backend/sample_videos/getty_border_migrants.mp4",
        "fence_coords": (0.05, 0.52, 0.95, 0.52),
    },
    "cam2": {
        "id": "cam2",
        "name": "CAM-02",
        "sector": "Wall Patrol Sector B (High-Security Barrier)",
        "source": "backend/sample_videos/getty_border_patrol.mp4",
        "fence_coords": (0.05, 0.65, 0.95, 0.65),
    },
    "cam3": {
        "id": "cam3",
        "name": "CAM-03",
        "sector": "Aerial Recon Sector C (Drone Border Gate)",
        "source": "backend/sample_videos/getty_drone_bridge.mp4",
        "fence_coords": (0.05, 0.55, 0.95, 0.55),
    },
    "cam4": {
        "id": "cam4",
        "name": "CAM-04",
        "sector": "Live Optical CCTV (Local Camera)",
        "source": "webcam",
        "fence_coords": (0.1, 0.6, 0.9, 0.6),
    },
}

# --- Detection & Tracking Config (AI Core) ---
YOLO_MODEL_PATH = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.28"))
TRACKER_CONFIG = os.getenv("TRACKER_CONFIG", "bytetrack.yaml")
