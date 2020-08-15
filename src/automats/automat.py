#!/usr/bin/python
#automat.py
#
# <<<COPYRIGHT>>>
#
#
#
#

"""
.. module:: automat

This is the base class for State Machine.

You can read more about `Automata-based programming <http://en.wikipedia.org/wiki/Automata-based_programming>`_
principles and learn how to develop your project in such way.

This is a programming paradigm in which the program or its part is thought of as a model of a
`finite state machine <http://en.wikipedia.org/wiki/Finite_state_machine>`_ or any other formal automaton.

Its defining characteristic is the use of finite state machines to
`describe program behavior <http://en.wikipedia.org/wiki/State_diagram>`_.

The transition graphs of state machines are used in all stages of software development:
- specification,
- implementation, 
- debugging and
- documentation.

A small tool called `visio2python <https://github.com/vesellov/visio2python/>`_
was written by Veselin Penev to simplify working with the visualized state machines.
It can translate transition graphs created in Microsoft Visio into Python code.

Automata-Based Programming technology was introduced by Anatoly Shalyto in 1991 and Switch-technology was
developed to support automata-based programming.
Automata-Based Programming is considered to be rather general purpose program development methodology
than just another one finite state machine implementation.
Anatoly Shalyto is the former of
`Foundation for Open Project Documentation <http://en.wikipedia.org/wiki/Foundation_for_Open_Project_Documentation>`_.

Read more about Switch-technology on the Saint-Petersburg National Research University
of Information Technologies, Mechanics and Optics, Programming Technologies Department
`Page <http://is.ifmo.ru/english>`_.
"""

#------------------------------------------------------------------------------

import logging
import traceback

#------------------------------------------------------------------------------ 

logger = logging.getLogger(__name__)

#------------------------------------------------------------------------------

_Debug = True       # set to False to turn off any logging
_LogEvents = True   # set to True to log every event passed to any state machine

#------------------------------------------------------------------------------

_Counter = 0  #: Increment by one for every new object, the idea is to keep unique ID's in the index
_Index = {}   #: Index dictionary, unique id (string) to index (int)
_Objects = {} #: Objects dictionary to store all state machines objects
_GlobalStateChangedCallback = None  #: Called when some state were changed

#------------------------------------------------------------------------------ 

def get_new_index():
    """
    Just get the current index and increase by one
    """
    global _Counter
    _Counter += 1
    return _Counter


def create_index(name):
    """
    Generate unique ID, and put it into Index dict, increment counter 
    """
    global _Index
    automatid = name
    if id in _Index:
        i = 1
        while _Index.get(automatid + '(' + str(i) + ')'):
            i += 1
        automatid = name + '(' + str(i) + ')'
    _Index[automatid] = get_new_index()
    return automatid, _Index[automatid]


def set_object(index, obj):
    """
    Put object for that index into memory
    """
    global _Objects
    _Objects[index] = obj


def clear_object(index):
    """
    Clear object with given index from memory
    """
    global _Objects
    if _Objects is None:
        return False
    if index in _Objects:
        del _Objects[index]
        return True
    return False


def objects():
    """
    Get all state machines stored in memory
    """
    global _Objects
    return _Objects

#------------------------------------------------------------------------------ 

def SetStateChangedCallback(cb):
    """
    Set callback to be fired when any state machine globally changes its state 
    Callback parameters are::
    
        cb(index, id, name, old_state, new_state)
    """
    global _GlobalStateChangedCallback
    _GlobalStateChangedCallback = cb

#------------------------------------------------------------------------------ 

class Automat(object):
    """
    Base class of the State Machine Object.
    You need to subclass this class and override the method ``A(event, arg)``.
    Constructor needs the ``name`` of the state machine and the beginning ``state``.
    At first it generate an unique ``id`` and new ``index`` value.  
    You can use ``init()`` method in the subclass to call some code at start.
    Finally put the new object into the memory with given index - 
    it is placed into ``objects()`` dictionary.
    To remove the instance call ``destroy()`` method.  
    """

    state = 'NOT_EXIST'
    """
    This is a string representing current Machine state, must be set in the constructor.
    ``NOT_EXIST`` indicates that this machine is not created yet.
    A blank state is a fundamental mistake! 
    """

    post = False
    """
    Sometimes need to set the new state AFTER finish all actions.
    Set ``post = True`` to call ``self.state = <newstate>``
    in the ``self.event()`` method, not in the ``self.A()`` method.
    You also must set that flag in the MS Visio document and rebuild the code:
    put ``[post]`` string into the last line of the LABEL shape.
    """
          
    def __init__(self,
            name,
            state,
            inputs=None,
            outputs=None,
            debug_level=18,
            log_events=False,
            log_transitions=False,
            raise_errors=False,
            **kwargs
        ):
        self.id, self.index = create_index(name)
        self.name = name
        self.state = state
        self.inputs = inputs
        self.outputs = outputs
        self._prev_state = None
        self._executing = False
        self._executions = 0
        self._current_execution = -1
        self._heap = {}
        self.debug_level = debug_level
        self.log_events = log_events
        self.log_transitions = log_transitions
        self.raise_errors = raise_errors
        self._state_callbacks = {}
        self.init(**kwargs)
        self.register()
        self.log(self.debug_level,  'CREATED AUTOMAT %s with index %d' % (str(self), self.index))

    def __del__(self):
        global _Index
        global _GlobalStateChangedCallback
        if self is None:
            return
        o = self
        last_state = self.state
        automatid = self.id
        name = self.name
        debug_level = self.debug_level
        if _Index is None:
            self.log(debug_level, 'automat.__del__ WARNING Index is None: %r %r' % (automatid, name))
            return
        index = _Index.get(automatid, None)
        if index is None:
            self.log(debug_level, 'automat.__del__ WARNING %s not found' % automatid)
            return
        del _Index[automatid]
        self.log(debug_level, 'DESTROYED AUTOMAT %s with index %d' % (str(o), index, ))
        del o
        if _GlobalStateChangedCallback is not None:
            _GlobalStateChangedCallback(index, automatid, name, last_state, 'NOT_EXIST')

    def __str__(self):
        """
        Will return something like: "network_connector(CONNECTED)"
        """
        return self.label

    def __repr__(self):
        """
        Will return something like: "network_connector(CONNECTED)"
        """
        return self.label

    @property
    def label(self):
        return '%s(%s)' % (self.id, self.state)

    def register(self):
        """
        Put reference to this automat instance into a global dictionary.
        """
        set_object(self.index, self)
        return self.index

    def unregister(self):
        """
        Removes reference to this instance from global dictionary tracking all state machines.
        """
        clear_object(self.index)
        return True

    def init(self, **kwargs):
        """
        Define this method in subclass to execute some code when creating an object.
        """

    def shutdown(self, **kwargs):
        """
        Define this method in subclass to execute some code when destroying an object.
        """

    def destroy(self, **kwargs):
        """
        Call this method to remove the state machine from the ``objects()`` dictionary
        and delete that instance. Be sure to not have any existing references on 
        that instance so destructor will be called immediately.
        """
        self.log(self.debug_level + 2, 'destroying %s, index=%d, heap=%d' % (
            self, self.index, len(self._heap), ))
        self.shutdown(**kwargs)
        self.unregister()

    def state_changed(self, oldstate, newstate, event, *args, **kwargs):
        """
        Redefine this method in subclass to be able to catch the moment 
        immediately after automat's state were changed.
        """        

    def state_not_changed(self, curstate, event, *args, **kwargs):
        """
        Redefine this method in subclass if you want to do some actions
        immediately after processing the event, which did not change the automat's state.
        """        

    def log(self, level, text):
        """
        Print log message. See ``OpenLogFile()`` and ``CloseLogFile()`` methods.
        """
        global _Debug
        if not _Debug:
            return
        logger.info((' ' * level) + text)

    def add_state_changed_callback(self, cb, oldstate=None, newstate=None, callback_id=None):
        """
        You can add a callback function to be executed when state machine
        reaches given scenario, it will be called with such arguments:

            cb(oldstate, newstate, event, *args, **kwargs)

        For example, method_B() will be called when machine_A become "ONLINE":

            machine_A.add_state_changed_callback(method_B, None, "ONLINE")

        If you set "None" to both arguments,
        the callback will be executed every time when the state gets changed:

            machineB.add_state_changed_callback(method_B)

        """
        key = (oldstate, newstate)
        if key not in self._state_callbacks:
            self._state_callbacks[key] = []
        if cb not in self._state_callbacks[key]:
            self._state_callbacks[key].append((callback_id, cb))

    def remove_state_changed_callback(self, cb=None, callback_id=None):
        """
        Remove given callback from the state machine.
        """
        removed_count = 0
        for key in list(self._state_callbacks.keys()):
            cb_list = self._state_callbacks[key]
            for cb_tupl in cb_list:
                cb_id_, cb_ = cb_tupl
                if cb and cb == cb_:
                    self._state_callbacks[key].remove(cb_tupl)
                    removed_count += 1
                if callback_id and callback_id == cb_id_:
                    self._state_callbacks[key].remove(cb_tupl)
                    removed_count += 1
                if len(self._state_callbacks[key]) == 0:
                    self._state_callbacks.pop(key)
        return removed_count

    def remove_state_changed_callback_by_state(self, oldstate=None, newstate=None):
        """
        Removes all callback methods with given condition.

        This is useful if you use ``lambda x: do_somethig()`` to catch
        the moment when state gets changed.
        """
        for key in list(self._state_callbacks.keys()):
            if key == (oldstate, newstate):
                self._state_callbacks.pop(key)
                break

    def execute_state_changed_callbacks(self, oldstate, newstate, event, *args, **kwargs):
        """
        Compare conditions and execute state changed callback methods matching criteria.
        """
        for key, cb_list in self._state_callbacks.items():
            old, new = key
            catched = False
            if old is None and new is None:
                catched = True
            elif old is None and new == newstate and newstate != oldstate:
                catched = True
            elif new is None and old == oldstate and newstate != oldstate:
                catched = True
            elif old == oldstate and new == newstate:
                catched = True
            if catched:
                for cb_tupl in cb_list:
                    _, cb = cb_tupl
                    cb(oldstate, newstate, event, *args, **kwargs)

    def A(self, event, *args, **kwargs):
        """
        Must define this method in subclass. 
        This is the core method of the SWITCH-technology.
        I am using ``visio2python`` (created by me) to generate Python code from MS Visio drawing.
        """
        raise NotImplementedError

    def automat(self, event, *args, **kwargs):
        """
        Just an alias for `event()` method.
        """
        return self.event(event, *args, **kwargs)

    def event(self, event, *args, **kwargs):
        """
        Use that method to send ``event`` directly to the state machine.
        It will execute ``self.A()`` immediately, run callbacks and loggers. 
        """
        if self._executing:
            # TODO: check what will happen if self.post is True
            if self._current_execution in self._heap:
                _event, _args, _kwargs = self._heap.pop(self._current_execution)
                self._executing = False
                self._post_processing(self.state, _event, *_args, **_kwargs)
            else:
                raise Exception('Last execution info was not found in the heap')
        self._executing = True
        self._current_execution = self._executions
        self._executions += 1
        self._heap[self._current_execution] = (event, args, kwargs)
        new_state = self._execute(event, *args, **kwargs)
        _event, _args, _kwargs = None, None, None
        if self._current_execution in self._heap:
            _event, _args, _kwargs = self._heap.pop(self._current_execution)
        self._executing = False
        if new_state is None:
            return None
        if _event:
            self._post_processing(new_state, _event, *_args, **_kwargs)
        return new_state

    def _execute(self, event, *args, **kwargs):
        if _LogEvents:
            self.log(self.debug_level + 4, '%s fired with event "%s"' % (
                self, event, ))
        elif self.log_events:
            self.log(self.debug_level + 4, '%s fired with event "%s"' % (
                self, event, ))
        self._prev_state = self.state
        if self.post:
            if self.raise_errors:
                new_state = self.A(event, *args, **kwargs)
            else:
                try:
                    new_state = self.A(event, *args, **kwargs)
                except:
                    self.log(self.debug_level, traceback.format_exc())
                    return None
            self.state = new_state
        else:
            if self.raise_errors:
                new_state = self.A(event, *args, **kwargs)
            else:
                try:
                    self.A(event, *args, **kwargs)
                except:
                    self.log(self.debug_level, traceback.format_exc())
                    return None
            new_state = self.state
        return new_state

    def _post_processing(self, new_state, event, *args, **kwargs):
        global _GlobalStateChangedCallback
        if self._prev_state != new_state:
            if self.log_transitions:
                self.log(self.debug_level + 2, '%s after "%s" : (%s)->(%s)' % (self, event, self._prev_state, new_state))
            self.state_changed(self._prev_state, new_state, event, *args, **kwargs)
            if _GlobalStateChangedCallback is not None:
                _GlobalStateChangedCallback(self.index, self.id, self.name, self._prev_state, new_state)
        else:
            self.state_not_changed(self.state, event, *args, **kwargs)
        self.execute_state_changed_callbacks(self._prev_state, new_state, event, *args, **kwargs)
        return True
