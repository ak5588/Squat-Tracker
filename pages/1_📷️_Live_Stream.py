import os
import sys
import asyncio
import av
import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoHTMLAttributes
from aiortc.contrib.media import MediaRecorder

# Setup project imports
BASE_DIR = os.path.abspath(os.path.join(__file__, "../../"))
sys.path.append(BASE_DIR)

from utils import get_mediapipe_pose
from process_frame import ProcessFrame
from thresholds import get_thresholds_beginner, get_thresholds_pro

# Fix asyncio loop for Streamlit Cloud
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# Page settings
st.set_page_config(page_title="AI Fitness Trainer", layout="centered")
st.title("🏋️ AI Fitness Trainer: Squats Analysis")

# Always visible reference video
st.markdown("### 🧭 Reference Squat Form")
st.video("squats3d.mp4")

# Mode selection
mode = st.radio("Select Mode", ["Beginner", "Pro"], horizontal=True)
thresholds = get_thresholds_beginner() if mode == "Beginner" else get_thresholds_pro()

# Pose estimation setup
pose = get_mediapipe_pose()
live_process_frame = ProcessFrame(thresholds=thresholds, flip_frame=True)

# Setup recording file and session state
output_video_file = "output_live.flv"
st.session_state.setdefault("download_ready", False)

def video_frame_callback(frame: av.VideoFrame):
    frame = frame.to_ndarray(format="rgb24")
    frame, _ = live_process_frame.process(frame, pose)
    return av.VideoFrame.from_ndarray(frame, format="rgb24")

def out_recorder_factory():
    return MediaRecorder(output_video_file)

ctx = webrtc_streamer(
    key="Squat-Tracker",
    video_frame_callback=video_frame_callback,
    rtc_configuration={
        "iceServers": [
            {"urls": ["stun:stun.l.google.com:19302"]},
            {
                "urls": ["turn:openrelay.metered.ca:80", "turn:openrelay.metered.ca:443"],
                "username": "openrelayproject",
                "credential": "openrelayproject"
            }
        ]
    },
    media_stream_constraints={"video": {"width": {"min": 480, "ideal": 640}}, "audio": False},
    video_html_attrs=VideoHTMLAttributes(autoPlay=True, controls=False, muted=False),
    out_recorder_factory=out_recorder_factory,
)

# WebRTC connection status
if ctx.state == ctx.State.CONNECTING:
    st.info("⌛ Connecting to webcam...")
elif ctx.state == ctx.State.PLAYING:
    st.success("✅ Webcam stream started.")
elif ctx.state == ctx.State.FAILED:
    st.error("❌ Connection failed. Try refreshing or check webcam access.")

# Download recorded video
if os.path.exists(output_video_file):
    st.markdown("---\n### 🎥 Recorded Session")
    with open(output_video_file, "rb") as f:
        download = st.download_button(
            label="⬇️ Download Video",
            data=f,
            file_name="squat_session.mp4",
            mime="video/mp4",
        )
        if download:
            st.session_state.download_ready = True

# Clean-up after download
if st.session_state.download_ready and os.path.exists(output_video_file):
    os.remove(output_video_file)
    st.session_state.download_ready = False
