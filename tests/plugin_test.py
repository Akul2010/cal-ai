from pathlib import Path
from core.core import Core

def main():
    base_dir = Path(__file__).parent.parent  # go up to /cal-ai
    core = Core(base_dir)
    core.resolve_and_load()
    print(core.list_plugins())

if __name__ == "__main__":
    main()

