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
import sys
import time
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
_StateChangedCallback = None  #: Called when some state were changed
_LogFile = None  #: This is to have a separated Log file for state machines logs
_LogFilename = None
_LogsCount = 0  #: If not zero - it will print time since that value, not system time 
_LifeBeginsTime = 0

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
        return
    if index in _Objects:
        del _Objects[index]


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
    global _StateChangedCallback
    _StateChangedCallback = cb


def OpenLogFile(filename):
    """
    Open a file to write logs from all state machines. Very useful during debug.
    """
    global _LogFile
    global _LogFilename
    if _LogFile:
        return
    _LogFilename = filename
    try:
        _LogFile = open(_LogFilename, 'w')
    except:
        _LogFile = None


def CloseLogFile():
    """
    Close the current log file, you can than open it again.
    """
    global _LogFile
    if not _LogFile:
        return
    _LogFile.flush()
    _LogFile.close()
    _LogFile = None
    _LogFilename = None


def LifeBegins(when=None):
    """
    Call that function during program start up to print relative time in the logs, not absolute. 
    """
    global _LifeBeginsTime
    if when:
        _LifeBeginsTime = when
    else:
        _LifeBeginsTime = time.time()
    
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
          
    def __init__(self, name, state, debug_level=18, log_events=False, log_transitions=False, **kwargs):
        self.id, self.index = create_index(name)
        self.name = name
        self.state = state
        self.debug_level = debug_level
        self.log_events = log_events
        self.log_transitions = log_transitions
        self.init(**kwargs)
        set_object(self.index, self)
        self.log(self.debug_level,  'CREATED AUTOMAT %s with index %d' % (str(self), self.index))

    def __del__(self):
        global _Index
        global _StateChangedCallback
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
        self.log(debug_level, 'DESTROYED AUTOMAT %s with index %d' % (str(o), index))
        del o
        if _StateChangedCallback is not None:
            _StateChangedCallback(index, automatid, name, last_state, 'NOT_EXIST')

    def __str__(self):
        """
        Will print something like: "network_connector(CONNECTED)"
        """
        return '%s(%s)' % (self.id, self.state)

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
        self.log(self.debug_level, 'destroying %r, refs=%d' % (self, sys.getrefcount(self)), )
        self.shutdown(**kwargs)
        objects().pop(self.index)

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
        It will execute ``self.A()`` immediately. 
        """
        global _StateChangedCallback
        if _LogEvents:
            self.log(self.debug_level * 4, '%s fired with event "%s", refs=%d' % (
                self, event, sys.getrefcount(self)))
        elif self.log_events:
            self.log(self.debug_level, '%s fired with event "%s", refs=%d' % (
                self, event, sys.getrefcount(self)))
        old_state = self.state
        if self.post:
            try:
                new_state = self.A(event, *args, **kwargs)
            except:
                self.log(self.debug_level, traceback.format_exc())
                return
            self.state = new_state
        else:
            try:
                self.A(event, *args, **kwargs)
            except:
                self.log(self.debug_level, traceback.format_exc())
                return
            new_state = self.state
        if old_state != new_state:
            if self.log_transitions:
                self.log(self.debug_level, '%s(%s): (%s)->(%s)' % (self.id, event, old_state, new_state))
            self.state_changed(old_state, new_state, event, *args, **kwargs)
            if _StateChangedCallback is not None:
                _StateChangedCallback(self.index, self.id, self.name, old_state, new_state)
        else:
            self.state_not_changed(self.state, event, *args, **kwargs)

    def log(self, level, text):
        """
        Print log message. See ``OpenLogFile()`` and ``CloseLogFile()`` methods.
        """
        global _LogFile
        global _LogFilename
        global _LogsCount
        global _LifeBeginsTime
        global _Debug
        if not _Debug:
            return
        if _LogFile is not None:
            if _LogsCount > 100000:
                _LogFile.close()
                _LogFile = open(_LogFilename, 'w')
                _LogsCount = 0

            s = ' ' * level + text+'\n'
            if _LifeBeginsTime != 0:
                dt = time.time() - _LifeBeginsTime
                mn = dt // 60
                sc = dt - mn * 60
                s = ('%02d:%02d.%02d' % (mn, sc, (sc-int(sc))*100)) + s
            else:
                s = time.strftime('%H:%M:%S') + s

            _LogFile.write(s)
            _LogFile.flush()
            _LogsCount += 1
        else:
            logger.debug((' ' * level) + text)
