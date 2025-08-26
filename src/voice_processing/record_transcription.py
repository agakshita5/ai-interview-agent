'''recording audio'''
import sounddevice as sd
from scipy.io.wavfile import write

def record_audio(output_file,fs=44100, duration=13):
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()  
    write(output_file, fs, myrecording) 

'''transcibing audio using whisper'''
import whisper

def transcribe_audio(audio_file:str):
    model = whisper.load_model("base")
    audio_input = model.transcribe(audio_file)
    return audio_input["text"]

'''ai reasoning'''
from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def ask_groq(prompt):
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

'''text -> speech'''
import wave
from piper import PiperVoice, SynthesisConfig
from pydub import AudioSegment

def generate_speech(text: str, output_file: str, model_path: str = "en_US-lessac-medium.onnx"):# Load voice model
    voice = PiperVoice.load(model_path)
    temp_wav = "data/temp.wav"
    syn_config = SynthesisConfig(
        volume=1.0,        
        length_scale=1.3,  
        noise_scale=0.667, 
        noise_w_scale=0.8  
    )

    with wave.open(temp_wav, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, syn_config=syn_config)

    # Convert to MP3
    sound = AudioSegment.from_wav(temp_wav)
    sound.export(output_file, format="mp3")

    return output_file

'''playing response'''
from pygame import mixer
import time
def play_audio(audio_file: str):
    mixer.init()
    mixer.music.load(audio_file)
    mixer.music.play()
    while mixer.music.get_busy(): 
        time.sleep(1)
    