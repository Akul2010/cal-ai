# minimal version helper used by runtime manager
import re
from functools import total_ordering

@total_ordering
class Version:
    def __init__(self, s):
        self.raw = str(s)
        m = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?', self.raw)
        if not m:
            self.parts = (0,0,0)
        else:
            parts = [int(x) if x is not None else 0 for x in m.groups()]
            while len(parts) < 3:
                parts.append(0)
            self.parts = tuple(parts)
    def __lt__(self, other):
        return self.parts < other.parts
    def __eq__(self, other):
        return self.parts == other.parts
    def __repr__(self):
        return ".".join(str(x) for x in self.parts)
