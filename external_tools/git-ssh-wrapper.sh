#!/bin/sh -x
# From http://www.reddit.com/r/git/comments/hdn1a/howto_using_the_git_ssh_variable_for_private_keys/

if [ -e "$GIT_SSH_KEY" ]; then
    exec ssh -oIdentityFile="$GIT_SSH_KEY" "$@"
else
    exec ssh "$@"
fi
