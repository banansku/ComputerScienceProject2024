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
    global video_title
    global video_uploader

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

    socketio.emit('message', {"text": "Getting video"})

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        error_code = ydl.download(video_url)
        info = ydl.extract_info(video_url, download=False)
        video_title = info.get('title')
        video_uploader = info.get('uploader')

    print(downloaded_file_path)
    print(video_title)
    print(video_uploader)

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

@app.route('/api/ask_question', methods=['POST'])
def ask_question():
    question = request.json.get('question')
    summary = final_summary
    summaries = chunk_summaries
    if not summary or not question:
        return jsonify({"error": "Summary or question not provided"}), 400
    try:
        answer = answer_question(summary, summaries, question)
        socketio.emit('message', {"text": answer.replace("\n", "\\n")})
        return jsonify({"answer": "200 OK"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def set_downloaded_file_path(d):
    global downloaded_file_path
    if d['status'] == 'finished':
        downloaded_file_path = d['filename']   

def split_text(text, max_length=10000):
    print("splitting")
    global chunks
    global current_chunk
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
            {"role": "system", "content": "You are a helpful assistant that summarizes youtube video transcriptions. You do not use markdown format."},
            {"role": "user", "content": f"Summarize this: {chunk}. For context, the video title is {video_title} and the uploader is {video_uploader}"}
        ],
        max_tokens=200
    )
    return response.choices[0].message.content

def summarize_transcription(text):
    print("summarizing transcription")
    global chunk_summaries
    global final_summary
    chunks = split_text(text)
    chunk_summaries = [summarize_chunk(chunk) for chunk in chunks]
    
    combined_summary_text = " ".join(chunk_summaries)
    
    # Summarize the combined summaries to get the final overview
    final_summary_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes youtube video transcriptions. You do not use markdown format."},
            {"role": "user", "content": f"Summarize this overall content: {combined_summary_text}"}
        ]
    )
    
    final_summary = final_summary_response.choices[0].message.content
    return final_summary.replace("\n", "\\n"), chunk_summaries

def answer_question(summary, chunk_summaries, question):
    
    chat_history = [
        {"role": "system", "content": "You are a helpful assistant that summarizes youtube video transcriptions. You do not use markdown format."},
        {"role": "system", "content": f"Here is what you know about the video: {chunks}. " 
                                    + f"The video title is {video_title}, " 
                                    + f"and the uploader of the video is {video_uploader}. " 
                                    + "If you don't know something, say 'I don't know'."},
        {"role": "user", "content": question}
        ]
        
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=chat_history
    )
    answer = response.choices[0].message.content
    print(answer.replace("\n", "\\n"))
    
    return answer.replace("\n", "\\n")

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