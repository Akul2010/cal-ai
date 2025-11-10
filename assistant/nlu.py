"""
Type-free slots NLU (regex-only validators are in the dialog manager).
Builds simple intent specs from plugin manifests and performs keyword/example matching.
"""

from assistant.persona_engine import PersonaEngine

class IntentSpec:
    def __init__(self, name, plugin, export, keywords=None, examples=None, slots=None, confirm_template=None):
        self.name = name
        self.plugin = plugin
        self.export = export
        self.keywords = keywords or []
        self.examples = examples or []
        self.slots = slots or {}
        self.confirm_template = confirm_template

    def to_dict(self):
        return {"name": self.name, "plugin": self.plugin, "export": self.export,
                "keywords": self.keywords, "examples": self.examples}

class NLU:
    def __init__(self, core, persona_engine=None):
        self.core = core
        self.persona = persona_engine or PersonaEngine()
        self.intent_specs = []
        self._build_from_manifests()

    def _build_from_manifests(self):
        self.intent_specs = []
        for pname, pdata in self.core.registry.plugins.items():
            manifest = pdata.get('manifest') or {}
            for iname, idef in (manifest.get('intents') or {}).items():
                slots = {}
                for sname, sdef in (idef.get('slots') or {}).items():
                    slots[sname] = {'prompt': sdef.get('prompt'), 'required': sdef.get('required', False), 'validator': sdef.get('validator')}
                spec = IntentSpec(iname, pname, idef.get('export') or iname, idef.get('keywords', []), idef.get('examples', []), slots, idef.get('confirm_template'))
                self.intent_specs.append(spec)

    def parse(self, utterance):
        # ask persona engine (LLM) if available
        specs = [s.to_dict() for s in self.intent_specs]
        chosen, score = self.persona.parse_intent(utterance, specs)
        if chosen:
            # find matching IntentSpec
            for s in self.intent_specs:
                if s.name == chosen['name'] and s.plugin == chosen['plugin']:
                    return s, {}
        # fallback: simple match by keywords
        # return first matching spec with naive slot extractions (location/number heuristics)
        u = utterance.lower()
        for s in self.intent_specs:
            for kw in s.keywords:
                if kw.lower() in u:
                    # simple global slots
                    slots = {}
                    import re
                    m = re.search(r'\b(?:in|for|at)\s+([A-Za-z0-9 \-]+)', utterance, re.IGNORECASE)
                    if m:
                        slots['location'] = m.group(1).strip()
                    m2 = re.search(r'\b(-?\d+)\b', utterance)
                    if m2:
                        try:
                            slots['number'] = int(m2.group(1))
                        except Exception:
                            pass
                    return s, slots
        return None, {}