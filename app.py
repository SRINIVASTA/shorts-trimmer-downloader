import os
import subprocess
import streamlit as st
import yt_dlp

# 'ffmpeg' is globally provided via your repository's packages.txt file
FFMPEG_CMD = "ffmpeg"

st.set_page_config(page_title="Shorts Downloader", layout="centered")
st.title("▶ YouTube Shorts Downloader")
st.caption("Production-Ready Streamlit Cloud Native Architecture")

# Sidebar Workspace Configuration
st.sidebar.header("🔑 Authentication & Inputs")

# --- Step-by-Step Guide for Users ---
with st.sidebar.expander("ℹ️ How to get your cookies.txt"):
    st.markdown("""
    1. Install the browser extension **'Get cookies.txt LOCALLY'** (Chrome/Firefox).
    2. Open a **New Incognito / Private Window**.
    3. Go to **YouTube.com** and log into your account.
    4. Click the extension icon and select **'Export As'** to save the text file.
    5. **Important:** Close the Incognito window immediately without clicking anything else on YouTube (this prevents session keys from rotating).
    """)

uploaded_cookies = st.sidebar.file_uploader(
    "Upload your YouTube cookies.txt file:", 
    type=["txt"]
)
youtube_url = st.sidebar.text_input("Enter YouTube Shorts URL:")
download_btn = st.sidebar.button("Download & Process")

if download_btn and youtube_url:
    # Handle mandatory data-center verification check with clear UI feedback
    if uploaded_cookies is None:
        st.error("⚠️ **Authentication Required:** YouTube blocks shared cloud hosting IP addresses. Please follow the sidebar instructions to upload a valid `cookies.txt` file to run this request.")
        st.stop()
        
    # Write cookies binary stream directly to a protected temporary storage path
    cookie_path = "/tmp/cookies.txt"
    if os.path.exists(cookie_path):
        os.remove(cookie_path)
        
    with open(cookie_path, "wb") as f:
        f.write(uploaded_cookies.getbuffer())
    st.sidebar.success("Session tokens injected!")

    # Establish deterministic filename templates using static IDs to prevent multi-user collisions
    video_id = "downloaded_video"
    video_filename = f"/tmp/{video_id}.mp4"
    audio_file = f"/tmp/{video_id}_audio.mp3"
    cropped_video = f"/tmp/{video_id}_cropped.mp4"
    subtitle_tmpl = f"/tmp/{video_id}_sub"

    # Deep clean working folder layers before parsing new streams
    for path in [video_filename, audio_file, cropped_video]:
        if os.path.exists(path):
            os.remove(path)

    # --- Consolidated yt-dlp Configuration Block ---
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'geo_bypass': True,
        'quiet': True,
        'cookiefile': cookie_path, # Injects authentication directly into the primary handshake
        
        'outtmpl': {
            'default': video_filename,
            'subtitle': f"{subtitle_tmpl}.%(ext)s"
        },
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],

        # Bypasses hardware DRM restrictions and bot traps by disabling iOS/TV spoof profiles
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'web_embedded', 'android_embed'],
                'skip': ['dash', 'hls']
            }
        },
        
        # Emulates vanilla desktop browser interactions
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }

    video_title = "Shorts_Video"
    with st.spinner("Passing bot checks and fetching streams from YouTube..."):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=True)
                raw_title = info.get('title', 'Shorts_Video')
                video_title = "".join(c for c in raw_title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        except Exception as e:
            st.error(f"Download execution failed: {e}")
            if "Sign in to confirm you’re not a bot" in str(e):
                st.info("💡 **Tip:** Your uploaded cookie file might have expired. Try exporting a new one from an fresh Incognito window.")
            if os.path.exists(cookie_path):
                os.remove(cookie_path)
            st.stop()

    # --- Processing Layer 1: Audio Extraction ---
    with st.spinner("Extracting audio stream..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-q:a", "0", "-map", "a", audio_file, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error("Audio demuxer failed to extract track asset.")
            st.stop()

    # --- Processing Layer 2: Video Cropping Filter ---
    with st.spinner("Applying vertical crop filters..."):
        try:
            subprocess.run([
                FFMPEG_CMD, "-i", video_filename, "-an", "-filter:v",
                "crop=in_w:in_h-200:0:0", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                cropped_video, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error("FFmpeg filter graph processing step failed.")
            st.stop()

    st.success("🎉 Processing complete!")

    # --- Content Presentation Layout ---
    st.subheader("🎞️ Original Video Track")
    st.video(video_filename)
    with open(video_filename, "rb") as f:
        st.download_button("⬇️ Download Original Video", f, file_name=f"{video_title}.mp4")

    st.subheader("▶ Cropped Video Frame (Muted)")
    st.video(cropped_video)
    with open(cropped_video, "rb") as f:
        st.download_button("⬇️ Download Cropped Video", f, file_name=f"{video_title}_cropped.mp4")

    st.subheader("🎵 High-Quality Audio Extract")
    st.audio(audio_file)
    with open(audio_file, "rb") as f:
        st.download_button("⬇️ Download Audio Track", f, file_name=f"{video_title}.mp3")

    # --- Subtitle Discovery Block ---
    sub_files = [f for f in os.listdir("/tmp") if f.startswith(video_id) and f.endswith(('.vtt', '.srt', '.ass'))]
    if sub_files:
        st.subheader("💬 Available Text Captions")
        for sub_file in sub_files:
            sub_path = os.path.join("/tmp", sub_file)
            ext = os.path.splitext(sub_file)[1]
            with open(sub_path, "rb") as f:
                st.download_button(
                    f"⬇️ Download Subtitle ({ext.replace('.', '').upper()})", 
                    f, 
                    file_name=f"{video_title}{ext}"
                )

    # Privacy safety: wipe cookie file data at execution finish
    if os.path.exists(cookie_path):
        os.remove(cookie_path)
