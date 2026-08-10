import os
import subprocess
import streamlit as st
import yt_dlp

# 'ffmpeg' is now a globally available system command
FFMPEG_CMD = "ffmpeg"

st.title("▶ YouTube Shorts Downloader")

# Sidebar Inputs
st.sidebar.header("Input Options")
uploaded_cookies = st.sidebar.file_uploader("Upload your YouTube cookies.txt (optional)", type=["txt"])
youtube_url = st.sidebar.text_input("Enter YouTube Shorts URL:")
download_btn = st.sidebar.button("Download & Process")

if download_btn and youtube_url:
    cookie_path = None
    if uploaded_cookies is not None:
        cookie_path = "/tmp/cookies.txt"
        with open(cookie_path, "wb") as f:
            f.write(uploaded_cookies.getbuffer())
        st.sidebar.success("Cookies uploaded!")

    # --- Step 0: Get Unique Metadata ---
    with st.spinner("Extracting video metadata..."):
        try:
            ydl_meta_opts = {'cookiefile': cookie_path} if cookie_path else {}
            with yt_dlp.YoutubeDL(ydl_meta_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                video_id = info.get('id', 'default_id')
                video_title = info.get('title', 'Shorts_Video')
        except Exception as e:
            st.error(f"Failed to fetch video information: {e}")
            st.stop()

    # Create safe unique file paths using the ID to prevent concurrent user overlaps
    video_filename = f"/tmp/{video_id}.mp4"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"
    subtitle_tmpl = f"/tmp/{video_id}_sub"

    # --- Step 1: Download subtitles only ---
    subtitle_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'skip_download': True,
        'subtitleslangs': ['en'],
        'outtmpl': f"{subtitle_tmpl}.%(ext)s",
        'quiet': True,
    }
    if cookie_path:
        subtitle_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(subtitle_opts) as ydl:
            ydl.download([youtube_url])
    except Exception as e:
        pass  # Fail gracefully if video has no subtitles

    # --- Step 2: Download video & audio ---
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': video_filename,
        'geo_bypass': True,
        'quiet': True,
    }
    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    with st.spinner("Downloading main media streams..."):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
        except Exception as e:
            st.error(f"Download error: {e}")
            st.stop()

    # --- Step 3: Extract Audio via System FFmpeg ---
    with st.spinner("Extracting audio path..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-q:a", "0", "-map", "a", audio_file, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error("Audio extraction pipeline failed.")
            st.stop()

    # --- Step 4: Crop Video via System FFmpeg ---
    with st.spinner("Cropping video borders..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-an", "-filter:v",
                "crop=in_w:in_h-200:0:0", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                cropped_video, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error("Video cropping filter pipeline failed.")
            st.stop()

    st.success("🎉 Processing complete!")

    # --- Layout Displays ---
    st.subheader("🎞️ Original Video")
    st.video(video_filename)
    with open(video_filename, "rb") as f:
        st.download_button("⬇️ Download Original Video", f, file_name=f"{video_title}.mp4")

    st.subheader("▶ Cropped Video (Muted)")
    st.video(cropped_video)
    with open(cropped_video, "rb") as f:
        st.download_button("⬇️ Download Cropped Video", f, file_name=f"{video_title}_cropped.mp4")

    st.subheader("🎵 Extracted Audio Track")
    st.audio(audio_file)
    with open(audio_file, "rb") as f:
        st.download_button("⬇️ Download Audio", f, file_name=f"{video_title}.mp3")

    # --- Subtitles ---
    sub_files = [f for f in os.listdir("/tmp") if f.startswith(f"{video_id}_sub") and f.endswith(('.vtt', '.srt', '.ass'))]
    if sub_files:
        st.subheader("💬 Available Subtitles")
        for sub_file in sub_files:
            sub_path = os.path.join("/tmp", sub_file)
            ext = os.path.splitext(sub_file)[1]
            with open(sub_path, "rb") as f:
                st.download_button(f"⬇️ Download Subtitle ({ext.replace('.', '').upper()})", f, file_name=f"{video_title}{ext}")
