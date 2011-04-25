#!/usr/bin/env python
"""hgtool.py

Port of tools/buildfarm/utils/hgtool.py.
"""

import os
import pprint
import sys
try:
    import simplejson as json
except ImportError:
    import json

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import BaseScript
from mozharness.base.vcs.mercurial import MercurialMixin

# HGTool {{{1
class HGTool(MercurialMixin, BaseScript):
    # These options were chosen with an eye towards backwards
    # compatibility with the existing hgtool.
    config_options = [[
     ["--rev", "-r"],
     {"action": "store",
      "dest": "revision",
      "default": os.environ.get('HG_REV'),
      "help": "Specify which revision to update to"
     }
    ],[
     ["--branch", "-b"],
     {"action": "store",
      "dest": "branch",
      "default": os.environ.get('HG_BRANCH', 'default'),
      "help": "Specify which branch to update to"
     }
    ],[
     ["--props-file", "-p"],
     {"action": "store",
      "dest": "propsfile",
      "default": os.environ.get('PROPERTIES_FILE'),
      "help": "build json file containing revision information"
     }
    ],[
     ["--tbox",],
     {"action": "store_true",
      "dest": "tbox",
      "default": bool(os.environ.get('PROPERTIES_FILE')),
      "help": "output TinderboxPrint messages"
     }
    ],[
     ["--no-tbox",],
     {"action": "store_false",
      "dest": "tbox",
      "help": "don't output TinderboxPrint messages"
     }
    ],[
     ["--shared-dir", '-s'],
     {"action": "store",
      "dest": "shared_dir",
      "default": os.environ.get('HG_SHARE_BASE_DIR'),
      "help": "clone to a shared directory"
     }
    ],[
     ["--check-outgoing",],
     {"action": "store_true",
      "dest": "outgoing",
      "default": False,
      "help": "check for and clobber outgoing changesets"
     }
    ]]

    def __init__(self, require_config_file=False):
        self.config_files = []
        BaseScript.__init__(self, config_options=self.config_options,
                            all_actions=['doit',
                            ],
                            default_actions=['doit',
                            ],
                            require_config_file=require_config_file)

    def doit(self):
        pass

# __main__ {{{1
if __name__ == '__main__':
    hg_tool = HGTool()
    hg_tool.run()
