'''recording audio'''

import sounddevice as sd
from scipy.io.wavfile import write

fs = 44100  # Sample rate
seconds = 5  # Duration of recording

myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
print("Recording...")
sd.wait()  
print("Recording finished")
write('/Users/agakshita/AI/voice-to-voice-ai-assistant/record-output.wav', fs, myrecording) 
print("WAV file saved")

'''playing wav file'''


'''
task pr for each
master branch code
task list (to-do)
to do (in progress)
new task new pr/branch - branch nm = task nm
pr (merge)
new task
'''

'''transcibing audio using whisper'''
import whisper

model = whisper.load_model("turbo")
user_input = model.transcribe("record-output.wav")
user_prompt = user_input["text"]

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

assistant_reply = ask_groq(user_prompt)


'''text -> speech'''

from gtts import gTTS

tts = gTTS(assistant_reply)
tts.save("/Users/agakshita/AI/voice-to-voice-ai-assistant/response.mp3")

'''playing response'''
from pygame import mixer
import time
mixer.init()
mixer.music.load('/Users/agakshita/AI/voice-to-voice-ai-assistant/response.mp3')
mixer.music.play()
while mixer.music.get_busy(): 
    time.sleep(1)