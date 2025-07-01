import os
import sys
import asyncio
import av
import streamlit as st
from streamlit_webrtc import VideoHTMLAttributes, webrtc_streamer
from aiortc.contrib.media import MediaRecorder

# ---- Setup Environment Paths ---- #
BASE_DIR = os.path.abspath(os.path.join(__file__, '../../'))
sys.path.append(BASE_DIR)

from utils import get_mediapipe_pose
from process_frame import ProcessFrame
from thresholds import get_thresholds_beginner, get_thresholds_pro

# ---- Fix for Streamlit Cloud Asyncio RuntimeError ---- #
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

# ---- Streamlit Page Config ---- #
st.set_page_config(page_title="AI Fitness Trainer", layout="centered")
st.title('🏋️ AI Fitness Trainer: Squats Analysis')

# ---- Reference Video Display ---- #
st.video("squats3d.mp4")

# ---- Mode Selection ---- #
mode = st.radio('Select Your Fitness Level', ['Beginner', 'Pro'], horizontal=True)
thresholds = get_thresholds_beginner() if mode == 'Beginner' else get_thresholds_pro()

# ---- Pose Estimation and Frame Processor ---- #
live_process_frame = ProcessFrame(thresholds=thresholds, flip_frame=True)
pose = get_mediapipe_pose()

# ---- Video Output File ---- #
output_video_file = 'output_live.flv'
if 'download' not in st.session_state:
    st.session_state['download'] = False

# ---- Webcam Frame Callback ---- #
def video_frame_callback(frame: av.VideoFrame):
    if ctx and ctx.state.playing:
        frame = frame.to_ndarray(format="rgb24")
        frame, _ = live_process_frame.process(frame, pose)
        return av.VideoFrame.from_ndarray(frame, format="rgb24")
    return frame

# ---- Media Recorder Factory ---- #
def out_recorder_factory():
    return MediaRecorder(output_video_file)

# ---- WebRTC Streaming ---- #
ctx = webrtc_streamer(
    key="Squats-pose-analysis",
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
    media_stream_constraints={"video": {"width": {"min": 480, "ideal": 480}}, "audio": False},
    video_html_attrs=VideoHTMLAttributes(autoPlay=True, controls=False, muted=False),
    out_recorder_factory=out_recorder_factory,
)

# ---- Webcam Status Info ---- #
if ctx and ctx.state.playing:
    st.success("✅ Live webcam stream started. Perform your squats now!")
else:
    st.warning("📸 Waiting for webcam access or permission...")

# ---- Show Download Button If Video Recorded ---- #
if os.path.exists(output_video_file):
    st.markdown("---")
    with open(output_video_file, 'rb') as op_vid:
        download = st.download_button(
            label='⬇️ Download Recorded Squat Session',
            data=op_vid,
            file_name='output_squats_session.mp4',
            mime='video/mp4'
        )
        if download:
            st.session_state['download'] = True

# ---- Cleanup After Download ---- #
if os.path.exists(output_video_file) and st.session_state['download']:
    os.remove(output_video_file)
    st.session_state['download'] = False
