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





from pydub import AudioSegment
# Download the audio file as before
def download_video_as_audio(url: str, audio_format: str = 'mp3'):
    home_directory = os.path.expanduser("~")
    output_path = os.path.join(home_directory, '%(title)s.%(ext)s')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': audio_format,
        'outtmpl': output_path,
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audio_format,
            'preferredquality': '192',
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(result).replace('.webm', f'.{audio_format}')

    return filename

# Split audio into 30-second segments
def split_audio(file_path: str, segment_length: int = 30):
    audio = AudioSegment.from_file(file_path)
    duration = len(audio)

    base_directory = os.path.dirname(file_path)
    file_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.join(base_directory, file_name + "_segments")
    os.makedirs(output_dir, exist_ok=True)

    segment_files = []
    for i in range(0, duration, segment_length * 1000):
        segment = audio[i:i + segment_length * 1000]
        segment_file = os.path.join(output_dir, f"{file_name}_part_{i // 1000 // segment_length + 1}.mp3")
        segment.export(segment_file, format="mp3")
        segment_files.append(segment_file)
    
    return segment_files

# Upload file to AssemblyAI
def upload_file_to_assemblyai(file_path: str):
    headers = {'authorization': ASSEMBLYAI_API_KEY}
    with open(file_path, 'rb') as f:
        response = requests.post('https://api.assemblyai.com/v2/upload', headers=headers, files={'file': f})
    response.raise_for_status()
    return response.json()['upload_url']

# Request transcription for each uploaded file
def request_transcription(upload_url: str):
    endpoint = "https://api.assemblyai.com/v2/transcript"
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
        "content-type": "application/json"
    }
    response = requests.post(endpoint, json={"audio_url": upload_url}, headers=headers)
    response.raise_for_status()
    return response.json()['id']  # Return transcript ID to track status

# Track transcription status and retrieve results
def get_transcription_result(transcript_id: str):
    endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    headers = {"authorization": ASSEMBLYAI_API_KEY}
    while True:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data['status'] == 'completed':
            return data['text']  # Return the transcription text
        elif data['status'] == 'failed':
            raise Exception(f"Transcription failed for ID {transcript_id}")
        # Wait a moment before polling again
        time.sleep(5)

# Full process
def process_video_to_transcriptions(video_url: str):
    transcripts = []
    socketio.emit('message', {"text": "getting video"})
    audio_file = download_video_as_audio(video_url, audio_format='mp3')
    socketio.emit('message', {"text": "parsing video"})
    segment_files = split_audio(audio_file, segment_length=30)
    
    socketio.emit('message', {"text": "transcribing video"})
    for segment_file in segment_files:
        try:
            print(f"Uploading {segment_file}...")
            upload_url = upload_file_to_assemblyai(segment_file)
            print(f"Requesting transcription for {segment_file}...")
            transcript_id = request_transcription(upload_url)
            print(f"Waiting for transcription of {segment_file}...")
            transcript_text = get_transcription_result(transcript_id)
            transcripts.append(transcript_text)
            print(f"Transcription for {segment_file}:\n{transcript_text}\n")
        except Exception as e:
            print(f"Error processing {segment_file}: {e}")


# API Endpoint 1: Upload Video for Transcription
@app.route('/api/uploadtest', methods=['POST'])
def upload_video():
    video_url = request.json.get('video_url')
    print(video_url)
    socketio.emit('message', {"text": "getting video"})
    process_video_to_transcriptions(video_url)


    return jsonify({"success": "success"}, 200)



# Main entry point to run the Flask app
if __name__ == '__main__':
    app.run(debug=True)