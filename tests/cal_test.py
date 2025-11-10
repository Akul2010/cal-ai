# run this to start the assistant (use plugin_test.py for testing the plugin core)

import argparse
import os
from core.core import Core
from assistant.cal import Assistant

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--workspace', default=os.path.dirname(os.path.dirname(__file__)), help='workspace root')
    ap.add_argument('--model', default=None, help='optional local GGUF model for LLM (ctransformers)')
    ap.add_argument('--persona', default=None, help='optional persona json')
    args = ap.parse_args()
    core = Core(args.workspace)
    print("[CAL] assistant starting: discovering plugins...")
    core.resolve_and_load()
    assistant = Assistant(args.workspace, core, model_path=args.model, persona_path=args.persona)
    assistant.run_loop()

if __name__ == "__main__":
    main()