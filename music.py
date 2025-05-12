# backend/app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
# Enable CORS for all routes, allowing requests from your React frontend (e.g., http://localhost:3000)
CORS(app)

YOUTUBE_API_KEY = 'AIzaSyDIUnHwthByH5m26yhNgm31GeMmbUVDEI8'
youtube = None

# --- YouTube API Setup ---
try:
    if not YOUTUBE_API_KEY:
        print("Error: YouTube API Key not found in environment variables (.env file).")
    else:
        # Build the YouTube service object
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        print("YouTube service object created successfully.")
except HttpError as e:
    print(f"Error building YouTube service: {e}")
    print("Ensure the API key is valid and YouTube Data API v3 is enabled.")
    youtube = None
except Exception as e:
    print(f"An unexpected error occurred during API setup: {e}")
    youtube = None

# --- Helper Function (Adapted from Colab) ---
def search_youtube_song(mood, language, max_results=1):
    if not youtube:
        print("Error: YouTube service object is not available.")
        return None, "YouTube service not available. Check backend configuration."

    # Construct search query (same logic as before)
    base_query = f"{language} song music"
    if "sad" in mood.lower() or "anxious" in mood.lower() or "stressed" in mood.lower() or "depressed" in mood.lower():
        query = f"calm soothing comforting {mood} {base_query}"
    elif "happy" in mood.lower() or "joyful" in mood.lower() or "energetic" in mood.lower():
        query = f"upbeat happy energetic {mood} {base_query}"
    elif "calm" in mood.lower() or "peaceful" in mood.lower() or "reflective" in mood.lower():
         query = f"calm peaceful reflective {mood} {base_query}"
    else:
         query = f"{mood} {base_query}"
    query = query.replace(" song song", " song").replace(" music music", " music")

    print(f"Searching YouTube with query: '{query}'") # Log search query

    try:
        search_request = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=max_results,
            type='video',
            topicId='/m/04rlf', # Music topic
            relevanceLanguage=language[:2].lower() if language else 'en' # Use 'en' if language is empty
        )
        search_response = search_request.execute()
        videos = search_response.get('items', [])

        if not videos:
            print("No relevant videos found.")
            return None, "No relevant videos found on YouTube for your request."
        else:
            video_id = videos[0]['id']['videoId']
            video_title = videos[0]['snippet']['title']
            print(f"Found video: '{video_title}' (ID: {video_id})")
            return video_id, None # Return video_id and no error

    except HttpError as e:
        error_content = e.content.decode('utf-8') # Decode error content
        print(f"An HTTP error {e.resp.status} occurred: {error_content}")
        error_message = f"YouTube API error ({e.resp.status}). Check API key/quota."
        if e.resp.status == 403:
             error_message += " Possible quota exceeded or API not enabled/key invalid."
        return None, error_message
    except Exception as e:
        print(f"An unexpected error occurred during YouTube search: {e}")
        return None, f"An unexpected backend error occurred: {e}"

# --- API Endpoint ---
@app.route('/api/search_song', methods=['GET'])
def handle_search():
    # Get mood and language from query parameters
    mood = request.args.get('mood')
    language = request.args.get('language')

    # Basic validation
    if not mood or not language:
        return jsonify({"success": False, "error": "Missing 'mood' or 'language' parameter"}), 400

    if not youtube:
         return jsonify({"success": False, "error": "Backend YouTube service not configured."}), 500

    # Perform the search
    video_id, error = search_youtube_song(mood, language)

    if error:
        # If search failed, return error
        return jsonify({"success": False, "error": error}), 500 # Use 500 for server-side/API issues
    elif video_id:
        # If search succeeded, return video ID
        return jsonify({"success": True, "videoId": video_id})
    else:
        # Should not happen if error is None and video_id is None, but as fallback
        return jsonify({"success": False, "error": "Unknown error occurred during search"}), 500

# --- Run the App ---
if __name__ == '__main__':
    # Runs on http://127.0.0.1:5000 by default
    # debug=True automatically reloads on code changes (good for development)
    app.run(debug=True, port=5003)