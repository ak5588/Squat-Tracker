import os
import sys
import asyncio
import av
import streamlit as st
from streamlit_webrtc import VideoHTMLAttributes, webrtc_streamer
from aiortc.contrib.media import MediaRecorder

# Base path setup
BASE_DIR = os.path.abspath(os.path.join(__file__, '../../'))
sys.path.append(BASE_DIR)

from utils import get_mediapipe_pose
from process_frame import ProcessFrame
from thresholds import get_thresholds_beginner, get_thresholds_pro

# Fix asyncio loop if broken (common in Streamlit Cloud)
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

st.set_page_config(page_title="AI Fitness Trainer", layout="centered")
st.title('🏋️ AI Fitness Trainer: Squats Analysis')

# Reference video shown ALWAYS
st.video("squats3d.mp4")

# Mode selection
mode = st.radio('Select Mode', ['Beginner', 'Pro'], horizontal=True)
thresholds = get_thresholds_beginner() if mode == 'Beginner' else get_thresholds_pro()

# Pose & Frame setup
live_process_frame = ProcessFrame(thresholds=thresholds, flip_frame=True)
pose = get_mediapipe_pose()

output_video_file = 'output_live.flv'
if 'download' not in st.session_state:
    st.session_state['download'] = False

# Video frame processing
def video_frame_callback(frame: av.VideoFrame):
    if ctx and ctx.state.playing:
        frame = frame.to_ndarray(format="rgb24")
        frame, _ = live_process_frame.process(frame, pose)
        return av.VideoFrame.from_ndarray(frame, format="rgb24")
    return frame

# Recorder
def out_recorder_factory():
    return MediaRecorder(output_video_file)

# Webcam Stream
ctx = webrtc_streamer(
    key="Squats-pose-analysis",
    video_frame_callback=video_frame_callback,
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    media_stream_constraints={"video": {"width": {"min": 480, "ideal": 480}}, "audio": False},
    video_html_attrs=VideoHTMLAttributes(autoPlay=True, controls=False, muted=False),
    out_recorder_factory=out_recorder_factory,
)

# Webcam state info
if ctx and ctx.state.playing:
    st.success("✅ Live webcam stream started.")
else:
    st.warning("📸 Waiting for webcam access...")

# Show download button if video was recorded
if os.path.exists(output_video_file):
    st.markdown("---")
    with open(output_video_file, 'rb') as op_vid:
        download = st.download_button(
            '⬇️ Download Recorded Squat Session',
            data=op_vid,
            file_name='output_live.mp4'
        )
        if download:
            st.session_state['download'] = True

# Clean up after download
if os.path.exists(output_video_file) and st.session_state['download']:
    os.remove(output_video_file)
    st.session_state['download'] = False
