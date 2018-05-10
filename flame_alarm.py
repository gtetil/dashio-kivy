import time

class FlameAlarm:

    def __init__(self, **kwargs):
        self.prev_state = False
        self.flame_on_latch = False
        self.alarm = False
        self.on_debounce_time = 5
        self.off_debounce_time = 1
        self.prev_time = time.time()

    def update(self, state):
        self.alarm = False # always reset alarm as it is used as an event

        # check if flame state has changed
        if state and not self.prev_state or self.prev_state and not state:
            self.prev_time = time.time()  # state changed, so reset timer

        alarm_timer = time.time() - self.prev_time

        if state:
            if alarm_timer > self.on_debounce_time:
                self.flame_on_latch = True  # flame has been on long enough, so allow alarm to occur
        else:
            if (alarm_timer > self.off_debounce_time) and self.flame_on_latch:
                self.flame_on_latch = False
                self.alarm = True # flame has been off long enough, and it was previously on long enough, so set alarm

        self.prev_state = state

        return self.alarm