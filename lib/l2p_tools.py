import os
import sys
import re
import urllib.error
import urllib.parse
import urllib.request
from functools import update_wrapper


def clean_exit(exit_code=0):
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(exit_code)


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
            if hasattr(e, 'message'):
                print("Error in function {}: {}".format(f.__name__, e.message))
            elif hasattr(e, 'reason'):
                print("Error in function {}: {}".format(f.__name__, e.reason))
            else:
                print("Error in function {}: {}".format(f.__name__, str(e)))
            return False
    return update_wrapper(wrapper_func, f)


def get_version_str():
    return '0.6.2'
