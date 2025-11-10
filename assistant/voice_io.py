"""
Simple voice I/O: optional STT/TTS; falls back to text I/O.
By default uses text I/O (safe, no external deps).
"""

import speech_recognition as sr
import pyttsx3

class VoiceIO:
    def __init__(self, use_stt=False, use_tts=False):
        self.use_stt = use_stt
        self.use_tts = use_tts
        self.stt = None
        self.tts = None
        if use_stt:
            try:
                self.stt = sr.Recognizer()
                self.sr = sr
            except Exception:
                self.stt = None
        if use_tts:
            try:
                self.tts = pyttsx3.init()
            except Exception:
                self.tts = None

    def listen(self, prompt="You: "):
        if self.stt:
            try:
                with self.sr.Microphone() as mic:
                    print(prompt, end='', flush=True)
                    audio = self.stt.listen(mic, timeout=5, phrase_time_limit=8)
                    text = self.stt.recognize_google(audio)
                    print(text)
                    return text
            except Exception:
                print("(STT failed; falling back to keyboard input)")
        try:
            return input(prompt)
        except EOFError:
            return ""

    def speak(self, text):
        print("Assistant:", text)
        if self.tts:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception:
                pass
