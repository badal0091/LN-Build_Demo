import os
from flask import Flask, render_template, request, jsonify, send_file
from difflib import SequenceMatcher
from werkzeug.utils import secure_filename
import json
import requests  # Make sure you import requests
from openai import OpenAI
app = Flask(__name__)

# jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJhZ2hhdi5zaW5naEBzdHJhaXZlLmNvbSJ9.JvB8HqvJZs6M1JG9rkLyJTjAxQDluJTrLP5JZ7GRtqM:chatAssisit"
UPLOAD_FOLDER = 'temp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize OpenAI client
my_key = os.getenv('OPENAI_API_KEY', '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')
# my_model = 'ft:gpt-4o-mini-2024-07-18:withxl-data-solutions::A8KuO0AS'
my_model = 'ft:gpt-4o-mini-2024-07-18:personal::A8Rsdd8e'
client = OpenAI(api_key=my_key)


# Function to process XML using OpenAI
def process_xml(input_file_path):
    try:
        with open(input_file_path, 'r', encoding='utf-8') as file:
            xml_content = file.read()

        # OpenAI call to process the XML content
        completion = client.chat.completions.create(
            model=my_model,
            messages=[
                {"role": "system", "content": "Convert the following XML to LN XML feed"},
                {"role": "user", "content": xml_content}
            ]
        )

        # Write the processed XML content to output.xml.out
        processed_xml = completion.choices[0].message.content
        with open('output.xml.out', 'w', encoding='latin-1') as f:
            f.write(processed_xml)

        # Return the processed content to be read by the frontend
        return processed_xml

    except Exception as e:
        raise Exception(f"Error processing XML with OpenAI: {str(e)}")


@app.route('/download-ai-output')
def download_ai_output():
    try:
        file_path = 'output.xml.out'
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
        
        return send_file(file_path, as_attachment=True, download_name='output.xml.out')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Route to display the HTML page
@app.route('/')
def display():
    return render_template('display.html')

# Route to handle XML processing
@app.route('/process-xml', methods=['POST'])
def process_xml_route():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    filename = secure_filename(file.filename)
    temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(temp_file_path)
        
        # Process the XML file and get the result
        process_xml(temp_file_path)

        # Read the content of output.xml.out file to display it in the frontend
        with open('output.xml.out', 'r', encoding='latin-1') as file:
            content = file.read()

        # Return the file content as JSON response
        return jsonify({"content": content})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Cleanup: remove the file after processing
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)




# Route to handle BA prompt and update XML
@app.route('/process-ba-prompt', methods=['POST'])
def process_ba_prompt_route():
    try:
        if not os.path.exists('output.xml.out'):
            return jsonify({"error": "No output.xml.out file found"}), 400

        # Read the content of output.xml.out
        with open('output.xml.out', 'r', encoding='latin-1') as file:
            xml_content = file.read()

        data = request.json
        prompt1 = data.get('prompt')  # Ensure this is coming from the BA input in frontend
        if not prompt1:
            return jsonify({"error": "No BA prompt provided"}), 400

        # Call the external API with the BA prompt and XML content
        proxy_url = "https://llmfoundry.straive.com/anthropic/v1/messages"
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InJhZ2hhdi5zaW5naEBzdHJhaXZlLmNvbSJ9.JvB8HqvJZs6M1JG9rkLyJTjAxQDluJTrLP5JZ7GRtqM:chatAssisit"
        model = "claude-3-haiku-20240307"

        response = requests.post(proxy_url, json={
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": xml_content}],
            "system": prompt1
        }, headers={"Authorization": f"Bearer {jwt_token}"})

        if response.status_code == 200:
            response_data = response.json()
            content_list = response_data.get('content')
            if isinstance(content_list, list):
                xml_part = ''.join([item['text'] for item in content_list if item['type'] == 'text'])

                # Write the updated XML content to a file
                with open('updated_output.xml.out', 'w', encoding='latin-1') as f:
                    f.write(xml_part)

                return jsonify({"content": xml_part})
            else:
                return jsonify({"error": "Unexpected response format"}), 500
        else:
            error_message = response.text  # Get the response content for debugging
            return jsonify({"error": f"Failed to get response from external service: {error_message}"}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)