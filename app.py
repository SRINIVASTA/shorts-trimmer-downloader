import os
import re
import glob
import subprocess
import streamlit as st
import yt_dlp

# 'ffmpeg' is globally provided via your repository's packages.txt file
FFMPEG_CMD = "ffmpeg"

st.set_page_config(page_title="Shorts Downloader", layout="centered")
st.title("▶ YouTube Shorts Downloader")
st.caption("Production-Ready Streamlit Cloud Native Architecture")

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

    # Define unique file paths to completely avoid string concatenation bugs
    base_download_tmpl = f"/tmp/{video_id}.%(ext)s"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"

    # Clean working directory files
    for path in glob.glob(f"/tmp/{video_id}*"):
        try:
            os.remove(path)
        except Exception:
            pass

    # --- Secure Proxy Network Engine Block ---
    # We pass free, public proxy addresses to hide the Streamlit Cloud IP from YouTube
    ydl_opts = {
        'outtmpl': base_download_tmpl,
        'geo_bypass': True,
        'quiet': True,
        'nocheckcertificate': True,
        
        # FIX: Force yt-dlp to route through a public proxy to hide the data-center network sign
        'proxy': 'http://45.152.188.243:3128', 
        
        'extractor_args': {
            'youtube': {
                'player_client': ['web_embedded', 'android_embed', 'web'],
                'skip': ['dash', 'hls']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }

    with st.spinner("Bypassing firewalls and downloading video track directly..."):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
        except Exception as e:
            # Fallback Option: If the primary proxy drops, clear the proxy parameter to try a direct stream link
            try:
                del ydl_opts['proxy']
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([youtube_url])
            except Exception as inner_e:
                st.error(f"Download execution failed: {inner_e}")
                st.info("💡 Tip: YouTube has locked down its security profiles heavily. If this persists, running the file locally on your home computer terminal is the only way to avoid blocks.")
                st.stop()

    # Find the real downloaded video file dynamically (.mp4, .mkv, or .webm)
    downloaded_files = glob.glob(f"/tmp/{video_id}.*")
    downloaded_files = [f for f in downloaded_files if not f.endswith(('_audio.mp3', '_cropped.mp4'))]

    if not downloaded_files:
        st.error("❌ Media stream was dropped or could not be saved to storage disk.")
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

    # --- Processing Layer 2: Video Cropping & Audio Re-muxing via native FFmpeg ---
    with st.spinner("Executing vertical crops and merging audio back in..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, 
                "-filter:v", "crop=in_w:in_h-200:0:0", # Crops 200 pixels off the height
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-c:a", "aac", "-b:a", "192k", # Re-encodes the clean audio right into the file
                cropped_video, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            st.error("Video processing filter pipeline failed.")
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
