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
demo_bin="${ZDOTDIR:A}/../.venv/bin"
if [[ ! -x $demo_bin/chrome-agent ]]; then
  print -u2 "Run ${ZDOTDIR:A}/../setup.sh first to build the demo's chrome-agent."
  return 1
fi
path=( "$demo_bin" $path )
# Pin the hash entry as well as the path. Measured: inside a completion widget
# this shell resolved `chrome-agent` to ~/.local/bin (the globally installed
# tool) even with $demo_bin first on $path and `which -a` reporting the demo
# build -- so the completion silently exercised the wrong binary. A real
# install has only one chrome-agent on PATH; pinning reproduces that.
hash -r
hash chrome-agent="$demo_bin/chrome-agent"

source <(chrome-agent completions zsh)

print -P "%F{yellow}chrome-agent completion demo%f -- try:"
print "  chrome-agent <TAB>            commands + live instances"
print "  chrome-agent stop ensor<TAB>  substring match on instance names"
print "  chrome-agent launch --<TAB>   flags"
print "  exit                          leave the demo (your real shell is untouched)"
