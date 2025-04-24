import os
import yt_dlp
import whisper
import pandas as pd
import csv
from googleapiclient.discovery import build
from datetime import datetime
import openpyxl
import argparse
import sys

# Add dotenv import
from dotenv import load_dotenv

try:
    import torch
    if not hasattr(torch.classes, '__path__'):
        raise ImportError("Required class '__path__' is not registered in torch.classes")
except ImportError as e:
    print(f"Error importing torch or registering class: {e}")
    sys.exit(1)

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
        print(f"Error detecting GPUs: {e}")
        return []

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

def get_video_info(video_ids, api_key):
    youtube = build('youtube', 'v3', developerKey=api_key)
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
            print(f"[{get_timestamp()}] Error fetching video info: {e}")
    return video_info_list

def read_video_ids_from_file(file_path):
    try:
        with open(file_path, 'r') as file:
            video_ids = [line.strip() for line in file if line.strip()]
        return video_ids
    except Exception as e:
        print(f"[{get_timestamp()}] Error reading video IDs file: {e}")
        return []

def download_youtube_audio(video_id, output_path='.'):
    try:
        os.makedirs(output_path, exist_ok=True)
        audio_file_path = os.path.join(output_path, f"{video_id}.mp3")
        if os.path.exists(audio_file_path):
            print(f"[{get_timestamp()}] Skipping download for video ID {video_id}. File already exists.")
            return audio_file_path
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
        return audio_file_path
    except Exception as e:
        print(f"[{get_timestamp()}] Error while downloading audio for video ID {video_id}: {e}")
        return None

def transcribe_audio_and_save_to_txt(audio_file, video_id, language_code, output_path, auto_detect_language, gpu_id=0):
    try:
        transcript_file_path = os.path.join(output_path, f"{video_id}_transcription.txt")
        if os.path.exists(transcript_file_path):
            print(f"[{get_timestamp()}] Skipping transcription for video ID {video_id}. Transcript already exists.")
            return transcript_file_path
        if torch.cuda.is_available():
            device = f"cuda:{gpu_id}"
            torch.cuda.set_device(gpu_id)
            print(f"[{get_timestamp()}] Using {torch.cuda.get_device_name(gpu_id)} for transcription")
        else:
            device = "cpu"
            print(f"[{get_timestamp()}] CUDA not available. Using CPU for transcription (will be slow)")
        print(f"[{get_timestamp()}] Loading large model for transcription...")
        model = whisper.load_model("large", device=device)
        if auto_detect_language:
            print(f"[{get_timestamp()}] Using language auto-detection for video ID {video_id}")
            result = model.transcribe(audio_file)
        else:
            print(f"[{get_timestamp()}] Using specified language ({language_code}) for video ID {video_id}")
            result = model.transcribe(audio_file, language=language_code)
        with open(transcript_file_path, mode="w", encoding="utf-8") as file:
            for segment in result["segments"]:
                file.write(f"{segment['text']}\n")
        print(f"[{get_timestamp()}] Transcript for video ID {video_id} saved to {transcript_file_path}")
        return transcript_file_path
    except Exception as e:
        print(f"[{get_timestamp()}] Error while transcribing audio for video ID {video_id}: {e}")
        return None

def main():
    # Load .env file if present
    load_dotenv()

    parser = argparse.ArgumentParser(description="YouTube Video Transcriber from ID List (Server Mode)")
    parser.add_argument('--video_ids_file', help="Path to video IDs .txt file (one ID per line)")
    parser.add_argument('--api_key', help="YouTube Data API Key (if not set, will use YT_API_KEY from .env)")
    parser.add_argument('--output_path', default="audio_files", help="Directory to save audio and transcripts")
    parser.add_argument('--language', choices=[
        "Auto-detect language", "Kannada", "Hindi", "Tamil", "Marathi", "Gujarati", "Punjabi", "Bengali"
    ], help="Transcription language. Default: Hindi. Choose 'Auto-detect language' for automatic detection.")
    parser.add_argument('--gpu_id', type=int, default=0, help="GPU ID to use for transcription (default: 0)")
    args = parser.parse_args()

    # Prompt for input file if not provided
    video_ids_file = args.video_ids_file
    while not video_ids_file:
        video_ids_file = input("Enter path to video IDs .txt file: ").strip()
    # Ensure the input file is a .txt file
    if not video_ids_file.lower().endswith('.txt'):
        print("Error: --video_ids_file must be a .txt file")
        sys.exit(1)
    if not os.path.exists(video_ids_file):
        print(f"[{get_timestamp()}] File not found: {video_ids_file}")
        sys.exit(1)

    # Prefer command-line api_key, else fallback to .env
    api_key = args.api_key or os.getenv("YT_API_KEY")
    if not api_key:
        print("YouTube Data API Key is required (set --api_key or YT_API_KEY in .env)")
        sys.exit(1)

    # Language selection logic with auto-detect as an option
    language = args.language
    auto_detect_language = False
    languages = ["Auto-detect language", "Kannada", "Hindi", "Tamil", "Marathi", "Gujarati", "Punjabi", "Bengali"]
    if not language:
        print("Select transcription language:")
        for idx, lang in enumerate(languages, 1):
            print(f"{idx}. {lang}")
        choice = input("Enter the number for language [3]: ").strip()
        if not choice:
            language = "Hindi"
        else:
            try:
                idx = int(choice)
                if 1 <= idx <= len(languages):
                    language = languages[idx - 1]
                else:
                    print("Invalid selection. Defaulting to Hindi.")
                    language = "Hindi"
            except Exception:
                print("Invalid input. Defaulting to Hindi.")
                language = "Hindi"
    if language == "Auto-detect language":
        auto_detect_language = True
        language_code = None
        print("Selected: Auto-detect language")
    else:
        auto_detect_language = False
        language_code = get_language_code(language)
        print(f"Selected language: {language}")

    video_ids = read_video_ids_from_file(video_ids_file)
    if not video_ids:
        print(f"[{get_timestamp()}] No video IDs found in the file or file is empty.")
        sys.exit(1)
    print(f"[{get_timestamp()}] Found {len(video_ids)} video IDs in the file.")

    video_info_list = get_video_info(video_ids, api_key)
    if video_info_list:
        print(f"[{get_timestamp()}] Video info fetched for {len(video_info_list)} videos.")

    failed_videos = []
    for idx, video_id in enumerate(video_ids, start=1):
        print(f"[{idx}/{len(video_ids)}] Processing video ID: {video_id}")
        try:
            audio_file = download_youtube_audio(video_id, args.output_path)
            if not audio_file:
                raise Exception(f"Audio download failed for video ID: {video_id}")
            transcript_file = transcribe_audio_and_save_to_txt(
                audio_file, video_id, language_code, args.output_path, auto_detect_language, args.gpu_id
            )
            if transcript_file is None:
                raise Exception(f"Transcription failed or was skipped for video ID: {video_id}")
        except Exception as e:
            print(f"[{get_timestamp()}] Error for video ID {video_id}: {e}")
            failed_videos.append(video_id)
    print(f"Processing complete! Failed videos: {failed_videos}")

if __name__ == "__main__":
    main()