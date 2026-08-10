import os
import stat
import subprocess
import streamlit as st
import yt_dlp

FFMPEG_PATH = "/tmp/ffmpeg"

def download_ffmpeg():
    if os.path.isfile(FFMPEG_PATH):
        return
    url = "https://johnvansickle.com"
    tar_path = "/tmp/ffmpeg.tar.xz"
    st.sidebar.info("Downloading ffmpeg binary (~30MB)...")
    subprocess.run(["curl", "-L", url, "-o", tar_path], check=True)
    subprocess.run(["tar", "-xf", tar_path, "-C", "/tmp"], check=True)
    os.remove(tar_path)

    extracted_dir = next(
        (os.path.join("/tmp", d) for d in os.listdir("/tmp")
         if d.startswith("ffmpeg") and os.path.isdir(os.path.join("/tmp", d))),
        None
    )
    if extracted_dir is None:
        st.sidebar.error("Failed to find extracted ffmpeg directory.")
        st.stop()

    src_ffmpeg = os.path.join(extracted_dir, "ffmpeg")
    if not os.path.isfile(src_ffmpeg):
        st.sidebar.error("ffmpeg binary not found inside extracted archive.")
        st.stop()

    os.rename(src_ffmpeg, FFMPEG_PATH)
    os.chmod(FFMPEG_PATH, stat.S_IRWXU)
    st.sidebar.success("ffmpeg downloaded and ready.")

def get_ffmpeg_dir():
    return os.path.dirname(FFMPEG_PATH)

st.title("▶ YouTube Shorts Downloader")

download_ffmpeg()

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

    # Fetch info first to get a safe, unique ID for file mapping
    with st.spinner("Extracting video metadata..."):
        try:
            with yt_dlp.YoutubeDL({'cookiefile': cookie_path} if cookie_path else {}) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                video_id = info.get('id', 'default_id')
                video_title = info.get('title', 'video')
        except Exception as e:
            st.error(f"Failed to fetch video info: {e}")
            st.stop()

    # Define unique absolute paths based on video ID
    base_path = f"/tmp/{video_id}"
    video_filename = f"{base_path}.mp4"
    audio_file = f"{base_path}_audio.mp3"
    cropped_video = f"{base_path}_cropped.mp4"
    subtitle_tmpl = f"{base_path}_sub"

    # --- 1. Download subtitles ---
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

    with st.spinner("Searching for subtitles..."):
        try:
            with yt_dlp.YoutubeDL(subtitle_opts) as ydl:
                ydl.download([youtube_url])
        except Exception as e:
            st.warning(f"Subtitle processing skipped: {e}")

    # --- 2. Download video & audio ---
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': video_filename,
        'ffmpeg_location': get_ffmpeg_dir(),
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

    # --- 3. Process Audio ---
    with st.spinner("Extracting audio path..."):
        try:
            subprocess.run([
                FFMPEG_PATH, "-i", video_filename, "-q:a", "0", "-map", "a", audio_file, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error(f"Audio extraction failed: {e}")
            st.stop()

    # --- 4. Process Cropped Video ---
    with st.spinner("Cropping video borders..."):
        try:
            subprocess.run([
                FFMPEG_PATH, "-i", video_filename, "-an", "-filter:v",
                "crop=in_w:in_h-200:0:0", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                cropped_video, "-y"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            st.error(f"Video cropping failed: {e}")
            st.stop()

    st.success("🎉 All processes complete!")

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

    # --- Subtitle display logic using deterministic naming ---
    sub_files = [f for f in os.listdir("/tmp") if f.startswith(f"{video_id}_sub") and f.endswith(('.vtt', '.srt', '.ass'))]
    if sub_files:
        st.subheader("💬 Available Subtitles")
        for sub_file in sub_files:
            sub_path = os.path.join("/tmp", sub_file)
            ext = os.path.splitext(sub_file)[1]
            with open(sub_path, "rb") as f:
                st.download_button(f"⬇️ Download Subtitle ({ext.upper()})", f, file_name=f"{video_title}{ext}")
    else:
        st.info("No English subtitles found for this asset.")
