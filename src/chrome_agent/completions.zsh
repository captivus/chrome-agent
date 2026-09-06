#compdef chrome-agent

# zsh completion for chrome-agent.
#
# Printed by `chrome-agent completions zsh`. Install it where compinit will find
# it -- a directory on $fpath, with the file named _chrome-agent:
#
#   mkdir -p ~/.config/zsh/completions
#   chrome-agent completions zsh > ~/.config/zsh/completions/_chrome-agent
#
# or source it from .zshrc AFTER compinit:
#
#   source <(chrome-agent completions zsh)
#
# Instance names are read from the registry on every Tab (via
# `chrome-agent completions instances`), so they track what is actually
# running rather than a list captured at install time.

_chrome_agent_commands() {
  local -a commands
  commands=(
    'launch:Launch a Chrome instance with CDP enabled'
    'status:List instances and their tabs'
    'attach:Hold a connection and stream CDP events'
    'stop:Stop a browser, or close one of its tabs'
    'help:Query the running browser for its protocol schema'
    'cleanup:Drop dead instances and stale session directories'
    'guide:Print the bundled agent guide'
    'completions:Print shell completions, or the data behind them'
  )
  _describe -t commands 'command' commands
}

_chrome_agent_instances() {
  local -a instances
  instances=( ${(f)"$(_call_program chrome-agent-instances chrome-agent completions instances 2>/dev/null)"} )
  (( $#instances )) || return 1
  _describe -t instances 'instance' instances
}

_chrome_agent_first() {
  _alternative \
    'commands:command:_chrome_agent_commands' \
    'instances:instance:_chrome_agent_instances'
}

_chrome-agent() {
  local context state state_descr line ret=1
  typeset -A opt_args

  # The four target selectors are mutually exclusive -- the CLI errors if more
  # than one is given -- so each excludes the other three.
  local -a target_specs
  target_specs=(
    '(--target-id --target-index --url)--target[Tab index when fewer than 8 digits, else a target-id prefix]:spec:'
    '(--target --target-index --url)--target-id[Target-id prefix, as shown by status]:id:'
    '(--target --target-id --url)--target-index[1-based tab index, as shown by status]:index:'
    '(--target --target-id --target-index)--url[The tab whose URL contains this substring]:substring:'
  )

  _arguments -C \
    '(- *)'{-V,--version}'[Print the installed version and exit]' \
    '(- *)'{-h,--help}'[Show usage and exit]' \
    '1: :_chrome_agent_first' \
    '*:: :->rest' && ret=0

  [[ $state == rest ]] || return ret

  case $words[1] in
    launch)
      _arguments \
        '--port[Use this CDP port instead of an auto-allocated one]:port:' \
        '--headless[Run with no window]' \
        '--fingerprint[Spoof UA, viewport, language and timezone from a profile]:profile:_files -g "*.json"' \
        '--no-window-border[Suppress the agent window marker]' \
        '*:chrome flag (after --):' && ret=0
      ;;
    status)
      _arguments '1:instance:_chrome_agent_instances' && ret=0
      ;;
    stop)
      _arguments $target_specs '1:instance:_chrome_agent_instances' && ret=0
      ;;
    attach)
      _arguments $target_specs \
        '1:instance:_chrome_agent_instances' \
        '*:event to subscribe to (+Domain.event):' && ret=0
      ;;
    help)
      _arguments '1:instance or Domain:_chrome_agent_instances' && ret=0
      ;;
    guide)
      _arguments '--path[Print the guide file path instead of its contents]' && ret=0
      ;;
    completions)
      local -a what
      what=(
        'zsh:Print this completion function'
        'instances:Print instance names and descriptions, one per line'
      )
      _describe -t what 'what to print' what && ret=0
      ;;
    cleanup)
      ret=0
      ;;
    *)
      # The first word was an instance name, so this is the one-shot form:
      #   chrome-agent <instance> Domain.method '{"param": "value"}'
      _arguments $target_specs \
        '1:CDP method (Domain.method):' \
        '2:JSON parameters:' && ret=0
      ;;
  esac

  return ret
}

# Works both ways: autoloaded from $fpath by compinit, or sourced directly.
if [[ $funcstack[1] == _chrome-agent ]]; then
  _chrome-agent "$@"
else
  compdef _chrome-agent chrome-agent
fi
