#!/bin/sh
# From http://www.reddit.com/r/git/comments/hdn1a/howto_using_the_git_ssh_variable_for_private_keys/

if [ "x$GIT_SSH_KEY" != "x" ]; then
    exec ssh -o IdentityFile="$GIT_SSH_KEY" "$@"
else
    exec ssh "$@"
fi
