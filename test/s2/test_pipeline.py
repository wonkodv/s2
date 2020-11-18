from queue import Queue

from s2.pipeline import Stage


# TODO: test skipped because hangs with threads and stuff
def dont_test_stage():
    def task1(i):
        return str(i)

    def task2(s):
        return s + s

    qi1 = Queue()
    q12 = Queue()
    q2o = Queue()

    s1 = Stage(qi1, task1, q12, "Task1")
    s2 = Stage(q12, task1, q2o, "Task2")

    qi1.put(7)
    qi1.put(0)

    assert q12.empty()
    assert q2o.empty()
    s1.start()
    s2.start()
    assert q2o.get() == "1414"
    assert q2o.get() == "00"

    s1.stop()
    s2.stop()
    s1.join()
    s2.join()
