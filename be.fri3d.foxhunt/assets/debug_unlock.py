# debug_unlock.py — pure state machine for the hidden debug-menu gesture.

_CLEARED_CODES = ("1", "22", "333")
_FINAL_CODE = "4444"
DEBUG_CODE = "1111"
_debug_code_enabled = False


def enable_debug_code():
    global _debug_code_enabled
    _debug_code_enabled = True


def disable_debug_code():
    global _debug_code_enabled
    _debug_code_enabled = False


def accepts_debug_code(code):
    return _debug_code_enabled and code == DEBUG_CODE


class DebugUnlock:
    """Recognise 1-clear, 22-clear, 333-clear, 4444.

    Keeping this independent from LVGL makes the deliberately fussy sequence
    easy to verify without starting the emulator.
    """

    def __init__(self):
        self._step = 0

    def cleared(self, code):
        if self._step < len(_CLEARED_CODES) and code == _CLEARED_CODES[self._step]:
            self._step += 1
        else:
            self._step = 0

    def entered(self, code):
        unlocked = self._step == len(_CLEARED_CODES) and code == _FINAL_CODE
        if unlocked or len(code) >= len(_FINAL_CODE):
            self._step = 0
        return unlocked
