import os
import subprocess
import streamlit as st
import requests

FFMPEG_CMD = "ffmpeg"

st.set_page_config(page_title="Shorts Downloader", layout="centered")
st.title("▶ YouTube Shorts Downloader (Resilient API Engine)")
st.caption("Using distributed community networks to process tracks cleanly")

youtube_url = st.text_input("Enter Your YouTube Shorts URL:")
download_btn = st.button("Download & Process Video")

if download_btn and youtube_url:
    # Safely isolate the 11-character video ID from the text string
    video_id = None
    if "shorts/" in youtube_url:
        video_id = youtube_url.split("shorts/")[-1].split("?")[0].split("/")[0]
    elif "v=" in youtube_url:
        video_id = youtube_url.split("v=")[-1].split("&")[0]
    elif "youtu.be/" in youtube_url:
        video_id = youtube_url.split("youtu.be/")[-1].split("?")[0]
        
    if not video_id or len(video_id) != 11:
        st.error("❌ Invalid YouTube URL format. Please supply a valid 11-character video link.")
        st.stop()

    # Define processing variables
    video_filename = f"/tmp/{video_id}.mp4"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"

    # Clean working directory tracks
    for path in [video_filename, audio_file, cropped_video]:
        if os.path.exists(path):
            os.remove(path)

    # --- Fetching via Distributed Piped API Node ---
    with st.spinner("Streaming data stream from public mesh..."):
        try:
            # Direct API request structure using a stable default node mapping layer
            api_url = f"https://kavin.rocks{video_id}"
            response = requests.get(api_url, timeout=15)
            
            if response.status_code != 200:
                raise Exception(f"API server responded with error code {response.status_code}")
                
            res_data = response.json()
            
            # Find the best unencrypted MP4 video track stream link inside the payload array
            video_streams = [
                stream for stream in res_data.get("videoStreams", []) 
                if stream.get("videoOnly") is False and stream.get("mimeType") == "video/mp4"
            ]
            
            if not video_streams:
                # Fallback to absolute standard format if preferred array filter checks empty
                video_streams = [s for s in res_data.get("videoStreams", []) if s.get("mimeType") == "video/mp4"]
                
            if not video_streams:
                raise Exception("No processable unencrypted MP4 streams were uncovered for this Short asset.")
                
            # Grab the highest quality format index link available
            download_stream_url = video_streams[0].get("url")

            # Stream download chunks directly down into local Streamlit container memory
            file_response = requests.get(download_stream_url, stream=True, timeout=30)
            with open(video_filename, "wb") as f:
                for chunk in file_response.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
                        
        except Exception as e:
            st.error(f"❌ Extraction Gateway Failure: {e}. Please ensure the Short is fully public and try again.")
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
    with st.spinner("Executing top and bottom aspect crops..."):
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
