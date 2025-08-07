
'''playing mp3 format'''
# from pygame import mixer
# import time
# mixer.init()
# mixer.music.load('/Users/agakshita/AI/voice-to-voice-ai-assistant/coin-audio.mp3')
# mixer.music.play()
# while mixer.music.get_busy(): # wait for music to finish playing
#     time.sleep(1)

'''recording audio'''
# python-sounddevice records to NumPy arrays and pyaudio records to bytes objects. 
# Both of these can be stored as WAV files using the scipy and wave libraries, respectively

# import sounddevice as sd
# from scipy.io.wavfile import write
# import numpy as np

# fs = 44100  # Sample rate
# seconds = 3  # Duration of recording

# myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
# print("Recording...")
# sd.wait()  # Wait until recording is finished
# print("Recording finished")
# # audio_data = np.copy((myrecording * 32767).astype(np.int16)) -> when using simplaaudio
# write('/Users/agakshita/AI/voice-to-voice-ai-assistant/record-output.wav', fs, myrecording) 
# print("WAV file saved")
# 32767 is the maximum value for a 16-bit integer
# The default behavior of sounddevice.rec() with scipy.io.wavfile.write() saves the audio as float32, which is not compatible with simpleaudio
# hence converting the float recording (in range -1.0 to 1.0) to 16-bit PCM format — the standard for WAV files.

'''either convert wav to mp3 or mp3 to wav''' 
# can play either of them -> use pygame, it worked for both wav and mp3

'''playing wav file'''

# import simpleaudio as sa -> not working for wav
# from pydub import AudioSegment -> not working for wav
# playsound -> outdatd on macOs

# from pygame import mixer
# import time
# mixer.init()
# mixer.music.load('/Users/agakshita/AI/voice-to-voice-ai-assistant/record-output.wav')
# mixer.music.play()
# while mixer.music.get_busy(): # wait for music to finish playing
#     time.sleep(1)

'''converting wav to mp3 and can play it using pygame'''
# from pydub import AudioSegment
# sound = AudioSegment.from_wav('/Users/agakshita/AI/voice-to-voice-ai-assistant/record-output.wav')
# sound.export('/Users/agakshita/AI/voice-to-voice-ai-assistant/record-output.mp3', format='mp3')


'''transcibing audio using whisper'''
import whisper

model = whisper.load_model("turbo")
result = model.transcribe("record-output.wav")
print(result["text"])


'''
task pr for each
master branch code
task list (to-do)
to do (in progress)
new task new pr/branch - branch nm = task nm
pr (merge)
new task
'''