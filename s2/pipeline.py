import queue
import threading
import time

STOP = object()


class Stage(threading.Thread):
    def __init__(self, q_in, task, q_out, name):
        self.q_in = q_in
        self.task = task
        self.q_out = q_out
        super().__init__(name=name, daemon=True)

    def run(self):
        waiting = 0
        doing = 0
        putting = 0
        cycles = 0
        try:
            while True:

                t = time.perf_counter()
                args = self.q_in.get()
                w = time.perf_counter() - t

                if args is STOP:
                    break

                t = time.perf_counter()
                result = self.task(*args)
                d = time.perf_counter() - t

                t = time.perf_counter()
                self.q_out.put(result)
                p = time.perf_counter() - t

                waiting += w
                doing += d
                putting += p
                cycles += 1

        finally:
            self.logger.debug(
                "Stage %s did %d cycles of Wait/do/put: %.3f %.3f %.3f",
                self.name,
                cycles,
                waiting,
                doing,
                putting,
            )

    def stop(self):
        try:
            while True:
                self.q_in.get_nowait()
        except queue.empty:
            pass
        self.q_in.put(STOP)
