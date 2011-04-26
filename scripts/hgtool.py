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
      "dest": "vcs_revision",
      "default": os.environ.get('HG_REV'),
      "help": "Specify which revision to update to"
     }
    ],[
     ["--branch", "-b"],
     {"action": "store",
      "dest": "vcs_branch",
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
      "dest": "tbox_output",
      "default": bool(os.environ.get('PROPERTIES_FILE')),
      "help": "output TinderboxPrint messages"
     }
    ],[
     ["--no-tbox",],
     {"action": "store_false",
      "dest": "tbox_output",
      "help": "don't output TinderboxPrint messages"
     }
    ],[
     ["--shared-dir", '-s'],
     {"action": "store",
      "dest": "vcs_shared_dir",
      "default": os.environ.get('HG_SHARE_BASE_DIR'),
      "help": "clone to a shared directory"
     }
    ],[
     ["--check-outgoing",],
     {"action": "store_true",
      "dest": "vcs_strip_outgoing",
      "default": False,
      "help": "check for and clobber outgoing changesets"
     }
    ]]

    def __init__(self, require_config_file=False):
        BaseScript.__init__(self, config_options=self.config_options,
                            all_actions=['doit',
                            ],
                            default_actions=['doit',
                            ],
                            usage="usage: %prog [options] repo [dest]",
                            require_config_file=require_config_file)

    def _pre_config_lock(self, rw_config):
        # This is a workaround for legacy compatibility with the original
        # hgtool.py.
        #
        # Since we need to read the buildbot json props, as well as parse
        # additional commandline arguments that aren't specified via
        # options, we call this function before locking the config.
        #
        # rw_config is the BaseConfig object that parsed the options;
        # self.config is the soon-to-be-locked runtime configuration.
        #
        # This is a powerful way to hack the config before locking;
        # we need to be careful not to abuse it.
        args = rw_config.args
        if len(args) not in (1, 2):
            self.fatal("Invalid number of arguments!\n" + rw_config.config_parser.get_usage())
        self.config['vcs_repo'] = args[0]
        if len(args) == 2:
            self.config['vcs_dest'] = args[1]
        else:
            self.config['vcs_dest'] = os.path.basename(self.config['vcs_repo'])

    def doit(self):
        pass

# __main__ {{{1
if __name__ == '__main__':
    hg_tool = HGTool()
    hg_tool.run()
