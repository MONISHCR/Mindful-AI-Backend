import os
import json
from flask import Flask, jsonify, request # Added request
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/generate-questions": {"origins": "http://localhost:3000"}}) # Adjust if your React port is different

try:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash-latest') # Or 'gemini-pro'
    print("Gemini model initialized successfully.")
except Exception as e:
    print(f"Error initializing Gemini model: {e}")
    model = None

def construct_gemini_prompt(user_type="general"):
    common_intro = """
    You are a helpful assistant designing a mood journaling application.
    Generate a list of exactly 10 diverse questions for a user to reflect on their mood and day.
    Provide the output STRICTLY as a JSON array of objects. Each object MUST have a "text" field (the question string)
    and a "type" field (a string: "emotion", "slider", or "text"). Do not include any other text or explanations outside the JSON array.
    The entire output must be a valid JSON array.

    Example of a single question object:
    { "text": "What is one thing you are grateful for today?", "type": "text" }
    """

    if user_type == "student":
        specific_instructions = """
        The user is a student. Tailor the questions accordingly.

        1. The first question MUST be: "How are you feeling about your day as a student?" and its type MUST be "emotion".
        2. The second question MUST be: "On a scale of 0-10, how intense are your current emotions related to your studies or college life?" and its type MUST be "slider".
        3. The third question should be about sleep quality, e.g., "Did you get enough restful sleep last night to feel prepared for your classes?" (type: "text").
        4. The fourth question should be about academic engagement or challenges, e.g., "What was the most engaging or challenging part of your studies today?" (type: "text").
        5. For the remaining 6 questions (questions 5 through 10), generate varied, open-ended questions (type: "text") focusing on student-specific experiences like:
           - Feelings about classes or specific subjects
           - Social interactions at college or with peers
           - Stressors like exams, assignments, or future prospects (e.g., placements)
           - Positive experiences or achievements in their student life
           - Work-life-study balance
           - Specific worries or excitements related to being a student.
        """
    else: # General user
        specific_instructions = """
        The user is a general adult (non-student). Tailor the questions accordingly.

        1. The first question MUST be: "How do you feel right now?" and its type MUST be "emotion".
        2. The second question MUST be: "How would you rate the intensity of your emotions on a scale of 0-10?" and its type MUST be "slider".
        3. The third question should be about sleep, e.g., "Did you sleep well, and roughly how many hours?" (type: "text").
        4. The fourth question should be about meals or daily routine, e.g., "Did you manage to have your regular meals today?" (type: "text").
        5. For the remaining 6 questions (questions 5 through 10), generate varied, open-ended questions (type: "text") focusing on general life experiences like:
           - Social interactions with friends or family
           - Work-related thoughts or feelings (if applicable, otherwise general daily activities)
           - Worries or concerns
           - Moments of gratitude or looking forward to something
           - Daily reflections, frustrations, or small joys
           - Physical activity or well-being.
        """
    return f"{common_intro}\n{specific_instructions}"


@app.route('/generate-questions', methods=['GET'])
def generate_questions_api():
    if not model:
        return jsonify({"error": "Gemini model not initialized"}), 500

    user_type = request.args.get('user_type', 'general').lower() # Get user_type from query param
    if user_type not in ['student', 'general']:
        user_type = 'general' # Default to general if invalid type

    prompt = construct_gemini_prompt(user_type)
    print(f"\n--- Generating questions for user_type: {user_type} ---")
    # print(f"Prompt sent to Gemini:\n{prompt}\n--------------------") # Uncomment for debugging prompt

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        print(f"Gemini Raw Response Text for {user_type}:\n{response_text}") # For debugging

        questions_data = json.loads(response_text)

        if not isinstance(questions_data, list) or not all(isinstance(q, dict) and "text" in q and "type" in q for q in questions_data):
            raise ValueError("Generated data is not in the expected JSON format of a list of objects with 'text' and 'type'.")
        
        if len(questions_data) != 10:
            print(f"Warning: Gemini generated {len(questions_data)} questions for {user_type} instead of 10. Using what was generated.")
        
        # Basic validation of first two questions based on type (text can vary more)
        if not (questions_data[0]['type'] == "emotion"):
             print(f"Warning: First question type for {user_type} not 'emotion'. Gemini generated: {questions_data[0]['type']}")
             # Potentially override or log an error if strictness is paramount
        if not (questions_data[1]['type'] == "slider"):
             print(f"Warning: Second question type for {user_type} not 'slider'. Gemini generated: {questions_data[1]['type']}")

        return jsonify(questions_data)

    except json.JSONDecodeError as e:
        error_message = f"JSONDecodeError for {user_type}: {e}. Response was: {response_text}"
        print(error_message)
        return jsonify({"error": "Failed to parse questions from Gemini", "details": str(e), "raw_response": response_text}), 500
    except Exception as e:
        error_message = f"Error generating questions for {user_type}: {e}"
        print(error_message)
        # Consider returning the prompt that failed for easier debugging
        return jsonify({"error": "Failed to generate questions", "details": str(e), "failed_prompt_user_type": user_type}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5003)