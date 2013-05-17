#!/bin/sh -x
# From http://www.reddit.com/r/git/comments/hdn1a/howto_using_the_git_ssh_variable_for_private_keys/

p=`echo "$GIT_SSH_KEY"`

if [ -e "$p" ]; then
    exec ssh -o IdentityFile="$GIT_SSH_KEY" "$@"
else
    exec ssh "$@"
fi
