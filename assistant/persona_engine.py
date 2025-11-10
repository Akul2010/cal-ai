"""
Optional offline persona decorator.
If `ctransformers` is installed and a GGUF model provided, it will use it.
Otherwise it falls back to a trivial template-based persona.
"""

from ctransformers import AutoModelForCausalLM
import json
import os
import random

class PersonaEngine:
    """
    Offline LLM wrapper for intent parsing and persona responses.
    Uses ctransformers if available and model_path provided; otherwise falls back to template behavior.
    """

    def __init__(self, persona_path=None, model_path=None):
        self.persona = {"name":"CAL","style":"friendly, concise","wrap":"{reply}"}
        if persona_path and os.path.exists(persona_path):
            try:
                self.persona = json.load(open(persona_path))
            except Exception:
                pass
        self.model = None
        if model_path:
            try:
                self.model = AutoModelForCausalLM.from_pretrained(model_path)
                print("[CAL][persona] Loaded local LLM model:", model_path)
            except Exception as e:
                print("[CAL][persona] model load failed:", e)
                self.model = None

    def decorate(self, user_text, plugin_result=None):
        """
        Convert plugin result into persona-flavored text. If model available, calls it.
        """
        if self.model:
            prompt = f"You are {self.persona.get('name')}, {self.persona.get('style')}.\nUser: {user_text}\nData: {plugin_result}\nReply briefly."
            try:
                out = self.model(prompt, max_new_tokens=80, temperature=0.6)
                return out.strip()
            except Exception:
                pass
        # fallback templating
        if plugin_result is None:
            return random.choice(["Sorry, I don't know that yet.", "I couldn't find an answer."])
        if isinstance(plugin_result, dict) and 'city' in plugin_result and 'forecast' in plugin_result:
            return f"In {plugin_result['city']}, it's {plugin_result['forecast']} at {plugin_result.get('temp_c')}°C."
        return str(plugin_result)

    def parse_intent(self, utterance, intent_specs):
        """
        If a local model exists, ask it to choose an intent from intent_specs.
        Otherwise fallback to keyword scoring.
        intent_specs: list of IntentSpec-like dicts with keys: name, plugin, export, keywords, examples.
        Returns (chosen_intent_spec, score) or (None,0).
        """
        if self.model:
            # Build a small prompt listing intents and examples
            lines = ["You are an intent classifier. Choose the best matching intent name from the list."]
            lines.append("Utterance: " + utterance)
            lines.append("Intents:")
            for i, spec in enumerate(intent_specs):
                lines.append(f"{i}: name={spec['name']}, keywords={spec.get('keywords',[])}, examples={spec.get('examples',[])}")
            lines.append("Respond with the integer index of the best intent (or -1 if none).")
            prompt = "\n".join(lines)
            try:
                out = self.model(prompt, max_new_tokens=16, temperature=0.0)
                out = out.strip()
                # attempt to parse an int
                idx = int(''.join(ch for ch in out if ch.isdigit() or ch == '-'))
                if 0 <= idx < len(intent_specs):
                    return intent_specs[idx], 1.0
            except Exception:
                pass
        # fallback: simple scoring by keywords/examples
        best = None; best_score = 0
        u = utterance.lower()
        for spec in intent_specs:
            score = 0
            for kw in spec.get('keywords', []):
                if kw.lower() in u:
                    score += 10
            for ex in spec.get('examples', []):
                if ex.lower() in u:
                    score += 20
            if score > best_score:
                best_score = score; best = spec
        if best_score > 0:
            return best, float(best_score)
        return None, 0.0