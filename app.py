import os
import subprocess
import streamlit as st
import yt_dlp

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

    # --- Consolidated Video, Audio, and Subtitle Download Pass ---
    # This prevents the 403 Token reuse penalty by getting everything in one session handshake.
    video_id = "downloaded_video"
    video_filename = f"/tmp/{video_id}.mp4"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"
    subtitle_tmpl = f"/tmp/{video_id}_sub"

    ydl_opts = {
        # FIX 1: Use pre-combined web streams if independent streams trigger 403 errors
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': video_filename,
        'geo_bypass': True,
        'quiet': True,
        
        # FIX 2: Download subtitles simultaneously within the exact same handshake
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'outtmpl': {
            'default': video_filename,
            'subtitle': f"{subtitle_tmpl}.%(ext)s"
        },

        # FIX 3: Force client arrays away from iOS spoofing engines which cause errors
        'extractor_args': {
            'youtube': {
                'player_client': ['web_embedded', 'web', 'tv']
            }
        },
        
        # FIX 4: Replicate standard browser headers
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    }

    if cookie_path:
        ydl_opts['cookiefile'] = cookie_path

    video_title = "Shorts_Video"
    with st.spinner("Downloading video assets directly from YouTube..."):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                video_title = info.get('title', 'Shorts_Video').replace('/', '_').replace('\\', '_')
        except Exception as e:
            st.error(f"Download error: {e}")
            st.stop()

    # --- Step 2: Extract Audio Track ---
    with st.spinner("Extracting audio path..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-q:a", "0", "-map", "a", audio_file, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error("Audio extraction pipeline failed.")
            st.stop()

    # --- Step 3: Crop Video Track ---
    with st.spinner("Cropping vertical video borders..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-an", "-filter:v",
                "crop=in_w:in_h-200:0:0", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                cropped_video, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error("Video processing filter pipeline failed.")
            st.stop()

    st.success("🎉 Processing complete!")

    # --- UI Layout Rendering ---
    st.subheader("🎞️ Original Video")
    st.video(video_filename)
    with open(video_filename, "rb") as f:
        st.download_button("⬇️ Download Original Video", f, file_name=f"{video_title}.mp4")

    st.subheader("▶ Cropped Video (Muted)")
    st.video(cropped_video)
    with open(cropped_video, "rb") as f:
        st.download_button("⬇️ Download Cropped Video", f, file_name=f"{video_title}_cropped.mp4")

    st.subheader("🎵 Extracted Audio")
    st.audio(audio_file)
    with open(audio_file, "rb") as f:
        st.download_button("⬇️ Download Audio", f, file_name=f"{video_title}.mp3")

    # --- Subtitle Tracking ---
    sub_files = [f for f in os.listdir("/tmp") if f.startswith(video_id) and f.endswith(('.vtt', '.srt', '.ass'))]
    if sub_files:
        st.subheader("💬 Available Subtitles")
        for sub_file in sub_files:
            sub_path = os.path.join("/tmp", sub_file)
            ext = os.path.splitext(sub_file)[1]
            with open(sub_path, "rb") as f:
                st.download_button(f"⬇️ Download Subtitle ({ext.replace('.', '').upper()})", f, file_name=f"{video_title}{ext}")
