from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import assemblyai as aai
import openai
from openai import OpenAI
import requests
import time
import yt_dlp
import os
import re
from dotenv import load_dotenv

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
CORS(app)

# Set API keys here
load_dotenv()
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")
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

    ydl_opts = {
        'format': 'm4a/bestaudio/best',  # The best audio version in m4a format
        'outtmpl': '%(id)s.%(ext)s',  # The output name should be the id followed by the extension
        'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
        }],
        'progress_hooks': [lambda d: set_downloaded_file_path(d)]
    }

    def set_downloaded_file_path(d):
        global downloaded_file_path
        if d['status'] == 'finished':
            downloaded_file_path = d['filename']

    socketio.emit('message', {"text": "Getting video"})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        error_code = ydl.download(video_url)

    print(downloaded_file_path)

    if not video_url:
        return jsonify({"error": "Video URL is required"}), 400

    socketio.emit('message', {"text": "Transcribing video"})

    transcriber = aai.Transcriber()
    transcript = transcriber.transcribe(downloaded_file_path)
    print(transcript.text)

    try:
        os.remove(downloaded_file_path)
        print("video deleted from local")
    except FileNotFoundError:
        print("File not found")
    except PermissionError:
        print("You do not have permission to delete this file")
    except Exception as e:
        print(f"An error occurred: {e}")

    socketio.emit('message', {"text": "Summarizing transcript"})

    try:
        final_summary, chunk_summaries = summarize_transcription(transcript.text)
        socketio.emit('message', {"text": final_summary})
        socketio.emit('message', {"text": "If you have further questions, I can answer them."})
        
        return jsonify({"summary": final_summary, "chunk_summaries": chunk_summaries})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

def split_text(text, max_length=2000):
    print("splitting")
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > max_length:
            chunks.append(current_chunk.strip())
            current_chunk = sentence
        else:
            current_chunk += " " + sentence
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def summarize_chunk(chunk):
    print("summarizing")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Summarize this: {chunk}"}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content
def summarize_transcription(text):
    print("summarizing transcription")
    chunks = split_text(text)
    chunk_summaries = [summarize_chunk(chunk) for chunk in chunks]
    
    combined_summary_text = " ".join(chunk_summaries)
    
    # Summarize the combined summaries to get the final overview
    final_summary_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Summarize this overall content: {combined_summary_text}"}
        ]
    )
    
    final_summary = final_summary_response.choices[0].message.content
    return final_summary, chunk_summaries

def answer_question(summary, chunk_summaries, question):
    # Start with the overall summary as context
    chat_history = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Here is a summary of the video transcription: {summary}"},
        {"role": "user", "content": question}
    ]
    
    # Get a response based on the overall summary
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=chat_history,
        max_tokens=200
    )
    
    answer = response.choices[0].message.content
    
    # If the answer seems incomplete, look at chunk summaries for more detail
    if "I don't have enough information" in answer or len(answer) < 50:
        for chunk_summary in chunk_summaries:
            chat_history.append({"role": "user", "content": f"Additional context: {chunk_summary}"})
            chat_history.append({"role": "user", "content": question})
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=chat_history,
                max_tokens=200
            )
            answer = response.choices[0].message.content
            
            if len(answer) > 50:  # Assuming a longer answer indicates it was able to answer
                break
    
    return answer

#@socketio.on('track_transcription')
#def track_transcription(data):
#    transcription_id = data.get('transcription_id')
#    if not transcription_id:
#        emit('error', {"error": "Transcription ID is required"})
#        return
#
#    headers = {'authorization': assembly_api_key}
#    url = f'https://api.assemblyai.com/v2/transcript/{transcription_id}'
#
#    try:
#        # Poll until transcription is completed, sending progress updates
#        while True:
#            response = requests.get(url, headers=headers)
#            response_data = response.json()
#
#            status = response_data.get('status')
#            if status == 'completed':
#                transcription_text = response_data.get('text', '')
#                emit('transcription_completed', {"transcription_text": transcription_text})
#                break
#            elif status == 'failed':
#                emit('error', {"error": "Transcription failed"})
#                break
#            else:
#                # Emit the status update to the frontend
#                emit('status_update', {"status": status})
#                print(status)
#                time.sleep(2)  # Wait 2 seconds before checking again
#    except Exception as e:
#        emit('error', {"error": str(e)})
#
## API Endpoint 2: Retrieve Transcription
#@app.route('/api/get-transcription/<transcription_id>', methods=['GET'])
#def get_transcription(transcription_id):
#    headers = {'authorization': ASSEMBLYAI_API_KEY}
#    url = f'https://api.assemblyai.com/v2/transcript/{transcription_id}'
#
#    try:
#        # Poll until transcription is completed
#        while True:
#            response = requests.get(url, headers=headers)
#            response_data = response.json()
#
#            status = response_data.get('status')
#            if status == 'completed':
#                transcription_text = response_data.get('text', '')
#                return jsonify({"transcription_text": transcription_text})
#            elif status == 'failed':
#                return jsonify({"error": "Transcription failed"}), 500
#            else:
#                time.sleep(2)  # Wait 2 seconds before checking again
#    except Exception as e:
#        return jsonify({"error": str(e)}), 500
#
## API Endpoint 3: Summarize Transcription with ChatGPT
#@app.route('/api/summarize-transcription', methods=['POST'])
#def summarize_transcription():
#    transcription_text = request.json.get('transcription_text')
#
#    if not transcription_text:
#        return jsonify({"error": "Transcription text is required"}), 400
#
#    try:
#        response = openai.Completion.create(
#            engine="text-davinci-003",
#            prompt=f"Summarize the following text:\n\n{transcription_text}",
#            max_tokens=100
#        )
#        summary = response.choices[0].text.strip()
#        return jsonify({"summary": summary})
#    except Exception as e:
#        return jsonify({"error": str(e)}), 500

def summarize_chunk(chunk):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text."},
            {"role": "user", "content": f"Summarize this: {chunk}"}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content


# Main entry point to run the Flask app
if __name__ == '__main__':
    app.run(debug=True)