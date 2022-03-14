#!/usr/bin/env python

#   Copyright 2016 Scott Bezek
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from xvfbwrapper import Xvfb
from contextlib import contextmanager
import subprocess
import time


class PopenContext(subprocess.Popen):
    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        if self.stdin:
            self.stdin.close()
        if type:
            self.terminate()
        # Wait for the process to terminate, to avoid zombies.
        self.wait()


def xdotool(command):
    return subprocess.check_output(['xdotool'] + command)


def wait_for_window(window_regex, timeout=10):
    DELAY = 0.5
    for i in range(int(timeout/DELAY)):
        try:
            xdotool(['search', '--name', window_regex])
            return
        except subprocess.CalledProcessError:
            pass
        time.sleep(DELAY)
    raise RuntimeError('Timed out waiting for %s window' % window_regex)
