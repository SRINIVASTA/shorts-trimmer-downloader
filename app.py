import os
import re
import glob
import subprocess
import streamlit as st
import yt_dlp

# 'ffmpeg' is globally provided via your repository's packages.txt file
FFMPEG_CMD = "ffmpeg"

st.set_page_config(page_title="Local Shorts Downloader", layout="centered")
st.title("▶ YouTube Shorts Downloader")
st.caption("Optimized for Residential Networks — No Cookies Required")

# Workspace Controls
youtube_url = st.text_input("Enter Your YouTube Shorts URL:")
download_btn = st.button("Download & Process Video")

if download_btn and youtube_url:
    # --- Robust Regex Video ID Extraction ---
    video_id = None
    regex_pattern = r"(?:v=|\/v\/|youtu\.be\/|\/shorts\/|^)([a-zA-Z0-9_-]{11})"
    match = re.search(regex_pattern, youtube_url)
    
    if match:
        video_id = match.group(1)

    if not video_id:
        st.error("❌ Invalid YouTube URL format. Could not parse video ID.")
        st.stop()

    # Pre-clean matching files in directory to prevent container conflicts
    for old_file in glob.glob(f"/tmp/{video_id}*"):
        try:
            os.remove(old_file)
        except Exception:
            pass

    # Dynamic fallback output paths
    base_download_tmpl = f"/tmp/{video_id}.%(ext)s"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"

    # --- Resident Network yt-dlp Configuration Block ---
    # FIX: Bypasses the bot check by mimicking a vanilla web browser player
    ydl_opts = {
        'format': 'best', # Pulls pre-merged stream to avoid extra handshakes
        'outtmpl': base_download_tmpl,
        'geo_bypass': True,
        'quiet': True,
        'nocheckcertificate': True,
        
        # CRITICAL FIX: Tells YouTube you are using a desktop browser client, not an automated app
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'web_embedded'],
                'skip': ['dash', 'hls'] # Skips streaming chunks prone to bot-checks
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
    }

    with st.spinner("Downloading video track using browser emulation..."):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
        except Exception as e:
            st.error(f"Download execution failed: {e}")
            st.info("💡 If this fails on your resident network, make sure to reboot the app in the Streamlit panel to clear old connection tokens.")
            st.stop()

    # Find the real downloaded video path dynamically
    downloaded_files = glob.glob(f"/tmp/{video_id}.*")
    downloaded_files = [f for f in downloaded_files if not f.endswith(('_audio.mp3', '_cropped.mp4'))]

    if not downloaded_files:
        st.error("❌ Media stream was dropped or could not be saved to disk storage.")
        st.stop()
        
    video_filename = downloaded_files[0]

    # --- Processing Layer 1: Audio Extract via native FFmpeg ---
    with st.spinner("Extracting audio stream track..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-q:a", "0", "-map", "a", audio_file, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            st.error("Audio processing track crashed.")
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

    st.success("🎉 Processing complete!")

    # --- UI Asset Display Layout Panels ---
    st.subheader("╠ Original Track File")
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
