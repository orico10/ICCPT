import time

class Timer:
    def __init__(self):
        self.start_time = None

    def start(self):
        """initialize the timer."""
        if self.start_time is not None:
            raise RuntimeError("Timer is already running.")
        self.start_time = time.time()

    def stop(self):
        """Stop the timer and return the elapsed time."""
        if self.start_time is None:
            raise RuntimeError("Timer has not been started.")
        elapsed = time.time() - self.start_time
        self.start_time = None  # Reset the timer
        return elapsed

    def elapsed(self):
        """Return the elapsed time without stopping the timer."""
        if self.start_time is None:
            raise RuntimeError("Timer has not been started.")
        return time.time() - self.start_time
