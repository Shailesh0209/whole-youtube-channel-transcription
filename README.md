# whole-youtube-channel-transcription

# YouTube Video Transcriber

A command-line tool to download audio from YouTube videos (by video ID), transcribe the audio using OpenAI's Whisper model, and save the transcripts in text files. Supports multiple Indic languages and GPU selection for efficient transcription.

---

## Features

- **Batch Processing:** Transcribe multiple YouTube videos by providing a list of video IDs.
- **Language Support:** Transcribe in Hindi, Kannada, Tamil, Marathi, Gujarati, Punjabi, Bengali, or use automatic language detection.
- **GPU Support:** Select which GPU to use for transcription (if available).
- **YouTube Metadata Fetching:** Retrieves video titles, publish dates, and durations.
- **Resumable:** Skips already downloaded audio and existing transcripts.
- **Environment Configuration:** Supports `.env` files for API keys and configuration.

---

## Requirements

- Python 3.8+
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [openai-whisper](https://github.com/openai/whisper)
- [torch](https://pytorch.org/)
- [google-api-python-client](https://github.com/googleapis/google-api-python-client)
- [python-dotenv](https://github.com/theskumar/python-dotenv)
- pandas, openpyxl, argparse

Install dependencies:

```bash
pip install yt-dlp openai-whisper torch google-api-python-client python-dotenv pandas openpyxl
```

---

## Setup

1. **Clone the repository:**

    ```bash
    git clone <repo-url>
    ```

2. **Create a `.env` file** (optional, for API key):

    ```
    YT_API_KEY=your_youtube_data_api_key
    ```

3. **Prepare a text file with YouTube video IDs:**

    - Each line should contain a single YouTube video ID.
    - Example (`video_ids.txt`):

        ```
        dQw4w9WgXcQ
        3JZ_D3ELwOQ
        ```

---

## Usage

Run the script from the command line:

```bash
python run-transcription-in-server2404.py --video_ids_file video_ids.txt --output_path output_dir --language Hindi --gpu_id 0
```

### Arguments

- `--video_ids_file` (required): Path to the `.txt` file containing YouTube video IDs (one per line).
- `--api_key`: YouTube Data API key (optional if set in `.env`).
- `--output_path`: Directory to save audio files and transcripts (default: `audio_files`).
- `--language`: Transcription language. Choose from: `Auto-detect language`, `Kannada`, `Hindi`, `Tamil`, `Marathi`, `Gujarati`, `Punjabi`, `Bengali`. Default: `Hindi`.
- `--gpu_id`: GPU ID to use for transcription (default: `0`).

If arguments are omitted, the script will prompt for them interactively.

---

## Output

- **Audio Files:** Saved as `<video_id>.mp3` in the output directory.
- **Transcripts:** Saved as `<video_id>_transcription.txt` in the output directory.
- **Logs:** Console output includes progress and error messages.

---

## Example

```bash
python run-transcription-in-server2404.py --video_ids_file video_ids.txt --language "Auto-detect language"
```

---

## Notes

- The script skips downloading or transcribing if files already exist.
- For best performance, use a machine with a CUDA-enabled GPU.
- The YouTube Data API key is required for fetching video metadata.

---

## Troubleshooting

- **CUDA not available:** Ensure you have a compatible GPU and the correct version of PyTorch installed.
- **API errors:** Check your YouTube Data API key and quota.
- **Audio download issues:** Some videos may be restricted or unavailable.

---

## License

MIT License

---

## Acknowledgements

- [OpenAI Whisper](https://github.com/openai/whisper)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [PyTorch](https://pytorch.org/)
- [Google API Python Client](https://github.com/googleapis/google-api-python-client)
