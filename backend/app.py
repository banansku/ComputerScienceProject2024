from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import assemblyai as aai
import openai
import requests
import time
import yt_dlp
import os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Set your API keys here
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")
openai.api_key = os.getenv("openai.api_key")
test_url = os.getenv("test_url")

@app.before_request
def log_request_info():
    print("\n--- New Request ---")
    print("Method:", request.method)
    print("URL:", request.url)
    print("Headers:", request.headers)
    print("Body:", request.get_data(as_text=True))

# API Endpoint 1: Upload Video for Transcription
@app.route('/api/upload', methods=['POST'])
def upload_video():
    video_url = request.json.get('video_url')

    print(video_url)

    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(video_url, download=False)

    for format in info["formats"][::-1]:
        if format["resolution"] == "audio only" and format["ext"] == "m4a":
            url = format["url"]
            print(url)
            break

    if not video_url:
        return jsonify({"error": "Video URL is required"}), 400

    '''headers = {'authorization': ASSEMBLY_API_KEY}
    data = {'audio_url': video_url}'''

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(url)
    print(transcript.text)

    return jsonify({"transcription": transcript.text})

    '''try:
        response = requests.post('https://api.assemblyai.com/v2/transcript', json=data, headers=headers)
        return jsonify({"response": response})
        response_data = response.json()
        transcription_id = response_data['id']
        return jsonify({"transcription_id": transcript})
    except Exception as e:
        return jsonify({"error": str(e)}), 500'''

@socketio.on('track_transcription')
def track_transcription(data):
    transcription_id = data.get('transcription_id')
    if not transcription_id:
        emit('error', {"error": "Transcription ID is required"})
        return

    headers = {'authorization': assembly_api_key}
    url = f'https://api.assemblyai.com/v2/transcript/{transcription_id}'

    try:
        # Poll until transcription is completed, sending progress updates
        while True:
            response = requests.get(url, headers=headers)
            response_data = response.json()

            status = response_data.get('status')
            if status == 'completed':
                transcription_text = response_data.get('text', '')
                emit('transcription_completed', {"transcription_text": transcription_text})
                break
            elif status == 'failed':
                emit('error', {"error": "Transcription failed"})
                break
            else:
                # Emit the status update to the frontend
                emit('status_update', {"status": status})
                print(status)
                time.sleep(2)  # Wait 2 seconds before checking again
    except Exception as e:
        emit('error', {"error": str(e)})

# API Endpoint 2: Retrieve Transcription
@app.route('/api/get-transcription/<transcription_id>', methods=['GET'])
def get_transcription(transcription_id):
    headers = {'authorization': ASSEMBLYAI_API_KEY}
    url = f'https://api.assemblyai.com/v2/transcript/{transcription_id}'

    try:
        # Poll until transcription is completed
        while True:
            response = requests.get(url, headers=headers)
            response_data = response.json()

            status = response_data.get('status')
            if status == 'completed':
                transcription_text = response_data.get('text', '')
                return jsonify({"transcription_text": transcription_text})
            elif status == 'failed':
                return jsonify({"error": "Transcription failed"}), 500
            else:
                time.sleep(2)  # Wait 2 seconds before checking again
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API Endpoint 3: Summarize Transcription with ChatGPT
@app.route('/api/summarize-transcription', methods=['POST'])
def summarize_transcription():
    transcription_text = request.json.get('transcription_text')

    if not transcription_text:
        return jsonify({"error": "Transcription text is required"}), 400

    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Summarize the following text:\n\n{transcription_text}",
            max_tokens=100
        )
        summary = response.choices[0].text.strip()
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Main entry point to run the Flask app
if __name__ == '__main__':
    app.run(debug=True)