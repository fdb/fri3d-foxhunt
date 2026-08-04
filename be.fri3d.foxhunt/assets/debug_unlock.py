# debug_unlock.py — session-wide switch for the 1111 test code.
#
# The debug screen itself opens from settings (five taps on the badge id);
# this module only holds the flag that screen makes the keypad honour.

DEBUG_CODE = "1111"
_debug_code_enabled = False


def enable_debug_code():
    global _debug_code_enabled
    _debug_code_enabled = True


def disable_debug_code():
    global _debug_code_enabled
    _debug_code_enabled = False


def debug_code_enabled():
    return _debug_code_enabled


def accepts_debug_code(code):
    return _debug_code_enabled and code == DEBUG_CODE
