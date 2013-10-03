#! /usr/bin/env python
# vim: set et sw=4 ts=4 ft=python:
# -*- coding: utf-8 -*-
from __future__ import print_function
from Queue import Queue, Empty
import sys
import termios
from threading import Thread
import tty


class NonBlockingReadChar:
    def __init__(self, source):
        self.queue = Queue()
        self.source = source
        self.closed = False
        self.t = Thread(target=self.__read_chars)
        self.t.daemon = True
        self.t.start()

    def readchar(self):
        try:
            char = self.queue.get_nowait()
            if char is None or char == '':
                self.closed = True
                return None
            return char
        except Empty:
            return None

    def __read_char(self):
        return self.source.read(1)

    def __read_chars(self):
        for ch in iter(self.__read_char, ''):
            if ord(ch) == 3:  # ^c
                print('\n\r[ Interrupted ]')
                break
            if ord(ch) == 4:  # eof
                break
            self.queue.put(ch)
        self.source.close()
        self.queue.put('')


class NonBlockingKeypress(object):
    KEY_INT = 3
    KEY_EOF = 4

    def __init__(self, keymap=None, pass_keys=False, source=None):
        # keymap example:
        #   key = 'a'
        #   key2 = 'b'
        #   {key: (list, of, callbacks),
        #    key2: (another, callbacks),
        #    'all': (call, for, all, keys),
        #    'default': (call, for, keys, without, specific, binding)
        #   }
        # pass_keys: bool, if True pass pressed key as first arg to callback
        # source: file like object, defaults to sys.stdin (should be/have tty?)
        if source is None:
            source = sys.stdin

        self._keymap = {}
        self._pass_keys = pass_keys
        self._input_fd = source.fileno()
        self._input_attrs = termios.tcgetattr(self._input_fd)

        if keymap is not None:
            for key, actions in keymap.iteritems():
                for action in actions:
                    self.reg_key(key, action)

    def __enter__(self):
        tty.setraw(self._input_fd)
        new_attr = termios.tcgetattr(self._input_fd)
        new_attr[3] = new_attr[3] & ~termios.ECHO
        termios.tcsetattr(self._input_fd, termios.TCSANOW, new_attr)
        self._input = NonBlockingReadChar(sys.stdin)
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        termios.tcsetattr(self._input_fd, termios.TCSADRAIN, self._input_attrs)

    def unreg_key(self, key):
        try:
            return self._keymap.pop(key)
        except KeyError:
            return None

    def reg_key(self, key, action, override=False):
        if override:
            self.unreg_key(key)
        if key not in self._keymap:
            self._keymap[key] = []
        self._keymap[key].append(action)

    def process_keys(self):
        while True:
            c = self._input.readchar()
            if c is None and self._input.closed:
                return False
            if c is None:
                break
            if c in self._keymap:
                for action in self._keymap[c]:
                    self._call(action, c)
            elif 'default' in self._keymap:
                for action in self._keymap['default']:
                    self._call(action, c)
            if 'all' in self._keymap:
                for action in self._keymap['all']:
                    self._call(action, c)
        return True

    def _call(self, action, char):
        if self._pass_keys:
            action(char)
        else:
            action()

if __name__ == '__main__':
    import time

    def interrupted():
        raise Exception('Interrupted!')

    my_keymap = {
        'default': (lambda char: print('Char "%s" pressed!\r' % char),),
        NonBlockingKeypress.KEY_INT: (interrupted,),
    }

    with NonBlockingKeypress(my_keymap) as x:
        x.reg_key('H', lambda char: print('Hello world!\r'))
        print('Press (ascii) keys ... '
              '(Shift+h for welcome msg,'
              ' Ctrl+c for int,'
              ' Ctrl+d to quit\r')
        while True:
            time.sleep(0.1)
            if not x.process_keys():
                break
