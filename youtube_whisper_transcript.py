import streamlit as st
import os
import yt_dlp
import whisper
import pandas as pd
import csv
from googleapiclient.discovery import build
from datetime import datetime
import openpyxl

# Ensure torch is imported and the required class is registered
try:
    import torch
    # Check if the required class is registered
    if not hasattr(torch.classes, '__path__'):
        raise ImportError("Required class '__path__' is not registered in torch.classes")
except ImportError as e:
    st.error(f"Error importing torch or registering class: {e}")

# Check available GPUs
def get_available_gpus():
    try:
        if not torch.cuda.is_available():
            return []
        
        gpu_count = torch.cuda.device_count()
        available_gpus = []
        
        for i in range(gpu_count):
            gpu_name = torch.cuda.get_device_name(i)
            available_gpus.append((i, f"GPU {i}: {gpu_name}"))
            
        return available_gpus
    except Exception as e:
        st.error(f"Error detecting GPUs: {e}")
        return []

# -----------------------------
# 1. Timestamp Helper
# -----------------------------
def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------
# 2. Language Code Mapping
# -----------------------------
def get_language_code(selected_language):
    language_map = {
        "Kannada": "kn",
        "Hindi": "hi",
        "Tamil": "ta",
        "Marathi": "mr",
        "Gujarati": "gu",
        "Punjabi": "pa",
        "Bengali": "bn",
    }
    return language_map.get(selected_language, None)

# -----------------------------
# 3. Get Video Info from YouTube API
# -----------------------------
def get_video_info(video_ids, api_key):
    """
    Gets video information for a list of video IDs using the YouTube Data API
    """
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Process video IDs in chunks of 50 (API limit)
    video_info_list = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        
        try:
            request = youtube.videos().list(
                part="snippet,contentDetails",
                id=",".join(chunk)
            )
            response = request.execute()
            
            for item in response.get('items', []):
                video_info = {
                    'id': item['id'],
                    'title': item['snippet']['title'],
                    'publishedAt': item['snippet']['publishedAt'],
                    'duration': item['contentDetails']['duration']
                }
                video_info_list.append(video_info)
                
        except Exception as e:
            st.error(f"[{get_timestamp()}] Error fetching video info: {e}")
    
    return video_info_list

# -----------------------------
# 4. Read Video IDs from File
# -----------------------------
def read_video_ids_from_file(file_path):
    """
    Reads video IDs from a text file, one ID per line
    """
    try:
        with open(file_path, 'r') as file:
            video_ids = [line.strip() for line in file if line.strip()]
        return video_ids
    except Exception as e:
        st.error(f"[{get_timestamp()}] Error reading video IDs file: {e}")
        return []

# -----------------------------
# 5. Download Audio
# -----------------------------
def download_youtube_audio(video_id, output_path='.'):
    """
    Downloads the audio of a given YouTube video if it doesn't already exist.
    """
    try:
        os.makedirs(output_path, exist_ok=True)
        audio_file_path = os.path.join(output_path, f"{video_id}.mp3")

        # Check if the file already exists
        if os.path.exists(audio_file_path):
            st.info(f"[{get_timestamp()}] Skipping download for video ID {video_id}. File already exists.")
            return audio_file_path  # Return the existing file path

        # File doesn't exist, proceed to download
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(output_path, f'{video_id}.%(ext)s'),
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        return audio_file_path  # Return the path of the downloaded file

    except Exception as e:
        st.error(f"[{get_timestamp()}] Error while downloading audio for video ID {video_id}: {e}")
        return None

# -----------------------------
# 6. Transcribe Audio and Save to Text File
# -----------------------------
def transcribe_audio_and_save_to_txt(audio_file, video_id, language_code, output_path, auto_detect_language, gpu_id=0):
    """
    Transcribes the audio and saves the transcript to a text file.
    """
    try:
        # Define a path for the transcript text file
        transcript_file_path = os.path.join(output_path, f"{video_id}_transcription.txt")

        # Check if transcription already exists
        if os.path.exists(transcript_file_path):
            st.info(f"[{get_timestamp()}] Skipping transcription for video ID {video_id}. Transcript already exists.")
            return transcript_file_path  # Return the existing transcript path

        # Set GPU device if available
        if torch.cuda.is_available():
            device = f"cuda:{gpu_id}"
            torch.cuda.set_device(gpu_id)
            st.info(f"[{get_timestamp()}] Using {torch.cuda.get_device_name(gpu_id)} for transcription")
        else:
            device = "cpu"
            st.warning(f"[{get_timestamp()}] CUDA not available. Using CPU for transcription (will be slow)")

        # Perform transcription as it doesn't exist
        st.info(f"[{get_timestamp()}] Loading large model for transcription...")
        model = whisper.load_model("large", device=device)
        
        # Use auto-detection or specified language based on setting
        if auto_detect_language:
            st.info(f"[{get_timestamp()}] Using language auto-detection for video ID {video_id}")
            result = model.transcribe(audio_file)  # Let whisper auto-detect the language
        else:
            st.info(f"[{get_timestamp()}] Using specified language ({language_code}) for video ID {video_id}")
            result = model.transcribe(audio_file, language=language_code)

        # Save transcription to a text file
        with open(transcript_file_path, mode="w", encoding="utf-8") as file:
            for segment in result["segments"]:
                # file.write(f"Start Time: {round(segment['start'], 2)}s\n")
                # file.write(f"End Time: {round(segment['end'], 2)}s\n")
                # file.write(f"Transcript: {segment['text']}\n\n")
                # add all segments to the file
                file.write(f"{segment['text']}\n")

        st.success(f"[{get_timestamp()}] Transcript for video ID {video_id} saved to {transcript_file_path}")
        return transcript_file_path

    except Exception as e:
        st.error(f"[{get_timestamp()}] Error while transcribing audio for video ID {video_id}: {e}")
        return None

# -----------------------------
# 7. Streamlit App
# -----------------------------
st.title("YouTube Video Transcriber from ID List")

# 7a. File path for video IDs and API Key
video_ids_file = st.text_input(
    "Enter path to video IDs file (e.g., 'non_transcript_ids.txt')",
    
)
api_key = st.text_input("Enter YouTube Data API Key", type="password")

# 7b. Language settings
auto_detect_language = st.checkbox(
    "Auto-detect language (recommended for mixed-language content or code-switching)",
    value=False,
    help="When enabled, Whisper will automatically detect the language. Best for content with multiple languages."
)

# Only show language selection if not auto-detecting
if not auto_detect_language:
    selected_language = st.selectbox(
        "Select transcription language",
        ["Kannada", "Hindi", "Tamil", "Marathi", "Gujarati", "Punjabi", "Bengali"]
    )
    language_code = get_language_code(selected_language)
else:
    # Set placeholder values (won't be used in auto-detect mode)
    selected_language = None
    language_code = None

# 7c. Output directory
output_path = "audio_files_W2"

# 7d. Dictionary to store each video's transcripts as a separate DataFrame
all_video_dfs = {}

# Add GPU selection
available_gpus = get_available_gpus()
selected_gpu = 0  # Default to first GPU

if available_gpus:
    gpu_options = [f"{gpu[1]}" for gpu in available_gpus]
    selected_gpu_name = st.selectbox(
        "Select GPU for transcription",
        options=gpu_options,
        index=0
    )
    # Get the GPU ID from the selected name
    selected_gpu = [gpu[0] for gpu in available_gpus if gpu[1] == selected_gpu_name][0]
    st.info(f"Using GPU {selected_gpu} for transcription")
else:
    st.warning("No GPUs detected. Will use CPU (very slow for transcription)")

# 7e. Process Videos
if st.button("Process Videos"):
    if not os.path.exists(video_ids_file):
        st.error(f"[{get_timestamp()}] File not found: {video_ids_file}")
        st.stop()
        
    if not api_key:
        st.error("YouTube Data API Key is required")
        st.stop()
    
    # Read video IDs from file
    with st.spinner(f"[{get_timestamp()}] Reading video IDs from file..."):
        video_ids = read_video_ids_from_file(video_ids_file)
        
    if not video_ids:
        st.error(f"[{get_timestamp()}] No video IDs found in the file or file is empty.")
        st.stop()
    
    st.success(f"[{get_timestamp()}] Found {len(video_ids)} video IDs in the file.")
    
    # Get video info from YouTube API
    with st.spinner(f"[{get_timestamp()}] Fetching video information..."):
        video_info_list = get_video_info(video_ids, api_key)
    
    # Display video info table
    if video_info_list:
        st.subheader("Videos to Process")
        video_info_df = pd.DataFrame(video_info_list)
        st.dataframe(video_info_df[['id', 'title']])
    
    # Initialize failed_videos list
    failed_videos = []
    
    # Create a progress bar for overall processing
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Loop through each video
    for idx, video_id in enumerate(video_ids, start=1):
        progress = (idx - 1) / len(video_ids)
        progress_bar.progress(progress)
        status_text.text(f"[{idx}/{len(video_ids)}] Processing video ID: {video_id}")
        
        try:
            # Step 1: Download audio
            audio_file = download_youtube_audio(video_id, output_path)
            if not audio_file:
                raise Exception(f"Audio download failed for video ID: {video_id}")

            # Step 2: Transcribe audio and save to .txt
            transcript_file = transcribe_audio_and_save_to_txt(audio_file, video_id, language_code, output_path, auto_detect_language, selected_gpu)
            if transcript_file is None:
                raise Exception(f"Transcription failed or was skipped for video ID: {video_id}")

            # Step 3: Store transcript DataFrame in dictionary
            all_video_dfs[video_id] = transcript_file

        except Exception as e:
            # Log the error and add the video ID to the failed list
            st.error(f"[{get_timestamp()}] Error for video ID {video_id}: {e}")
            failed_videos.append(video_id)

    # Complete the progress bar
    progress_bar.progress(1.0)
    status_text.text("Processing complete!")
