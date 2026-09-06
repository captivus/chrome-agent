# Demo shell for the chrome-agent zsh completion.
#
# Faithful mirror, not a stand-in: it sources the REAL ~/.zshrc, so compinit,
# matcher-list, carapace and fzf-tab are exactly the user's own stack. The only
# additions are (a) a PATH shim so `chrome-agent` is the working-tree build and
# (b) the completion itself, registered the same way `source <(...)` would in a
# real .zshrc -- i.e. after compinit, via compdef.

source "$HOME/.zshrc"

# $0 is "zsh" inside a ZDOTDIR .zshrc, not this file's path -- $ZDOTDIR is
# the only reliable handle on where this rc lives.
path=( "${ZDOTDIR:A}/../demo-bin" $path )

source <(chrome-agent completions zsh)

print -P "%F{yellow}chrome-agent completion demo%f -- try:"
print "  chrome-agent <TAB>            commands + live instances"
print "  chrome-agent stop ensor<TAB>  substring match on instance names"
print "  chrome-agent launch --<TAB>   flags"
print "  exit                          leave the demo (your real shell is untouched)"
