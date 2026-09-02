"""
Owner: Backend

Loads settings from .env (see .env.example at repo root for every key this reads).
Every other module should import config values from here rather than reading
os.environ directly, so there's one place to look when something's misconfigured.
"""
import os
from dotenv import load_dotenv

load_dotenv()

VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "sample")
SAMPLE_VIDEO_PATH = os.getenv("SAMPLE_VIDEO_PATH", "backend/sample_videos/demo_clip.mp4")
RTSP_URL = os.getenv("RTSP_URL", "")

# "x1,y1,x2,y2" as fractions of frame size -> tuple of 4 floats
FENCE_LINE_COORDS = tuple(
    float(v) for v in os.getenv("FENCE_LINE_COORDS", "0.1,0.6,0.9,0.6").split(",")
)

DATABASE_PATH = os.getenv("DATABASE_PATH", "backend/app/db/events.db")
