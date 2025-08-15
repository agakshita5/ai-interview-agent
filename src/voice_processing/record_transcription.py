'''recording audio'''
import sounddevice as sd
from scipy.io.wavfile import write

def record_audio(fs=44100, duration=10, output_file='data/recorded_audio.wav'):
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()  
    write(output_file, fs, myrecording) 

'''transcibing audio using whisper'''
import whisper

def transcribe_audio(audio_file:str):
    model = whisper.load_model("turbo")
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

assistant_reply = ask_groq(transcribe_audio("data/recorded_audio.wav"))


'''text -> speech'''

# from gtts import gTTS
# tts = gTTS(assistant_reply)
# tts.save("/Users/agakshita/AI/voice-to-voice-ai-assistant/response.mp3")

from google.cloud import texttospeech
client = texttospeech.TextToSpeechClient()
def generate_speech(text: str, output_file: str = "data/response.mp3", accent: str = "en-US-Standard-C"):
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        name=accent, 
        language_code="en-US")
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(
        input=input_text,
        voice=voice,
        audio_config=audio_config)
    # The response's audio_content is binary.
    with open(output_file, "wb") as out:
        out.write(response.audio_content)

'''playing response'''
from pygame import mixer
import time
mixer.init()
mixer.music.load('data/response.mp3')
mixer.music.play()
while mixer.music.get_busy(): 
    time.sleep(1)