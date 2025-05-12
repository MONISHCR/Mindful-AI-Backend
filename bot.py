# backend/app.py
import os
import google.generativeai as genai
import json
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv() # Load variables from .env file
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# --- Flask App Setup ---
app = Flask(__name__)
# Enable CORS for requests from the React frontend (adjust origin if needed)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# --- Gemini Configuration ---
MODEL_NAME = 'gemini-1.5-flash' # Or 'gemini-pro'
LOG_FILE = 'interactions.json'

try:
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in environment variables.")
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
    print(f"Successfully configured Gemini with model: {MODEL_NAME}")
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    model = None # Ensure model is None if setup fails

# Optional: Generation Configuration
generation_config = {
    "temperature": 0.75,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 1024,
}

# Safety Settings (Important!)
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Interaction Logging ---
def load_interactions(filename=LOG_FILE):
    """Loads interactions from the JSON log file."""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading interactions log: {e}. Starting fresh.")
            return []
    return []

def save_interactions(interaction, filename=LOG_FILE):
    """Appends a single interaction to the JSON log file."""
    interactions_log = load_interactions(filename)
    interactions_log.append(interaction)
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(interactions_log, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"\nError saving interaction to {filename}: {e}")


# --- Core Gemini Interaction Function ---
def get_supportive_answer(question):
    """Sends a question to Gemini and returns the answer or error."""
    if not model:
        return "Error: AI Model not initialized. Check API key and configuration."

    # Prompt Engineering (same as your original script)
    prompt = f"""You are an AI assistant designed to be supportive and provide general motivation and encouragement.
You can answer questions about psychological concepts for educational purposes, OR you can respond to requests for motivation with uplifting perspectives, positive reframing, and general encouragement.
Think like a helpful guide, offering constructive insights based on common knowledge and positive psychology principles (without claiming expertise you don't have).

**Important Boundaries:**
*   You are an AI and CANNOT provide therapy, medical advice, diagnosis, or specific personal life coaching.
*   Do NOT act like a human therapist or counselor.
*   Focus on general encouragement, positive affirmations, and reframing techniques.
*   If the user asks for help with a serious mental health crisis or expresses severe distress, gently state your limitations as an AI and strongly recommend they seek help from a qualified professional (like a therapist, counselor, doctor, or a crisis hotline). Do not attempt to handle the crisis yourself.
*   Keep responses positive, constructive, and safe.

User Question: {question}

Supportive Answer:"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        if response.parts:
            answer = response.text
            # Optional: Add reminder (consider if this is better handled on frontend)
            answer += "\n\n(Remember: I'm an AI providing general information and encouragement. For specific advice or mental health support, please consult a qualified professional.)"
            return answer
        else:
            block_reason = "Unknown (possibly safety filters or empty response)"
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback and hasattr(response.prompt_feedback, 'block_reason') and response.prompt_feedback.block_reason:
                block_reason = response.prompt_feedback.block_reason.name
            elif response.candidates and response.candidates[0].finish_reason != 'STOP':
                block_reason = f"Blocked: Finish Reason - {response.candidates[0].finish_reason}"
            return f"Error: The model could not generate a response. Reason: {block_reason}"

    except Exception as e:
        print(f"\nAn error occurred during API call: {e}")
        # You might want more specific error handling here in a production app
        return f"Error: Could not get an answer from the AI model. Details: {str(e)}"


# --- API Endpoint ---
@app.route('/api/ask', methods=['POST'])
def ask_gemini():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    data = request.get_json()
    question = data.get('question')

    if not question or not question.strip():
        return jsonify({"error": "Question cannot be empty"}), 400

    print(f"Received question: {question}") # Log received question

    answer = get_supportive_answer(question)

    # Log the interaction
    interaction_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "question": question,
        "answer": answer # Store the actual answer sent back
    }
    save_interactions(interaction_data)

    # Check if the answer indicates an error from the get_supportive_answer function
    if answer.startswith("Error:"):
         # Return a server error status code if the AI failed
        return jsonify({"answer": answer}), 500
    else:
         # Return the successful answer
        return jsonify({"answer": answer}), 200


# --- Basic Root Route (Optional) ---
@app.route('/')
def index():
    return "Psychology & Motivation Bot Backend is running!"

# --- Run the App ---
if __name__ == '__main__':
    # Use 0.0.0.0 to make it accessible on your network if needed,
    # otherwise localhost (127.0.0.1) is fine.
    # Debug=True is useful for development but should be False in production.
    app.run(host='0.0.0.0', port=5001, debug=True)