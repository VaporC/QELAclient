
import multiprocessing as mp
from multiprocessing.managers import DictProxy
from importlib import import_module
import signal
import os


class _Process(mp.Process):
    '''
    Process for executing <functionstr> in separate environment
    and cpu core
    '''

    def __init__(self, task_queue, callback,  functionstr):
        super().__init__()

        self.task_queue = task_queue
        self.callback = callback
        # get module and function from
        i = functionstr[::-1].index('.')
        modulestr = functionstr[:-i - 1]
        functionstr = functionstr[-i:]
        # load function environment only once per process:
        module = import_module(modulestr)
        self.fn = getattr(module, functionstr)

    def run(self):
        # wait for new task:
        args, kwargs = self.task_queue.get()

        kwargs = dict(kwargs)
        sdict = kwargs.pop('sdict', None)
        if sdict:
            sdict['pid'] = self.pid
        # execute task
        answer = self.fn(*args, **kwargs)
        # inform queue:
        self.task_queue.task_done()
        # callback
        if callable(self.callback):
            self.callback(answer)


class RunFnParallel(object):
    '''
    Runs the same function multiple times and in parallel, if possible.
    The environment, needed to execute the function is only imported once,
    per process. This ensures, that after calling .addTask(...) the function 
    starts immediately.
    '''

    def __init__(self, functionstr, nprocesses=None, callback=None):
        '''
        functionstr -> e.g. 'package.module.function'
        callback -> callable witch will be called with task output
                    after task completion
        nprocesses -> if not defined, number of processes equals number
                      of available cpu cores.
                      that ensures max 100% overall load if enough tasks are assigned
        sharedDict -> enable using createSharedDict()
        '''
        self.callback = callback
        self.functionstr = functionstr
#         if sharedDict:
#             self._manager = mp.Manager()
        self._manager = None
        self.tasks = mp.JoinableQueue()
        # number of processes -> number of cpu cores
        # that ensures 100% load
        num_consumers = mp.cpu_count() if nprocesses is None else nprocesses
        # load module (and its environment)
        # FIXME ###################ADD AGAIN
#         self.consumers = [self.addProcess()
#                           for _ in range(num_consumers)]

    def addProcess(self):
        p = _Process(self.tasks, self.callback, self.functionstr)
        # start listening to tasks:
        p.start()
        return p

    def createSharedDict(self, d={}):
        if self._manager is None:
            self._manager = mp.Manager()
        if type(d) == DictProxy:
            return d
        return self._manager.dict(d)

    def addTask(self, *args, sdict=None, **kwargs):
        '''
        *args, **kwargs -> same arguments as used to execute <functionstr>

        to allow co,mmunication with the process assigne a dict to sdict

        returns dist, to communicate with the process
            the process itself can be accessed via scist['pid']

        '''
        if sdict is not None:
            sdict = self.createSharedDict(sdict)
            sdict['pid'] = None  # no process assigned jet
            kwargs['sdict'] = sdict
        self.tasks.put((args, kwargs))
        return sdict

    # where do i use than one??
    def terminateAll(self):
        '''Terminate all processes'''
        for w in self.consumers:
            w.terminate()

    def terminateProcess(self, pid):
        os.kill(pid, signal.SIGINT)
        # to keep numbers of active processed:
        self.addProcess()


# <<<<<<only for module test (need to be defined on module level)


def _MODULE_TEST_hardTask(*args):
    #     if args[0] == 12:
    #         rrh
    for i in range(10000000):
        i**1.5
    return args


def _MODULE_TEST_printresult(res):
    print('Result:', res)
# >>>>>>>


if __name__ == '__main__':
    import time
    M = RunFnParallel('RunFnParallel._MODULE_TEST_hardTask',
                      callback=_MODULE_TEST_printresult)
    sdict = M.addTask(1, sdict={})
    M.addTask(12)
    M.addTask(13)
    M.addTask(14)
    M.addTask(15)
    M.addTask(165)

    time.sleep(1)
    print(sdict)
    M.terminateProcess(sdict['pid'])
