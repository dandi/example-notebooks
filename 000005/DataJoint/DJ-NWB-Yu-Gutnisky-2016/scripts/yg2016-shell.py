#! /usr/bin/env python3

import os
import sys
import logging


from code import interact

# BOOKMARK: ensure loading
from pipeline import reference
from pipeline import subject
from pipeline import action
from pipeline import acquisition
from pipeline import behavior
from pipeline import ephys


log = logging.getLogger(__name__)
__all__ = [reference, subject, action, acquisition, behavior, ephys]


def usage_exit():
    print("usage: {p} [{c}]"
          .format(p=os.path.basename(sys.argv[0]),
                  c='|'.join(list(actions.keys()))))
    sys.exit(0)


def logsetup(*args):
    logging.basicConfig(level=logging.ERROR)
    log.setLevel(logging.DEBUG)
    logging.getLogger('pipeline').setLevel(logging.DEBUG)


def shell(*args):
    interact('gao2018 shell.\n\nschema modules:\n\n  - {m}\n'
             .format(m='\n  - '.join(
                 '.'.join(m.__name__.split('.')[1:]) for m in __all__)),
             local=globals())



actions = {
    'shell': shell,
}


if __name__ == '__main__':

    if len(sys.argv) < 2 or sys.argv[1] not in actions:
        usage_exit()

    logsetup()

    action = sys.argv[1]
    actions[action](sys.argv[2:])
