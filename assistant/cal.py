from assistant.voice_io import VoiceIO
from assistant.persona_engine import PersonaEngine
from assistant.nlu import NLU
from assistant.dialog_manager import DialogManager

class Assistant:
    def __init__(self, workspace, core, model_path=None, persona_path=None):
        self.core = core
        self.voice = VoiceIO()
        self.persona = PersonaEngine(persona_path=persona_path, model_path=model_path)
        self.nlu = NLU(core, persona_engine=self.persona)
        self.dialog = DialogManager(workspace, core, self.nlu, self.voice)

    def run_loop(self):
        self.voice.speak_text("Hello — CAL assistant ready.")
        try:
            while True:
                text = self.voice.listen_text("You: ")
                if not text:
                    continue
                if text.strip().lower() in ('exit','quit','stop'):
                    self.voice.speak_text("Goodbye.")
                    break
                res = self.dialog.handle_utterance(text)
                if res is None:
                    # fallback persona small talk
                    reply = self.persona.decorate(text, None)
                    self.voice.speak_text(reply)
                else:
                    # decorate plugin response
                    decorated = self.persona.decorate(text, res)
                    self.voice.speak_text(decorated)
        except KeyboardInterrupt:
            self.voice.speak_text("Shutting down.")