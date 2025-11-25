"""
Persona engine that uses a local LLM (via LLMClient) for responses and intent detection.
"""

import json
import os
import random
from assistant.llm_client import LLMClient

class PersonaEngine:
    """
    Wrapper for intent parsing and persona responses using a local LLM.
    """

    def __init__(self, persona_path=None, model_path=None):
        self.persona = {"name":"CAL","style":"friendly, concise","wrap":"{reply}"}
        if persona_path and os.path.exists(persona_path):
            try:
                with open(persona_path) as f:
                    self.persona = json.load(f)
            except Exception:
                pass
        
        # Initialize LLM Client
        self.llm = LLMClient(model_path)

    def decorate(self, user_text, plugin_result=None):
        """
        Convert plugin result into persona-flavored text.
        """
        if self.llm.model:
            # Construct a prompt suitable for TinyLlama
            # <|system|>\n{system}</s>\n<|user|>\n{user}</s>\n<|assistant|>
            sys_prompt = f"You are {self.persona.get('name')}. Style: {self.persona.get('style')}."
            user_prompt = f"User said: {user_text}\nData: {plugin_result}\nReply to the user using the data."
            
            prompt = f"<|system|>\n{sys_prompt}</s>\n<|user|>\n{user_prompt}</s>\n<|assistant|>"
            
            out = self.llm.generate(prompt, max_new_tokens=100, temperature=0.6)
            if out:
                return out.strip()

        # fallback templating
        if plugin_result is None:
            return random.choice(["Sorry, I don't know that yet.", "I couldn't find an answer."])
        if isinstance(plugin_result, dict) and 'city' in plugin_result and 'forecast' in plugin_result:
            return f"In {plugin_result['city']}, it's {plugin_result['forecast']} at {plugin_result.get('temp_c')}°C."
        return str(plugin_result)

    def parse_intent(self, utterance, intent_specs):
        """
        Ask LLM to choose an intent from intent_specs.
        """
        if self.llm.model:
            # Build prompt
            lines = ["<|system|>\nYou are an intent classifier. Choose the best matching intent from the list. Return ONLY the index number.</s>"]
            
            user_lines = [f"Utterance: {utterance}", "Intents:"]
            for i, spec in enumerate(intent_specs):
                user_lines.append(f"{i}: {spec['name']} (keywords: {', '.join(spec.get('keywords',[])[:3])})")
            user_lines.append("Index:")
            
            prompt = "\n".join(lines) + "\n<|user|>\n" + "\n".join(user_lines) + "</s>\n<|assistant|>"
            
            out = self.llm.generate(prompt, max_new_tokens=5, temperature=0.1)
            if out:
                # Clean up output to find the number
                cleaned = ''.join(ch for ch in out if ch.isdigit())
                if cleaned:
                    try:
                        idx = int(cleaned)
                        if 0 <= idx < len(intent_specs):
                            return intent_specs[idx], 1.0
                    except ValueError:
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