"""A utility for controlling, and binding events to the C* Music Player.
"""

import re
import time
import psutil
import subprocess
from pathlib import Path

types = {
    "\d*\.\d+": float,
    "((T|t)rue|(F|f)alse)": lambda value: True if value.lower() == "true" \
                                               else False,
    "\d+": int,
}


class CmusNotRunning(Exception):
    pass


class Cmus():
    """The Cmus wrapper.
    """

    
    def __init__(self):
        self._alive = self._is_running()
        self._events = {
            "on_started": [],
            "on_ended": [],
        }


    @staticmethod
    def _is_running() -> bool:
        """Returns whether or not Cmus is currently running.

        :return: whether or not Cmus is running
        :rtype bool
        """

        return any(proc.name() == "cmus" for proc in psutil.process_iter())

    @staticmethod
    def _typecast(value: str) -> any:
        """Converts a string's contents to it's type.

        :return: the casted type
        :rtype: any
        """

        for pattern, cast_to in types.items():
            if re.match(pattern, value):
                try:
                    return cast_to(value)
                except ValueError:
                    break

        return value

    def get_state_info(self) -> dict:
        """Returns a dictionary with the information from the Cmus
        state inside of it.

        :return: the state information of Cmus
        :rtype: dict
        """

        if self._is_running() is False:
            raise CmusNotRunning

        default_states = {
            "values": {
                "status": "",
                "file": "",
                "duration": 0,
                "position": 0,
            },
            "tag": {
                "artist": "",
                "album": "",
                "title": "",
                "tracknumber": 0,
            },
            "set": {
                "aaa_mode": "",
                "continue": False,
                "play_library": False,
                "play_sorted": False,
                "replaygain": False,
                "replaygain_limit": False,
                "replaygain_preamp": 0.0,
                "repeat": False,
                "repeat_current": False,
                "shuffle": False,
                "softvol": False,
                "vol_left": 0,
                "vol_right": 0,
            },
        }

        # Saves the output of status.
        output = subprocess.check_output(["cmus-remote", "-C", "status"]).decode("UTF-8") 

        # Load the Cmus states.
        for line in (output.splitlines()):
            words = line.split(" ")
            section_name = words[0]

            # Sections have three-fields
            if section_name in default_states.keys():
                section = default_states[section_name]
                field_name = words[1]

                default_states[field_name] = self._typecast(" ".join(words[2:]))
            else:
                field_name = words[0]
                default_states["values"][field_name] = self._typecast(" ".join(words[1:]))

        return default_states

    def get_filename(self) -> str:
        """Returns the name of the currently playing file.

        :return: the name of the currently playing file
        :rtype: str
        """

        filename = Path(self.get_state_info()["values"]["file"]).stem

        if len(filename) > 0:
            return filename
        else:
            return ""

    def hook(self, event: str, callback: callable):
        """Hooks a new event for an event.

        :param event: the name of the event to hook to
        :type event: str
        :param callback: the function to hook to the event
        :type callback:
        """

        if self._events.get(event) is not None:
            self._events[event].append(callback)
        else:
            raise KeyError(f"'{event}' is not an event.")

    def monitor(self, blocking=False):
        """Begins monitoring for event callbacks.

        :param blocking: whether or not to block
        :type blocking: bool
        """

        while True:
            alive_state = self._is_running()

            # If Cmus is now running, and it was not already opened.
            if alive_state is True and self._alive is False:
                self._alive = True

                # Fire each event.
                for event in self._events["on_started"]:
                    event(time.time())

            # If Cmus is no longer running, and it is not already dead.
            if alive_state is False and self._alive is True:
                self._alive = False

                # Fire each event.
                for event in self._events["on_ended"]:
                    event(time.time())


myCmus = Cmus()
myCmus.hook("on_started", lambda timestamp: print(f"Started: {timestamp}"))
myCmus.hook("on_ended", lambda timestamp: print(f"Ended: {timestamp}"))
myCmus.monitor()
