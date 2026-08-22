import json
import os
import time


def load_json_safe(path, default):
    """
    Reads a JSON file, tolerating one that can't be parsed -- e.g. left
    truncated by the app being force-closed mid-save -- by falling back
    to `default` instead of crashing every future read of that file
    until someone manually deletes it.
    """

    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError):
        return default


def write_json_atomic(path, data, **dump_kwargs):
    """
    Writes JSON via a temp file + atomic rename, so a process killed
    mid-write leaves the previous file intact instead of a truncated,
    unreadable one -- os.replace is atomic on both Windows and POSIX.

    Unlike POSIX, Windows refuses to replace a file that another handle
    has open at that exact instant (WinError 5, Access Denied). Two
    different things can cause that here: a brief one (another thread's
    memory lookup mid-read right when a save happens -- clears on its
    own almost immediately) and a much longer one seen in practice on
    this app's own files, consistent with antivirus real-time scanning
    treating "write a temp file, then rename it over an existing one" as
    a ransomware-like pattern and holding the target file locked while
    it inspects. Retrying handles the first case; if the lock still
    hasn't cleared after a real wait, this falls back to writing the
    target file directly (no rename) -- not atomic against a mid-write
    crash, but that specific failure is already handled on the read side
    (load_json_safe treats a corrupt file as empty rather than crashing
    the app), so it's the safe trade here: something is clearly
    preventing the rename, and the app being unable to save translation
    progress at all is worse than that residual risk.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(path.name + ".tmp")

    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, **dump_kwargs)

    attempts = 20
    for attempt in range(attempts):
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                break
            time.sleep(min(0.1 * (attempt + 1), 1.0))

    try:
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, **dump_kwargs)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass
