# YouTubeTranscriptApi.py
import os
import argparse
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi

def get_video_title(video_id):
    """
    Gets the title of a YouTube video.
    
    Args:
        video_id (str): The YouTube video ID.
        
    Returns:
        str: The title of the video or the video ID if title retrieval fails.
    """
    try:
        # Access the YouTube page and extract the title
        url = f"https://www.youtube.com/watch?v={video_id}"
        response = requests.get(url)
        
        if response.status_code == 200:
            # Look for the title in the HTML
            title_match = re.search(r'<title>(.*?) - YouTube</title>', response.text)
            if title_match:
                return title_match.group(1)
        
        # If we can't get the title, return the video ID
        return video_id
    except Exception as e:
        print(f"Error getting video title: {str(e)}")
        return video_id

def sanitize_filename(title):
    """
    Sanitizes a string to make it a valid filename.
    
    Args:
        title (str): The string to sanitize.
        
    Returns:
        str: A sanitized string safe for use as a filename.
    """
    # Replace invalid filename characters with hyphens
    sanitized = re.sub(r'[\\/*?:"<>|]', '-', title)
    # Replace multiple spaces with a single space
    sanitized = re.sub(r'\s+', ' ', sanitized)
    # Trim to reasonable length
    if len(sanitized) > 100:
        sanitized = sanitized[:97] + '...'
    return sanitized.strip()

def get_available_transcripts(video_id):
    """
    Gets a list of all available transcripts for a video.
    
    Args:
        video_id (str): The YouTube video ID.
        
    Returns:
        list: A list of available transcript objects.
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        return transcript_list
    except Exception as e:
        raise Exception(f"Error listing transcripts for {video_id}: {str(e)}")

def fetch_original_transcript(video_id):
    """
    Fetches the original transcript for a given YouTube video ID.
    
    Args:
        video_id (str): The YouTube video ID.
        
    Returns:
        tuple: (transcript_data, language_code, is_generated)
    """
    try:
        transcript_list = get_available_transcripts(video_id)
        
        # Get the original/manual transcript if available
        manual_transcripts = []
        generated_transcripts = []
        
        for transcript in transcript_list:
            if transcript.is_generated:
                generated_transcripts.append(transcript)
            else:
                manual_transcripts.append(transcript)
        
        # Prioritize manual transcripts over generated ones
        if manual_transcripts:
            selected = manual_transcripts[0]  # Take the first manual transcript
        elif generated_transcripts:
            selected = generated_transcripts[0]  # Take the first generated transcript
        else:
            raise Exception("No transcripts available")
            
        transcript_data = selected.fetch()
        return transcript_data, selected.language_code, selected.is_generated
        
    except Exception as e:
        raise Exception(f"Error fetching transcript: {str(e)}")

def extract_transcript_text(transcript_data):
    """
    Extracts plain text from transcript data in any format, as a single passage.
    
    Args:
        transcript_data: Transcript data in any format (dict, list, FetchedTranscript, etc.)
        
    Returns:
        str: Plain text of the transcript as a single passage
    """
    text_parts = []
    
    # Handle FetchedTranscript format
    if hasattr(transcript_data, 'snippets') and hasattr(transcript_data.snippets, '__iter__'):
        for snippet in transcript_data.snippets:
            if hasattr(snippet, 'text'):
                text_parts.append(snippet.text)
    
    # Handle list of dictionaries format
    elif isinstance(transcript_data, list):
        for item in transcript_data:
            if isinstance(item, dict) and 'text' in item:
                text_parts.append(item['text'])
            elif hasattr(item, 'text'):
                text_parts.append(item.text)
            else:
                # Try to convert to string if we can't extract text otherwise
                try:
                    text_parts.append(str(item))
                except:
                    pass
    
    # Handle string or other formats
    else:
        try:
            text_parts.append(str(transcript_data))
        except:
            pass
    
    return ' '.join(text_parts)

def process_video_ids_file(file_path, output_dir="transcripts"):
    """
    Processes a file of video IDs and saves transcripts to individual files.
    
    Args:
        file_path (str): Path to the text file with video IDs.
        output_dir (str): Directory to save transcript files.
    """
    # Make sure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Read video IDs from file
    with open(file_path, 'r') as f:
        video_ids = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(video_ids)} video IDs in file.")
    
    success_count = 0
    
    # Process each video ID
    for i, video_id in enumerate(video_ids, 1):
        print(f"Processing {i}/{len(video_ids)}: {video_id}")
        
        try:
            # Get video title
            video_title = get_video_title(video_id)
            safe_title = sanitize_filename(video_title)
            
            # First, list all available transcripts
            transcript_list = get_available_transcripts(video_id)
            print(f"  Available transcripts:")
            for transcript in transcript_list:
                transcript_type = "Generated" if transcript.is_generated else "Manual"
                print(f"  - {transcript.language} ({transcript.language_code}) [{transcript_type}]")
            
            # Fetch original transcript
            transcript_data, language_code, is_generated = fetch_original_transcript(video_id)
            transcript_type = "generated" if is_generated else "manual"
            
            # Extract text content only
            transcript_text = extract_transcript_text(transcript_data)
            
            # Save to file using the video title
            output_file = os.path.join(output_dir, f"{safe_title}.txt")
            
            with open(output_file, 'w', encoding='utf-8') as f:
                # Write only the transcript text
                f.write(transcript_text)
            
            print(f"  Success: Saved {language_code} ({transcript_type}) transcript to {output_file}")
            success_count += 1
            
        except Exception as e:
            print(f"  Failed: {str(e)}")
    
    print(f"\nSummary: Successfully processed {success_count} out of {len(video_ids)} videos.")

def save_all_available_transcripts(video_id, output_dir="transcripts"):
    """
    Saves all available transcripts for a video ID.
    
    Args:
        video_id (str): The YouTube video ID.
        output_dir (str): Directory to save transcript files.
    """
    try:
        # Get video title
        video_title = get_video_title(video_id)
        safe_title = sanitize_filename(video_title)
        
        transcript_list = get_available_transcripts(video_id)
        
        for transcript in transcript_list:
            language_code = transcript.language_code
            is_generated = transcript.is_generated
            transcript_type = "generated" if is_generated else "manual"
            
            try:
                # Fetch the transcript
                transcript_data = transcript.fetch()
                
                # Extract text content only
                transcript_text = extract_transcript_text(transcript_data)
                
                # Create filename using the video title and language
                output_file = os.path.join(output_dir, f"{safe_title}_{language_code}.txt")
                
                # Save to file - only transcript text
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(transcript_text)
                
                print(f"Saved {language_code} ({transcript_type}) transcript to {output_file}")
            
            except Exception as e:
                print(f"Error saving {language_code} transcript: {str(e)}")
                # Add debug info
                print(f"Debug: transcript_data type: {type(transcript_data)}")
        
    except Exception as e:
        print(f"Error processing transcripts for {video_id}: {str(e)}")

def process_video_ids_file_all_languages(file_path, output_dir="transcripts"):
    """
    Processes a file of video IDs and saves ALL available transcripts for each video.
    
    Args:
        file_path (str): Path to the text file with video IDs.
        output_dir (str): Directory to save transcript files.
    """
    # Make sure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Read video IDs from file
    with open(file_path, 'r') as f:
        video_ids = [line.strip() for line in f if line.strip()]
    
    print(f"Found {len(video_ids)} video IDs in file.")
    
    # Process each video ID
    for i, video_id in enumerate(video_ids, 1):
        print(f"Processing {i}/{len(video_ids)}: {video_id}")
        
        try:
            save_all_available_transcripts(video_id, output_dir)
        except Exception as e:
            print(f"Failed to process {video_id}: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch YouTube transcripts from video IDs in a file")
    parser.add_argument("input_file", help="Path to text file containing YouTube video IDs (one per line)")
    parser.add_argument("-o", "--output_dir", default="transcripts", 
                        help="Directory to save transcript files (default: transcripts)")
    parser.add_argument("-a", "--all_languages", action="store_true",
                        help="Save all available language transcripts for each video")
    
    args = parser.parse_args()
    
    if args.all_languages:
        process_video_ids_file_all_languages(args.input_file, args.output_dir)
    else:
        process_video_ids_file(args.input_file, args.output_dir)
