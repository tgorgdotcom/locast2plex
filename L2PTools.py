import os
import sys
import re
from functools import update_wrapper
import urllib.error
import urllib.parse
import urllib.request


def clean_exit():
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(0)


# from https://stackoverflow.com/a/43880536
def is_docker():
    path = "/proc/self/cgroup"
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        for line in f:
            if re.match("\d+:[\w=]+:/docker(-[ce]e)?/\w+", line):
                return True
        return False


def handle_url_except(f):
    def wrapper_func(self, *args, **kwargs):
        try:
            return f(self, *args, **kwargs)
        except urllib.error.URLError as urlError:
            print("Error in function {}: {}".format(f.__name__, str(urlError.reason)))
            return False
        except urllib.error.HTTPError as httpError:
            print("Error in function {}: {}".format(f.__name__, str(httpError.reason)))
            return False
        except Exception as e:
            print("Error in function {}: {}".format(f.__name__, e.message or e.reason))
            return False
    return update_wrapper(wrapper_func, f)
