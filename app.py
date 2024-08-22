import logging
import google.generativeai as genai
from docx import Document
import pdfplumber
import random
from google.generativeai.types import GenerationConfig
from flask import Flask, request, jsonify
import json

# Initialize Flask app
app = Flask(__name__)

# Set up Google Generative AI with multiple API keys
api_list = [
    "AIzaSyA51WTz0t69sBFs8D2ZmLLypKs6X9rIcEI",
    "AIzaSyDlCk6V9XXwHEYJSjSC4-g28N69UgNcVYA"
]
api_key = random.choice(api_list)
print(f"Using API Key: {api_key}")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_text_from_docx(file):
    """
    Extract text from a DOCX file.
    """
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_text_from_pdf(file):
    """
    Extract text from a PDF file.
    """
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def get_gemini_response(model, input_text, prompt):
    """
    Generate a response from the Gemini model using the provided prompt and input text.
    """
    try:
        full_prompt = f"{prompt}\n\nJob Description:\n{input_text}"
        response = model.generate_content(
            [full_prompt],
            generation_config=GenerationConfig(
                temperature=0.4
            )
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating Gemini response: {e}")
        return None

@app.route('/extract', methods=['POST'])
def extract_information():
    """
    API endpoint to process the job description file and extract structured information.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not (file.filename.endswith('.pdf') or file.filename.endswith('.docx')):
        return jsonify({"error": "Unsupported file format"}), 400

    # Determine file type and extract text
    if file.filename.endswith('.pdf'):
        text = extract_text_from_pdf(file)
    elif file.filename.endswith('.docx'):
        text = extract_text_from_docx(file)

    # Define the prompt for extraction
    prompt = """
    Extract the following information from the job description and format it as JSON:
    - Title
    - Company Name
    - Hide Company (keep false)
    - Qualification
    - Job Type
    - Workplace Type
    - Experience (provide as an object with min and max values)
    - Currency ( INR (₹))
    - Salary (provide as an object with min and max values)
    - Hide Salary (keep false)
    - Hiring For
    - Description
    - Industries (provide as a list of strings)
    - Skills (provide as a list of strings)
    - Location (provide as a list of strings)

    Provide the information in the following key-value format:
    {
        "title": "",
        "company": "",
        "hideCompany": "",
        "qualification": "",
        "jobType": "",
        "workplaceType": "",
        "experience": {
            "min": "",
            "max": ""
        },
        "currency": "",
        "salary": {
            "min": "",
            "max": ""
        },
        "hideSalary": "",
        "hiringFor": "",
        "description": "",
        "industries": [""],
        "skills": [""],
        "location": [""]
    }
    """

    # Get the response from the Gemini model
    response = get_gemini_response(model, text, prompt)
    if response:
        try:
            # Remove any extra formatting or markdown if present
            clean_response = response.strip().strip('```json').strip('```')
            # Parse the cleaned response as JSON
            parsed_response = json.loads(clean_response)
            return jsonify({"data": parsed_response})
        except json.JSONDecodeError:
            logging.error("Error decoding JSON from response")
            return jsonify({"error": "Invalid JSON response"}), 500
        except Exception as e:
            logging.error(f"Error processing response: {e}")
            return jsonify({"error": "Response processing error"}), 500
    else:
        return jsonify({"error": "Failed to generate response."}), 500

if __name__ == '__main__':
    app.run(debug=True)
