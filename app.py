import os
import subprocess
import streamlit as st
import requests

FFMPEG_CMD = "ffmpeg"

st.set_page_config(page_title="Shorts Downloader", layout="centered")
st.title("▶ YouTube Shorts Downloader (No Cookies Required)")
st.caption("Using Public Extraction Gateways to Bypass Cloud Blocks")

youtube_url = st.text_input("Enter Your YouTube Shorts URL:")
download_btn = st.button("Download & Process Video")

if download_btn and youtube_url:
    # Extract the unique 11-character video ID from the URL
    video_id = None
    if "shorts/" in youtube_url:
        video_id = youtube_url.split("shorts/")[1].split("?")[0].split("/")[0]
    elif "v=" in youtube_url:
        video_id = youtube_url.split("v=")[1].split("&")[0]
    
    if not video_id or len(video_id) != 11:
        st.error("❌ Invalid YouTube URL format. Please paste a valid Shorts link.")
        st.stop()

    # Define working file paths
    video_filename = f"/tmp/{video_id}.mp4"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"

    # Clean up old files
    for path in [video_filename, audio_file, cropped_video]:
        if os.path.exists(path):
            os.remove(path)

    # --- Step 1: Download via Cobalt Public API Gateway ---
    # Cobalt is an open-source, cookie-free API engine that handles infrastructure blocks
    with st.spinner("Routing stream through public gateway..."):
        try:
            api_url = "https://cobalt.tools"
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
            payload = {
                "url": youtube_url,
                "videoQuality": "720", # Optimized for fast cloud processing
                "filenamePattern": "basic"
            }
            
            response = requests.post(api_url, json=payload, headers=headers)
            res_data = response.json()
            
            if res_data.get("status") == "stream" or res_data.get("status") == "redirect":
                download_stream_url = res_data.get("url")
            else:
                raise Exception(res_data.get("text", "Unknown API error"))

            # Stream the file down to your Streamlit storage layer
            file_response = requests.get(download_stream_url, stream=True)
            with open(video_filename, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        except Exception as e:
            st.error(f"Gateway download failed: {e}. The public node might be overloaded.")
            st.stop()

    # --- Step 2: Extract Audio Track via FFmpeg ---
    with st.spinner("Extracting audio track..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-q:a", "0", "-map", "a", audio_file, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            st.error("Audio conversion failed.")
            st.stop()

    # --- Step 3: Vertical Video Crop via FFmpeg ---
    with st.spinner("Applying crop adjustments..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-an", "-filter:v",
                "crop=in_w:in_h-200:0:0", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                cropped_video, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            st.error("Video processing filter pipeline failed.")
            st.stop()

    st.success("🎉 Processing complete without cookies!")

    # --- UI Layout Rendering ---
    st.subheader("🎞️ Original Video Track")
    st.video(video_filename)
    with open(video_filename, "rb") as f:
        st.download_button("⬇️ Download Original Video", f, file_name=f"{video_id}.mp4")

    st.subheader("▶ Cropped Video Frame (Muted)")
    st.video(cropped_video)
    with open(cropped_video, "rb") as f:
        st.download_button("⬇️ Download Cropped Video", f, file_name=f"{video_id}_cropped.mp4")

    st.subheader("🎵 Extracted Audio Track")
    st.audio(audio_file)
    with open(audio_file, "rb") as f:
        st.download_button("⬇️ Download Audio", f, file_name=f"{video_id}.mp3")
