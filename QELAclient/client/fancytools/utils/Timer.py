
from threading import Timer


class RecurringTimer(Timer):
    """
    make threading.Timer recurring
    """

    def __init__(self, timeout, fn,  start_first=False):
        self._start_first = start_first
        Timer.__init__(self, timeout, fn)

    def run(self):
        if self._start_first:
            self.function(*self.args, **self.kwargs)
        while not self.finished.is_set():
            self.finished.wait(self.interval)
            self.function(*self.args, **self.kwargs)

        self.finished.set()


if __name__ == '__main__':
    def fn():
        print(1)
    t = Timer(2, fn)
    t.start()
    print(333)
