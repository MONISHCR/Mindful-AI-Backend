from flask import Flask, request, jsonify, make_response # type: ignore
import google.generativeai as genai # type: ignore
import os
from huggingface_hub import InferenceClient # type: ignore
from dotenv import load_dotenv # type: ignore
from flask_cors import CORS # type: ignore
import time
import json
import re

# Load environment variables
load_dotenv()

# Set up API keys
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
hf_api_key = os.getenv("HF_API_KEY")

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

# models = list(genai.list_models())
# print("Available Models:", models)

def get_journal_analysis(prompt: str):
    model = genai.GenerativeModel("gemini-1.5-flash-002")

    instruction = """
    You are an AI assistant trained to analyze journal entries and assess the mental health state of the writer.
    Analyze the emotional tone, sentiment, and overall mental state based on the text provided.

    **Task:**
    - Assign a **mental health score** between **1 to 10**:
      - **1** = Very Happy (Positive mindset, motivated, relaxed)
      - **5** = Neutral (Balanced mood, neither too happy nor too sad)
      - **10** = Very Depressed (Hopelessness, sadness, despair)
    - Provide a short **justification** for the score.
    - If signs of distress (e.g., suicidal thoughts, extreme sadness) are detected, recommend seeking professional help.

    **Output Format Example:**
        {
            "score": 5,
            "explanation": "The user expresses a neutral tone with no strong emotions.",
            "recommendation": "Continue journaling to track emotional patterns."
        }

    Now, analyze the following journal entry and return the JSON response:
    """

    full_prompt = instruction + "\n" + prompt

    response = model.generate_content(full_prompt)
    # print("Raw response:", response)
    # Extract the text from Gemini's response
    if hasattr(response, "text"):
        response_text = response.text.strip()
    elif hasattr(response, "candidates") and response.candidates:
        response_text = response.candidates[0]["content"]["parts"][0]["text"].strip()
    else:
        return {"error": "Invalid AI response", "details": "No valid content found"}

    print("Extracted Response (Before Cleanup):", response_text)

    response_text = re.sub(r"```json\s*", "", response_text)  
    response_text = re.sub(r"\s*```", "", response_text)  

    # print("Cleaned Response ", response_text)

    try:
        json_response = json.loads(response_text)  # Convert to dictionary
        return json_response  # Return as dict, not string
    except json.JSONDecodeError as e:
        print("JSON Decoding Error:", str(e))
        return {"error": "Invalid AI response", "details": str(e)}


@app.route('/analyze', methods=['POST'])
def analyze_journal():
    data = request.json
    prompt = data.get("content", "")

    if not prompt:
        return jsonify({"error": "No content provided"}), 400

    analysis = get_journal_analysis(prompt)
    # print("Final Analysis Output Before JSON Response:", analysis)
    # print(type(analysis))

    try:
        if isinstance(analysis, dict):
            return jsonify(analysis) 
        analysis_json = json.loads(analysis)
        print(analysis_json)
        return jsonify(analysis_json)
    except Exception as e:
        return jsonify({"error": "Failed to process analysis", "details": str(e)}), 500

def get_mind_solution(prompt: str):
    model = genai.GenerativeModel("gemini-1.5-flash-002")
    #model = genai.GenerativeModel("imagen-3.0-generate-002")
    response = model.generate_content(prompt)
    return response.text.strip()

@app.route("/generate", methods=["POST"]) 
def generate_image():
    data = request.json
    user_input = data.get("text", "")

    if not user_input:
        response = make_response(jsonify({"error": "No input provided"}), 400)
        response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
        return response

    prompt = f"""
    The user is feeling "{user_input}".
    Transform this feeling into a **concise and vivid image prompt** for AI-generated art.
    - Use **colors** to represent the mood (e.g., dark blue for sadness, bright yellow for happiness).
    - Indicate the **paintstroke intensity** (e.g., soft and blended for calm, rough and bold for anger).
    - The image should depict a scene, do not generate any inappropriate content like nudity or violent scenes.
    Return only the modified prompt.
    """

    ai_prompt = get_mind_solution(prompt)

    # Generate image
    client = InferenceClient(api_key=hf_api_key)
    image = client.text_to_image(ai_prompt, model="stabilityai/stable-diffusion-xl-base-1.0")

    # Save image
    timestamp = int(time.time())
    image_path = f"static/generated_image_{timestamp}.png"
    image.save(image_path)

    return jsonify({"image_url": f"/{image_path}"})


def get_mood_analysis(prompt: str):
    model = genai.GenerativeModel("gemini-1.5-flash-002")

    instruction = """
    You are an expert in mental wellness. Given a list of question-answer pairs from a self-reflection mood assessment, analyze the content and provide 3 scores on a scale of 1 to 10:

    1. **Mental Health Score** – Reflects overall emotional well-being, positivity, stress level, signs of depression or anxiety.
    2. **Emotional Quotient (EQ) Score** – Measures the ability to recognize, manage, and express emotions, and handle interpersonal relationships.
    3. **Self-Awareness Score** – Indicates understanding of personal emotions, triggers, thoughts, and behavioral patterns.

    **Important:**
    - A **lower score (closer to 1)** indicates **better mental wellness** (more positive, stable, and self-aware).
    -A **higher score (closer to 10)** indicates **greater concerns** (more stress, emotional struggles, or low self-awareness).

    Return only a clean JSON object in this format:

    ```json
    {
    "mental_score": <integer between 1-10>,
    "eq_score": <integer between 1-10>,
    "self_awareness_score": <integer between 1-10>
    }"""

    print("Recieved prompt", prompt)
    full_prompt = instruction + "\n" + prompt

    response = model.generate_content(full_prompt)
    # print("Raw response:", response)
    # Extract the text from Gemini's response
    if hasattr(response, "text"):
        response_text = response.text.strip()
    elif hasattr(response, "candidates") and response.candidates:
        response_text = response.candidates[0]["content"]["parts"][0]["text"].strip()
    else:
        return {"error": "Invalid AI response", "details": "No valid content found"}

    print("Extracted Response (Before Cleanup):", response_text)

    response_text = re.sub(r"```json\s*", "", response_text)  
    response_text = re.sub(r"\s*```", "", response_text)  

    # print("Cleaned Response ", response_text)

    try:
        json_response = json.loads(response_text)  # Convert to dictionary
        return json_response  
    except json.JSONDecodeError as e:
        print("JSON Decoding Error:", str(e))
        return {"error": "Invalid AI response", "details": str(e)}
    

def get_report_analysis(prompt: str):
    model = genai.GenerativeModel("gemini-1.5-flash-002")

    instruction = """
    You are a mental wellness expert. Given the following scores:
    - `journal_score`: The mental health score from a journal entry (1-10).
    - `self_awareness_score`: The self-awareness score (1-10) from a self-reflection mood assessment.
    - `mental_score`: The overall mental health score (1-10) indicating emotional well-being.
    - `eq_score`: The emotional quotient (EQ) score (1-10) assessing emotional intelligence.
    - `quiz_score`: The total score from a mood and behavior-related quiz (1-10).

    **Evaluation Criteria:**
    - **Mental Health Score**: Reflects emotional well-being, positivity, stress levels, and signs of depression or anxiety.
      - **Instruction**: A score closer to 1 indicates better mental health, with fewer signs of stress, anxiety, or depression. A higher score closer to 10 suggests that the individual may be experiencing significant emotional distress or mental health challenges.
    
    - **Emotional Quotient (EQ) Score**: Assesses the ability to recognize, manage, and express emotions and handle interpersonal relationships.
      - **Instruction**: A lower score (closer to 1) indicates strong emotional intelligence, with the individual effectively managing their emotions and relationships. A higher score (closer to 10) suggests challenges in emotional regulation or interpersonal relationships.
    
    - **Self-Awareness Score**: Measures understanding of personal emotions, triggers, thoughts, and behavioral patterns.
      - **Instruction**: A lower score (closer to 1) indicates high self-awareness, with the individual having a good grasp of their emotions, thoughts, and behavior patterns. A higher score closer to 10 suggests low self-awareness and potential difficulty in recognizing personal triggers and emotional responses.

    - **Quiz Score**: Reflects the individual's emotional and behavioral assessment through a quiz.
      - **Instruction**: A lower score indicates fewer behavioral or emotional concerns, while a higher score could signify the presence of greater emotional or behavioral challenges, requiring attention and improvement.

    **Important Guidelines:**
    - A **lower score (closer to 1)** indicates **better mental wellness** (greater emotional stability, self-awareness, and less stress).
    - A **higher score (closer to 10)** signals **greater concerns** (more emotional struggles, anxiety, or lack of self-awareness).

    **Critical Instruction:**
    - Do not suggest generic advice such as exploring cognitive behavioral therapy (CBT), maintaining a healthy lifestyle, seeking professional help, or general emotional regulation strategies **unless the scores are extremely high (8-10) indicating severe concerns**.
    - Focus the analysis and recommendations only on what is inferred from the actual provided scores.
    
    Based on the provided scores, please generate a single comprehensive analysis. The analysis should:
    - Provide an overview of the individual’s mental wellness by integrating all the scores (Mental Health, EQ, Self-Awareness, and Quiz Score).
    - Discuss the implications of each score in relation to the individual’s emotional well-being, emotional intelligence, and self-awareness.
    - Offer **actionable recommendations** to improve mental wellness, including suggestions for enhancing emotional intelligence, managing stress, and fostering better self-awareness.

    **Note**: The analysis should be a cohesive, empathetic evaluation that provides both insights and practical steps for improvement.

    Return only a clean JSON object in the following format:

    ```json
    {
      "analysis": "<Common analysis paragraph covering all scores and recommendations>"
    }
    """

    print("Recieved prompt", prompt)
    if isinstance(prompt, dict):
        prompt = json.dumps(prompt, indent=2)
    full_prompt = instruction + "\n" + prompt

    response = model.generate_content(full_prompt)
    # print("Raw response:", response)
    # Extract the text from Gemini's response
    if hasattr(response, "text"):
        response_text = response.text.strip()
    elif hasattr(response, "candidates") and response.candidates:
        response_text = response.candidates[0]["content"]["parts"][0]["text"].strip()
    else:
        return {"error": "Invalid AI response", "details": "No valid content found"}

    print("Extracted Response (Before Cleanup):", response_text)

    response_text = re.sub(r"```json\s*", "", response_text)  
    response_text = re.sub(r"\s*```", "", response_text)  

    # print("Cleaned Response ", response_text)

    try:
        json_response = json.loads(response_text)  # Convert to dictionary
        return json_response  
    except json.JSONDecodeError as e:
        print("JSON Decoding Error:", str(e))
        return {"error": "Invalid AI response", "details": str(e)}

@app.route('/analyze_mood', methods=['POST'])
def analyze_mood():
    data = request.json
    prompt = data.get("content", "")

    if not prompt:
        return jsonify({"error": "No content provided"}), 400

    analysis = get_mood_analysis(prompt)

    try:
        if isinstance(analysis, dict):
            return jsonify(analysis) 
        analysis_json = json.loads(analysis)
        print(analysis_json)
        return jsonify(analysis_json)
    except Exception as e:
        return jsonify({"error": "Failed to process analysis", "details": str(e)}), 500


@app.route('/analyze_report', methods=['POST'])
def analyze_report():
    data = request.json
    prompt = data.get("content", "")

    if not prompt:
        return jsonify({"error": "No content provided"}), 400

    analysis = get_report_analysis(prompt)

    try:
        if isinstance(analysis, dict):
            return jsonify(analysis) 
        analysis_json = json.loads(analysis)
        print(analysis_json)
        return jsonify(analysis_json)
    except Exception as e:
        return jsonify({"error": "Failed to process analysis", "details": str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True,port=3002)
