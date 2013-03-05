#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
# ***** END LICENSE BLOCK *****
"""vcs_conversion.py

Currently for hg<->git conversions.
"""

import os
import sys

sys.path.insert(1, os.path.dirname(sys.path[0]))

from mozharness.base.script import BaseScript


# VCSConversionScript {{{1
class VCSConversionScript(BaseScript):
    config_options = [[
        ["--test-file", ],
        {"action": "extend",
         "dest": "test_files",
         "help": "Specify which config files to test"
         }
    ]]

    def __init__(self, require_config_file=False):
        BaseScript.__init__(
            self,
            config_options=self.config_options,
            all_actions=[
                'foo',
            ],
            default_actions=[
                'foo',
            ],
            require_config_file=require_config_file
        )


#g18_branch=b2g18
#g18_v100_branch=b2g18_v1_0_0
#g18_v101_branch=b2g18_v1_0_1
#
## boilerplate
#warn() { for m; do echo "$m"; done 1>&2; }
#die() { warn "$@"; exit 1; }
#usage() { warn "$@" "${USAGE:-}"; test $# -eq 0; exit $?; }
#
#run_cmd() {
#    local -i ec=0
#    # we need a date to correlate detail log with run log
#    echo "$(date $date_fmt): starting: $@" >>$UPDATE_DETAIL_LOG
#    $dry_run timeit "$@" >>$UPDATE_DETAIL_LOG 2>&1 || ec=$?
#    # we don't care if these failed, as that data is already logged
#    return 0
#}
#
#do_update_pass() {
#    for f in default beta b2g18 b2g18_v1_0_0 b2g18_v1_0_1 ; do
#	cur_tip=$(hg id $(hg path $f))
#	run_cmd hg --cwd $PWD pull -r $cur_tip $f
#	# map "well known" hg -> git branch names
#	case "$f" in
#	    default) git_branch="master" ;;
#	    *) git_branch=$f ;;
#	esac
#	# some branches need to be known by both their hg & git names
#	if test $git_branch == $g18_branch; then
#	    git_branch+=" gecko-18"
#	elif test $git_branch == $g18_v100_branch; then
#	    git_branch+=" v1.0.0"
#	elif test $git_branch == $g18_v101_branch; then
#	    git_branch+=" v1.0.1"
#	fi
#	for branch in $git_branch; do
#	    run_cmd hg --cwd $PWD bookmark -f -r $cur_tip $branch
#	done
#    done
#    run_cmd hg --cwd $PWD gexport
#    # we only want to push B2G tags - get the list and create the
#    # commands we need. At this point, we know we have at least one tag
#    tag_refs=$(git tag -l | grep ^B2G | sed 's,^,tag ,')
#
#    timeit git --git-dir $PWD/.git  push github +refs/heads/$g18_branch:refs/heads/gecko-18 \
#                                                +refs/heads/$g18_v100_branch:refs/heads/v1.0.0 \
#                                                +refs/heads/$g18_v101_branch:refs/heads/v1.0.1 \
#                                                +refs/heads/master:refs/heads/master \
#						$tag_refs || page "github push failed: $?"
#    timeit git --git-dir $PWD/.git  push git.m.o +refs/heads/$g18_branch:refs/heads/gecko-18 \
#                                                +refs/heads/$g18_v100_branch:refs/heads/v1.0.0 \
#                                                +refs/heads/$g18_v101_branch:refs/heads/v1.0.1 \
#                                                +refs/heads/master:refs/heads/master \
#						$tag_refs || page "git.m.o push failed: $?"
#
#}
#
#update_gitmapfile() {
#    local tmpDir=/tmp/vcs-sync
#    mkdir -p $tmpDir &>/dev/null && chmod 755 $tmpDir
#    if ! cmp --quiet $tmpDir/git-mapfile .hg/git-mapfile; then
#	cp -f $tmpDir/gecko-mapfile $tmpDir/gecko-mapfile.old &>/dev/null
#	ln -sf gecko-mapfile.old $tmpDir/gecko-latest
#	cp -f .hg/git-mapfile $tmpDir/gecko-mapfile
#	chmod 444 $tmpDir/gecko-mapfile
#	ln -sf gecko-mapfile $tmpDir/gecko-latest
#    fi
#}
#
#cd /opt/vcs2vcs/b2g/mc-cvs-ma-update-test3/ ||
#    die "can't cd to repo dir"
#
###do_update_pass ; exit $?
#while true; do
#    date --iso=min
#    do_update_pass
#    update_gitmapfile
#    sleep 600
#done


# __main__ {{{1
if __name__ == '__main__':
    conversion = VCSConversionScript()
    conversion.run()
