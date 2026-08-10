import os
import re
import subprocess
import streamlit as st
import requests

# 'ffmpeg' is globally provided via your repository's packages.txt file
FFMPEG_CMD = "ffmpeg"

st.set_page_config(page_title="Shorts Downloader", layout="centered")
st.title("▶ YouTube Shorts Downloader")
st.caption("Cloud Native Bypassing Architecture — No Cookies or Local Installs Required")

youtube_url = st.text_input("Enter Your YouTube Shorts URL:")
download_btn = st.button("Download & Process Video")

if download_btn and youtube_url:
    # --- Bulletproof Regex Video ID Isolation ---
    video_id = None
    regex_pattern = r"(?:v=|\/v\/|youtu\.be\/|\/shorts\/|^)([a-zA-Z0-9_-]{11})"
    match = re.search(regex_pattern, youtube_url)
    
    if match:
        video_id = match.group(1)

    if not video_id:
        st.error("❌ Invalid YouTube URL format. Could not parse video ID.")
        st.stop()

    # Define processing tracking variables inside /tmp container environment
    video_filename = f"/tmp/{video_id}.mp4"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"

    # Clean working directory tracks before making new network requests
    for path in [video_filename, audio_file, cropped_video]:
        if os.path.exists(path):
            os.remove(path)

    # --- Secure Multi-Node Failover API Download Routine ---
    # We cycle through free extraction proxy nodes to bypass data center blocks completely
    proxy_apis = [
        f"https://invidious.io{video_id}",
        f"https://kavin.rocks{video_id}",
        f"https://puffyan.us{video_id}"
    ]
    
    download_stream_url = None
    
    with st.spinner("Routing download traffic through residential proxy nodes..."):
        for api_endpoint in proxy_apis:
            try:
                response = requests.get(api_endpoint, timeout=10)
                if response.status_code == 200:
                    res_data = response.json()
                    
                    # Try Parsing standard Piped stream layouts
                    if "videoStreams" in res_data:
                        mp4_streams = [s for s in res_data["videoStreams"] if s.get("mimeType") == "video/mp4" and not s.get("videoOnly")]
                        if mp4_streams:
                            download_stream_url = mp4_streams[0]["url"]
                            break
                    
                    # Try Parsing standard Invidious stream layouts
                    elif "formatStreams" in res_data:
                        mp4_streams = [s for s in res_data["formatStreams"] if "mp4" in s.get("container", "")]
                        if mp4_streams:
                            download_stream_url = mp4_streams[0]["url"]
                            break
            except Exception:
                continue # If one community node is down or blocked, jump to the next one automatically

    if not download_stream_url:
        st.error("❌ All public media bypass gateways are currently overloaded or blocked by YouTube. Please try again in a few minutes.")
        st.stop()

    # --- Fetching Content ---
    with st.spinner("Streaming clean media file into Streamlit container..."):
        try:
            file_response = requests.get(download_stream_url, stream=True, timeout=30)
            with open(video_filename, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            st.error(f"Failed to stream raw file layout: {e}")
            st.stop()

    if not os.path.exists(video_filename) or os.path.getsize(video_filename) < 1000:
        st.error("❌ Media stream was dropped or could not be saved to disk storage.")
        st.stop()

    # --- Processing Layer 1: Audio Extract via native FFmpeg ---
    with st.spinner("Extracting audio stream track..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-q:a", "0", "-map", "a", audio_file, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            st.error("Audio demux processing track crashed.")
            st.stop()

    # --- Processing Layer 2: Video Cropping via native FFmpeg ---
    with st.spinner("Executing vertical aspect crops..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-an", "-filter:v",
                "crop=in_w:in_h-200:0:0", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                cropped_video, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            st.error("Video cropping filter pipeline failed.")
            st.stop()

    st.success("🎉 Processing complete completely code-native!")

    # --- UI Asset Display Layout Panels ---
    st.subheader("🎞️ Original Track File")
    st.video(video_filename)
    with open(video_filename, "rb") as f:
        st.download_button("⬇️ Download Original Video", f, file_name=f"original_{video_id}.mp4")

    st.subheader("▶ Cropped Frame Output (Muted)")
    st.video(cropped_video)
    with open(cropped_video, "rb") as f:
        st.download_button("⬇️ Download Cropped Video", f, file_name=f"cropped_{video_id}.mp4")

    st.subheader("🎵 Clean Extracted Audio Layer")
    st.audio(audio_file)
    with open(audio_file, "rb") as f:
        st.download_button("⬇️ Download Audio Track", f, file_name=f"audio_{video_id}.mp3")
