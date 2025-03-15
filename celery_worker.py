import os
import subprocess
import whisper
import json
import logging

_logger = logging.getLogger(__name__)


def format_time(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"


def create_srt(segments):
    """Create SRT file content from segments"""
    srt_content = ""
    for i, segment in enumerate(segments, 1):
        start_time = format_time(segment['start'])
        end_time = format_time(segment['end'])
        text = segment['text'].strip()
        srt_content += f"{i}\n{start_time} --> {end_time}\n{text}\n\n"
    return srt_content


def process_media(filepath, file_id, language=''):
    try:
        UPLOAD_FOLDER = 'uploads/'
        RESULTS_FOLDER = 'results/'

        _logger.info(f"Processing media file: {filepath}")

        if not os.path.exists(filepath):
            _logger.error(f"File not found: {filepath}")
            raise FileNotFoundError(f"File not found: {filepath}")

        if filepath.endswith(('.mp4', '.avi', '.mov')):
            _logger.info(f"Extracting audio from video file: {filepath}")
            audio_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.wav")
            process = subprocess.run([
                'ffmpeg', '-i', filepath, '-vn', '-acodec', 'pcm_s16le',
                '-ar', '16000', '-ac', '1', audio_path
            ], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if process.returncode != 0:
                _logger.error(f"FFmpeg error: {process.stderr.decode('utf-8', errors='replace')}")
                raise Exception(f"FFmpeg failed with error: {process.stderr.decode('utf-8', errors='replace')}")

            if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
                _logger.error(f"Audio extraction failed: {audio_path} not found or empty")
                raise Exception("Audio extraction failed: output file not found or empty")
        else:
            audio_path = filepath
            if not os.path.exists(audio_path):
                _logger.error(f"Audio file not found: {audio_path}")
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

        _logger.info("Loading whisper model")
        whisper_model = whisper.load_model("turbo")

        _logger.info(f"Starting transcription for: {audio_path}")
        decode_options = {}
        if language:
            decode_options['language'] = language
            result = whisper_model.transcribe(audio_path, fp16=False, **decode_options)
        else:
            result = whisper_model.transcribe(audio_path, fp16=False, verbose=True)
        _logger.info(f"Transcription complete with {len(result['segments'])} segments")

        _logger.info("Creating SRT file")
        srt_content = create_srt(result['segments'])
        srt_path = os.path.join(RESULTS_FOLDER, f"{file_id}.srt")
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

        _logger.info("Writing JSON results")
        json_path = os.path.join(RESULTS_FOLDER, f"{file_id}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        if filepath.endswith(('.mp4', '.avi', '.mov')) and audio_path != filepath:
            try:
                os.remove(audio_path)
                os.remove(filepath)
                _logger.info(f"Cleaned up temporary audio file: {audio_path}")
                _logger.info(f"Cleaned up Video file: {filepath}")
            except:
                _logger.warning(f"Failed to clean up temporary audio file: {audio_path}")

        return {'status': 'Completed', 'result': file_id}
    except Exception as e:
        _logger.error(f"Error processing media: {str(e)}")
        raise


def translate_subtitles(file_id, target_language):
    try:
        RESULTS_FOLDER = 'results/'
        json_path = os.path.join(RESULTS_FOLDER, f"{file_id}.json")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        from googletrans import Translator
        translator = Translator()

        for segment in data['segments']:
            translated_text = translator.translate(segment['text'], dest=target_language).text
            segment['text'] = translated_text

        srt_content = create_srt(data['segments'])
        translated_srt_path = os.path.join(RESULTS_FOLDER, f"{file_id}_{target_language}.srt")
        with open(translated_srt_path, 'w', encoding='utf-8') as f:
            f.write(srt_content)

        return {'status': 'Completed', 'result': f"{file_id}_{target_language}"}
    except Exception as e:
        _logger.error(f"Error translating subtitles: {str(e)}")
        raise
