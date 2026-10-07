#!/bin/sh
# Load shell-only credentials without taking the agent host's foreground TTY.
if [ "$#" -eq 0 ]; then
    echo 'Usage: sh with_zsh_env.sh COMMAND [ARG ...]' >&2
    exit 2
fi

# Keep startup output off the command's stdout (which may carry MCP JSON).
exec 3>&1
exec 1>&2
exec zsh +m -ic 'exec "$@" 1>&3 3>&-' codemagic-zsh-env "$@"
