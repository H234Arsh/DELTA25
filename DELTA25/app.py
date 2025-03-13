import os
# Set FFmpeg environment variables BEFORE importing any modules that depend on them.
os.environ["FFMPEG_BINARY"] = r"C:\Users\Pc\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe"
os.environ["FFPROBE_BINARY"] = r"C:\Users\Pc\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe"
os.environ["PATH"] += os.pathsep + r"C:\Users\Pc\Downloads\ffmpeg-master-latest-win64-gpl\ffmpeg-master-latest-win64-gpl\bin"

from flask import Flask, render_template, request, jsonify, send_file
import uuid
import boto3
import google.generativeai as genai
import cv2
import numpy as np
from PIL import Image
import io
from werkzeug.utils import secure_filename
import glob
import random
from pydub import AudioSegment

# Optionally, explicitly set the AudioSegment paths (redundant if env variables are set)
AudioSegment.converter = os.environ["FFMPEG_BINARY"]
AudioSegment.ffprobe = os.environ["FFPROBE_BINARY"]

app = Flask(__name__)

# Create necessary directories
os.makedirs('uploads', exist_ok=True)
music_dir = r'C:\Users\Pc\OneDrive\Desktop\Directory\College - CCE\Competitions\Delta\The Folder\Musics'
os.makedirs(music_dir, exist_ok=True)

# Configure API keys (for production, consider loading these from environment variables)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCVYGVvDKV5bg6Hd2TtrSEIbx0g6hTYnpI")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY", "AKIA4VDBMBKDQAICBAMW")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY", "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")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize AWS Polly
polly = boto3.client(
    "polly",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/process-image', methods=['POST'])
def process_image():
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file provided'})
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    # Save uploaded image
    filename = str(uuid.uuid4()) + '.jpg'
    filepath = os.path.join('uploads', filename)
    file.save(filepath)
    
    try:
        # Process image using OpenCV
        original_image = cv2.imread(filepath)
        gray = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)
        binarized = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        denoised = cv2.medianBlur(binarized, 3)
        
        # Convert processed image to bytes for further API usage
        processed_pil = Image.fromarray(denoised)
        buffered = io.BytesIO()
        processed_pil.save(buffered, format="JPEG")
        img_bytes = buffered.getvalue()
        
        return jsonify({
            'success': True, 
            'imageId': filename, 
            'message': 'Image processed successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/generate-audio', methods=['POST'])
def generate_audio():
    data = request.json
    image_id = data.get('imageId')
    voice = data.get('voice', 'Matthew')
    add_background_music = data.get('addBackgroundMusic', True)
    
    if not image_id:
        return jsonify({'success': False, 'message': 'No image ID provided'})
    
    try:
        # Retrieve the processed image
        filepath = os.path.join('uploads', image_id)
        with open(filepath, 'rb') as img_file:
            img_bytes = img_file.read()
        
        # Gemini prompt
        prompt = (
            "You are a cutting-edge text extraction and summarization engine armed with a battle-hardened, strategic mindset. "
            "I will supply you with an image containing a critical news article. Your mission is to first extract every detail of the text from the image with flawless precision, preserving line breaks, punctuation, and spacing exactly as they appear. "
            "Then, distill the core intelligence into a concise, razor-sharp summary that captures the essence of the news. "
            "Following that, craft a powerful, galvanizing military dispatch that amplifies the summary and ignites unyielding determination, valor, and strategic resolve—much like rallying an elite strike force on the frontline. "
            "The final output must be a single, coherent paragraph that seamlessly fuses the succinct news summary with the resolute, high-octane military dialogue. "
            "Do not include the full extracted text, and avoid any extraneous formatting characters such as numbers or asterisks; only use plain characters, punctuation, and spaces."
        )
        
        # Call Gemini API
        model = genai.GenerativeModel('gemini-1.5-flash')
        contents = [
            {
                "parts": [
                    prompt,
                    {"mime_type": "image/jpeg", "data": img_bytes},
                ]
            },
        ]
        response = model.generate_content(contents)
        extracted_text = response.text  # Save extracted text for display
        
        # Generate audio with AWS Polly using the extracted text
        polly_response = polly.synthesize_speech(
            Engine="neural",
            LanguageCode="en-US",
            VoiceId=voice,
            OutputFormat="mp3",
            Text=extracted_text
        )
        
        # Save raw audio file
        raw_audio_filename = f"{image_id.split('.')[0]}_raw.mp3"
        raw_audio_path = os.path.join('uploads', raw_audio_filename)
        with open(raw_audio_path, "wb") as file:
            file.write(polly_response["AudioStream"].read())
        
        # Define final audio file path
        audio_filename = f"{image_id.split('.')[0]}.mp3"
        audio_path = os.path.join('uploads', audio_filename)
        
        # Add background music if requested
        if add_background_music:
            bg_files = glob.glob(os.path.join(music_dir, "*.mp3"))
            if bg_files:
                selected_bg = random.choice(bg_files)
                speech = AudioSegment.from_mp3(raw_audio_path)
                background = AudioSegment.from_mp3(selected_bg)
                
                # Lower the background music volume by 21 dB
                background = background - 21
                
                # Adjust frame rate if necessary
                if speech.frame_rate != background.frame_rate:
                    background = background.set_frame_rate(speech.frame_rate)
                
                # Extend and trim background to match speech duration
                if len(background) < len(speech):
                    background = background * (len(speech) // len(background) + 1)
                background = background[:len(speech)]
                
                # Overlay background music onto the speech
                combined = speech.overlay(background, position=0)
                combined.export(audio_path, format="mp3")
            else:
                os.rename(raw_audio_path, audio_path)
        else:
            os.rename(raw_audio_path, audio_path)
        
        return jsonify({
            'success': True,
            'audioUrl': f'/api/audio/{audio_filename}',
            'extractedText': extracted_text,
            'message': 'Audio generated successfully with background music' if add_background_music else 'Audio generated successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/api/audio/<filename>')
def serve_audio(filename):
    return send_file(os.path.join('uploads', filename), mimetype='audio/mpeg')

@app.route('/api/upload-background-music', methods=['POST'])
def upload_background_music():
    if 'music' not in request.files:
        return jsonify({'success': False, 'message': 'No music file provided'})
    
    file = request.files['music']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})
    
    filename = secure_filename(file.filename)
    if not filename.endswith('.mp3'):
        filename += '.mp3'
    
    filepath = os.path.join(music_dir, filename)
    file.save(filepath)
    
    return jsonify({
        'success': True,
        'message': 'Background music uploaded successfully'
    })

@app.route('/api/list-background-music', methods=['GET'])
def list_background_music():
    bg_files = glob.glob(os.path.join(music_dir, "*.mp3"))
    music_list = [os.path.basename(file) for file in bg_files]
    
    return jsonify({
        'success': True,
        'music_files': music_list
    })

if __name__ == '__main__':
    app.run(debug=True)
