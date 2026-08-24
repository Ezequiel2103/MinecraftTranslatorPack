import time

from gui.api import Api


def main():
    api = Api()
    calls = []
    api._emit = lambda event, payload: calls.append((event, payload))

    emit = api._throttled_progress_emitter("text_progress", min_interval=0.2)

    # Rapid-fire calls within the throttle window collapse to one --
    # this is what keeps the window from getting flooded with
    # evaluate_js calls on a big modpack.
    emit(1, 1000)
    emit(2, 1000)
    emit(3, 1000)
    assert len(calls) == 1, calls
    assert calls[0] == ("text_progress", {"current": 1, "total": 1000})

    # Once the interval has actually passed, the next call goes through.
    time.sleep(0.25)
    emit(4, 1000)
    assert len(calls) == 2, calls
    assert calls[-1] == ("text_progress", {"current": 4, "total": 1000})

    # The final item always gets through immediately, even mid-window --
    # the count on screen must land on the real total, not get stuck
    # just short of it.
    emit(1000, 1000)
    assert len(calls) == 3, calls
    assert calls[-1] == ("text_progress", {"current": 1000, "total": 1000})

    # A separate emitter (different event name / callback instance) has
    # its own independent throttle state.
    emit2 = api._throttled_progress_emitter("mod_text_progress", min_interval=0.2)
    emit2(1, 50)
    assert len(calls) == 4, calls
    assert calls[-1] == ("mod_text_progress", {"current": 1, "total": 50})

    print("Progress throttle OK")


if __name__ == "__main__":
    main()
