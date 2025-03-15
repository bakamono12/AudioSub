# app.py
from flask import Flask, request, jsonify, render_template, send_file
import os
import uuid
import logging
import socket
import threading

# Import the task definitions directly
from celery_worker import process_media, translate_subtitles

# Configure logging
logging.basicConfig(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['RESULTS_FOLDER'] = 'results/'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg'}
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max upload size

# In-memory status tracker
processing_status = {}

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


@app.route('/')
def index():
    _logger.info(f"Request from: {socket.gethostname()}")
    return render_template('index.html')


def process_file_background(filepath, file_id, language=''):
    """Process file in background and update status"""
    try:
        # Update status to processing
        processing_status[file_id] = {
            'status': 'Processing audio extraction',
            'progress': 10,
            'state': 'PROCESSING'
        }

        if filepath.endswith(('.mp4', '.avi', '.mov')):
            processing_status[file_id]['status'] = 'Extracting audio from video file'
            processing_status[file_id]['progress'] = 20

        # When transcription begins
        processing_status[file_id]['status'] = 'Transcribing audio'
        processing_status[file_id]['progress'] = 40
        
        # Process the media file
        result = process_media(filepath, file_id, language) if language else process_media(filepath, file_id)
        
        # Update status to complete
        processing_status[file_id] = {
            'status': 'Completed',
            'progress': 100,
            'state': 'SUCCESS',
            'result': result
        }
    except Exception as e:
        _logger.error(f"Error processing file: {str(e)}")
        processing_status[file_id] = {
            'status': f'Error: {str(e)}',
            'progress': 0,
            'state': 'FAILURE'
        }


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    allowed_file_format_list =['mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg','webm','mkv','mpeg']

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    else:
        unique_id = str(uuid.uuid4())
        original_extension = file.filename.rsplit('.', 1)[1].lower()
        if original_extension not in allowed_file_format_list:
            return jsonify({'error': 'File type not allowed'}), 400
        secure_name = f"{unique_id}.{original_extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_name)

        file.save(filepath)
        _logger.info(f"File uploaded: {filepath}")
        
        # Initialize status for this file
        processing_status[unique_id] = {
            'status': 'File uploaded, starting processing',
            'progress': 5,
            'state': 'PROCESSING'
        }
        
        # Start processing in a background thread
        language = request.form.get('language', '')
        thread = threading.Thread(target=process_file_background, args=(filepath, unique_id, language))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': 'File uploaded successfully and processing started',
            'file_id': unique_id,
            'state': 'PROCESSING'
        })


@app.route('/status/<file_id>', methods=['GET'])
def get_status(file_id):
    """Get the current status of a processing file"""
    if file_id in processing_status:
        return jsonify(processing_status[file_id])
    return jsonify({
        'status': 'Not found',
        'state': 'FAILURE',
        'progress': 0
    }), 404


@app.route('/download/<file_id>')
def download_subtitle(file_id):
    srt_path = os.path.join(app.config['RESULTS_FOLDER'], f"{file_id}.srt")
    if os.path.exists(srt_path):
        return send_file(srt_path, as_attachment=True, download_name="subtitles.srt")
    else:
        return jsonify({'error': 'Subtitle file not found'}), 404


@app.route('/translate', methods=['POST'])
def translate():
    """Translate subtitles to a target language"""
    data = request.json
    file_id = data.get('file_id')
    target_language = data.get('target_language')
    
    if not file_id or not target_language:
        return jsonify({'error': 'Missing parameters'}), 400
        
    translation_id = f"{file_id}_{target_language}"
    processing_status[translation_id] = {
        'status': 'Starting translation',
        'progress': 10,
        'state': 'PROCESSING'
    }
    
    # Start translation in background thread
    def do_translation():
        try:
            processing_status[translation_id]['status'] = 'Translating subtitles'
            processing_status[translation_id]['progress'] = 50
            result = translate_subtitles(file_id, target_language)
            processing_status[translation_id] = {
                'status': 'Translation complete',
                'progress': 100,
                'state': 'SUCCESS',
                'result': result
            }
        except Exception as e:
            _logger.error(f"Error translating subtitles: {str(e)}")
            processing_status[translation_id] = {
                'status': f'Error: {str(e)}',
                'progress': 0,
                'state': 'FAILURE'
            }
    
    thread = threading.Thread(target=do_translation)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'message': 'Translation started',
        'translation_id': translation_id,
        'state': 'PROCESSING'
    })


if __name__ == '__main__':
    # Display important startup information
    _logger.info("=" * 50)
    _logger.info("APPLICATION STARTING")
    _logger.info(f"Upload folder: {os.path.abspath(app.config['UPLOAD_FOLDER'])}")
    _logger.info(f"Results folder: {os.path.abspath(app.config['RESULTS_FOLDER'])}")
    _logger.info("=" * 50)
    app.run(debug=True, use_reloader=False)
