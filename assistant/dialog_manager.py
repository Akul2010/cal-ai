"""
Dialog manager that uses type-free slots and regex-only validators.
- When a slot has a 'validator' string, it's treated as a regex and validated via re.fullmatch.
- No slot typing; assistant passes filled slots dict to plugin export.
- Supports simple confirmations using confirm_template.
- Persists session state to assistant_state.json in workspace.
"""

import os
import json
import time
import re

import os, json, time, re

STATE_FILE = "assistant_state.json"

class DialogSession:
    def __init__(self, workspace, session_id="default"):
        self.ws = os.path.abspath(workspace)
        self.id = session_id
        self.state = {"session_id": self.id, "current_intent": None, "filled_slots": {}, "pending": None, "history": []}
        self._load()

    def _path(self):
        return os.path.join(self.ws, STATE_FILE)

    def _load(self):
        p = self._path()
        if os.path.exists(p):
            try:
                data = json.load(open(p,'r'))
                if self.id in data:
                    self.state = data[self.id]
            except Exception:
                pass

    def save(self):
        p = self._path()
        data = {}
        if os.path.exists(p):
            try:
                data = json.load(open(p,'r'))
            except Exception:
                data = {}
        data[self.id] = self.state
        try:
            json.dump(data, open(p,'w'), indent=2)
        except Exception:
            pass

class DialogManager:
    def __init__(self, workspace, core, nlu, voice):
        self.workspace = workspace
        self.core = core
        self.nlu = nlu
        self.voice = voice
        self.session = DialogSession(workspace)

    def _next_required(self, intent_spec):
        for sname, sdef in intent_spec.slots.items():
            if sdef.get('required') and sname not in self.session.state['filled_slots']:
                return sname, sdef
        return None, None

    def _validate_regex(self, pattern, value):
        if not pattern:
            return True
        try:
            return re.fullmatch(pattern, value) is not None
        except Exception:
            return False

    def handle_utterance(self, utterance):
        # If in-progress intent, continue
        cur = self.session.state.get('current_intent')
        if cur:
            # resume existing
            intent = None
            for s in self.nlu.intent_specs:
                if s.name == cur['name'] and s.plugin == cur['plugin']:
                    intent = s; break
            if not intent:
                self.session.state['current_intent'] = None
                self.session.save()
            else:
                # merge simple auto slots
                _, global_slots = self.nlu.parse(utterance)  # fallback parse for autoslots
                for k,v in global_slots.items():
                    if k not in self.session.state['filled_slots']:
                        self.session.state['filled_slots'][k] = v
                # find next required
                next_name, next_def = self._next_required(intent)
                if next_name:
                    ans = self.voice.listen(next_def.get('prompt') + " ")
                    ok = self._validate_regex(next_def.get('validator'), ans.strip())
                    if not ok:
                        self.voice.speak("I didn't get that.")
                        retry = self.voice.listen(next_def.get('prompt') + " ")
                        ok = self._validate_regex(next_def.get('validator'), retry.strip())
                        if not ok:
                            self.voice.speak("Cancelling request.")
                            self.session.state['current_intent'] = None
                            self.session.save()
                            return None
                        val = retry.strip()
                    else:
                        val = ans.strip()
                    self.session.state['filled_slots'][next_name] = val
                    self.session.save()
                # check if all required filled
                nr, _ = self._next_required(intent)
                if nr is None:
                    # confirm if needed
                    if intent.confirm_template:
                        text = intent.confirm_template.format(**self.session.state['filled_slots'])
                        self.voice.speak(text)
                        ans = self.voice.listen("(yes/no) ")
                        if ans.strip().lower() not in ('yes','y','ok','sure'):
                            self.voice.speak("Cancelled.")
                            self.session.state['current_intent'] = None
                            self.session.save()
                            return None
                    # call plugin
                    res = self._call_plugin(intent, self.session.state['filled_slots'])
                    self.session.state['history'].append({'intent': intent.name, 'slots': self.session.state['filled_slots'], 'result': str(res), 'ts': time.time()})
                    self.session.state['current_intent'] = None
                    self.session.state['filled_slots'] = {}
                    self.session.save()
                    return res
                return None

        # no active session: parse intent
        intent, autoslots = self.nlu.parse(utterance)
        if not intent:
            return None
        # start session
        self.session.state['current_intent'] = {'name': intent.name, 'plugin': intent.plugin}
        # seed autoslots
        self.session.state['filled_slots'].update(autoslots or {})
        self.session.save()
        # prompt next required
        next_name, next_def = self._next_required(intent)
        if next_name:
            ans = self.voice.listen(next_def.get('prompt') + " ")
            ok = self._validate_regex(next_def.get('validator'), ans.strip())
            if not ok:
                self.voice.speak("I didn't understand.")
                retry = self.voice.listen(next_def.get('prompt') + " ")
                ok = self._validate_regex(next_def.get('validator'), retry.strip())
                if not ok:
                    self.voice.speak("Cancelling.")
                    self.session.state['current_intent'] = None
                    self.session.save()
                    return None
                val = retry.strip()
            else:
                val = ans.strip()
            self.session.state['filled_slots'][next_name] = val
            self.session.save()
        # if all filled, confirm/call
        nr, _ = self._next_required(intent)
        if nr is None:
            if intent.confirm_template:
                text = intent.confirm_template.format(**self.session.state['filled_slots'])
                self.voice.speak(text)
                ans = self.voice.listen("(yes/no) ")
                if ans.strip().lower() not in ('yes','y','ok','sure'):
                    self.voice.speak("Cancelled.")
                    self.session.state['current_intent'] = None
                    self.session.save()
                    return None
            res = self._call_plugin(intent, self.session.state['filled_slots'])
            self.session.state['history'].append({'intent': intent.name, 'slots': self.session.state['filled_slots'], 'result': str(res), 'ts': time.time()})
            self.session.state['current_intent'] = None
            self.session.state['filled_slots'] = {}
            self.session.save()
            return res
        return None

    def _call_plugin(self, intent, slots):
        # central call through registry
        try:
            return self.core.run_plugin(intent.plugin, intent.export, slots)
        except Exception as e:
            return f"Plugin call failed: {e}"