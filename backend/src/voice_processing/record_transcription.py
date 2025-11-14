# import webrtcvad
# import pyaudio
import whisper
import os
import wave 
import time
from piper import PiperVoice, SynthesisConfig
from groq import Groq
from dotenv import load_dotenv # for groq api
load_dotenv() # reads .env and sets values into os.environ

# recording audio
'''
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
FRAME_DURATION = 30 # 480 samples (960 bytes) at 16kHz
FRAME_SIZE = int(RATE * FRAME_DURATION / 1000)  # samples per frame
CHUNK = FRAME_SIZE
RECORD_SECONDS = 30  # overall timeout if no response
MAX_SILENCE = 15 # stop if silence for 15s

def record_audio(output_file, max_silence=10):
    audio = pyaudio.PyAudio()
    stream = None
    vad = webrtcvad.Vad(2)  # 0-3 (aggressiveness)
    frames = []
    silence_start = None
    recording_started = False
    start_time = time.time()
    try:
        stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        print("Listening... speak into the mic.")
        while True:
            if time.time() - start_time > RECORD_SECONDS:
                print("Timeout reached, stopping.")
                break
            frame = stream.read(CHUNK, exception_on_overflow=False)
            # VAD expects 20, 30, or 10 ms frames at 16kHz -> so feeding 100ms
            is_speech = vad.is_speech(frame[:960], RATE)
            if is_speech:
                frames.append(frame)
                recording_started = True
                silence_start = None
            elif recording_started:
                if silence_start is None:
                    silence_start = time.time()
                elif time.time() - silence_start > MAX_SILENCE:
                    print("Silence detected, stopping.")
                    break
    finally:
        # cleanup no matter what
        if stream:
            stream.stop_stream()
            stream.close()
        audio.terminate()
    # save only if something was recorded
    if frames:
        wf = wave.open(output_file, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()
        print(f"Saved recording to {output_file}")
        return output_file
    else:
        print("No audio recorded.")
'''

# transcribing audio using whisper
def transcribe_audio(audio_file: str) -> str:
    # Transcribes speech from an audio file using Whisper
    if not os.path.exists(audio_file):
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    try:
        model = whisper.load_model("tiny")
        result = model.transcribe(audio_file)
        return result.get("text", "").strip()
    except Exception as e:
        print(f"Transcription failed: {e}")
        return ""

# ai reasoning
def ask_groq(prompt):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    client = Groq(api_key=api_key)
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b", 
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=1,
            max_completion_tokens=200,  
            top_p=1,
            reasoning_effort="medium",
            stream=False
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"I apologize, but I'm unable to process your request right now. Please try again later. (Error: {str(e)[:100]})"

# text -> speech
def generate_speech(text: str, output_file: str, model_path: str = None):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
    PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))  
    if model_path is None:
        model_path = os.path.join(PROJECT_ROOT, "en_US-lessac-low.onnx")

    try:
        voice = PiperVoice.load(model_path)  # loads only when needed
        syn_config = SynthesisConfig(
            volume=1.0,
            length_scale=1.3,
            noise_scale=0.667,
            noise_w_scale=0.8
        )
        with wave.open(output_file, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=syn_config)
        return output_file
    except Exception as e:
        print(f"TTS failed: {e}")
        return ""

# playing response
'''
def play_audio(audio_file: str, blocking: bool = True):
    if not os.path.exists(audio_file):
        print(f"Error: file not found -> {audio_file}")
        return

    with wave.open(audio_file, 'rb') as wf:
        p = pyaudio.PyAudio()

        stream = p.open(
            format=p.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )

        # read and play audio
        data = wf.readframes(1024)
        while data:
            stream.write(data)
            data = wf.readframes(1024)

        stream.stop_stream()
        stream.close()
        p.terminate()

    if blocking:
        time.sleep(0.1)  # tiny pause 
'''