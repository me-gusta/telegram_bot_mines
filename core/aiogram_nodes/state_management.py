from typing import Type, Dict

import ujson

from core.constants import FILES_DIR

STATE_MANAGEMENT_FILE_NAME = 'state_management.json'


class StateManager:
    uid = 0

    generated: Dict[str, int] = {}
    is_loaded = False

    @classmethod
    def generate_simple(cls, klass: Type) -> str:
        name = klass.__name__
        if not cls.is_loaded:
            cls.generated = load_states()
            cls.is_loaded = True
            cls.uid = max([x for x in cls.generated.values()] + [0])
        try:
            return cls.get(name)
        except KeyError:
            pass
        cls.uid += 1
        cls.generated[name] = cls.uid
        store_states(cls.generated)
        return str(cls.uid)

    @classmethod
    def get(cls, name: str) -> str:
        return str(cls.generated[name])


def load_states() -> Dict[str, int]:
    with open(FILES_DIR / STATE_MANAGEMENT_FILE_NAME, 'r') as f:
        try:
            return ujson.loads(f.read())
        except ujson.JSONDecodeError:
            return {}


def store_states(states: Dict[str, int]):
    with open(FILES_DIR / STATE_MANAGEMENT_FILE_NAME, 'w') as f:
        return f.write(ujson.dumps(states))
