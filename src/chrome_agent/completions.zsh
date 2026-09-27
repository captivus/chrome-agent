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
    'save:Snapshot sessions (profile, tabs, cookies) to restore later'
    'restore:Bring saved sessions back, same name and port'
    'snapshots:List, inspect and delete saved snapshots'
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

# CDP methods and events come from the browser's own /json/protocol, so they
# describe the protocol THIS Chrome implements rather than a list bundled with
# chrome-agent. ~7 ms for the whole schema, so there is nothing to cache.
# $_chrome_agent_instance is set by _chrome-agent when the line names one;
# without it any live instance answers, the schema being identical across them.
_chrome_agent_methods() {
  local -a methods
  methods=( ${(f)"$(_call_program chrome-agent-methods chrome-agent completions methods ${_chrome_agent_instance:-} 2>/dev/null)"} )
  (( $#methods )) || return 1
  _describe -t methods 'CDP method' methods
}

_chrome_agent_events() {
  local -a events
  events=( ${(f)"$(_call_program chrome-agent-events chrome-agent completions events ${_chrome_agent_instance:-} 2>/dev/null)"} )
  (( $#events )) || return 1
  # attach subscribes with a leading +, which is part of the word being
  # completed -- prefix it so the inserted candidate is usable as typed.
  _describe -t events 'event to subscribe to' events -P '+'
}

# Saved snapshot names, read from the store's plaintext summaries (no key needed).
_chrome_agent_snapshots() {
  local -a snaps
  snaps=( ${(f)"$(_call_program chrome-agent-snapshots chrome-agent completions snapshots 2>/dev/null)"} )
  (( $#snaps )) || return 1
  _describe -t snapshots 'snapshot' snaps
}

_chrome_agent_first() {
  _alternative \
    'commands:command:_chrome_agent_commands' \
    'instances:instance:_chrome_agent_instances'
}

_chrome-agent() {
  local context state state_descr line ret=1
  local _chrome_agent_instance          # read by the method/event helpers
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
      _chrome_agent_instance=$words[2]
      _arguments $target_specs \
        '1:instance:_chrome_agent_instances' \
        '*:event:_chrome_agent_events' && ret=0
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
        'methods:Print Domain.method names from the running browser'
        'events:Print Domain.event names from the running browser'
      )
      _describe -t what 'what to print' what && ret=0
      ;;
    cleanup)
      ret=0
      ;;
    save)
      _arguments \
        '(*)--all[Save every running instance, as a batch restore --all brings back]' \
        '--stop[Close the browser cleanly first, for a fully consistent copy]' \
        '--as[Save under this snapshot name]:name:' \
        '(--keep-both)--overwrite[Replace the latest existing version without asking]' \
        '(--overwrite)--keep-both[Keep the existing version too, without asking]' \
        '*:instance:_chrome_agent_instances' && ret=0
      ;;
    restore)
      _arguments \
        '(*)--all[Restore the last save --all batch]' \
        '--here[Only snapshots launched from this directory]' \
        '--any-port[Use a new port if the saved one is taken]' \
        '--no-reattach[Do not restart file-backed attach observers]' \
        '--replace-profile[Move an existing custom profile dir aside]' \
        '--start-display[Start the virtual X display (Xvfb) a snapshot ran on, if it is not running]' \
        '--desktop[Place windows on their saved desktops or this terminal'"'"'s]:mode:(saved terminal)' \
        '*:snapshot:_chrome_agent_snapshots' && ret=0
      ;;
    snapshots)
      if (( CURRENT == 2 )); then
        local -a subs
        subs=(
          'list:List saved snapshots (default)'
          'show:Show a snapshot'"'"'s tabs, observers and launch settings'
          'rm:Delete snapshot versions'
          'export-key:Print the encryption key, for backup'
          'import-key:Store a backed-up key (read from stdin)'
        )
        _describe -t subcommands 'subcommand' subs && ret=0
      else
        case $words[2] in
          show) _arguments '1:snapshot:_chrome_agent_snapshots' && ret=0 ;;
          rm)
            _arguments \
              '--older-than[Only versions older than this age]:age (e.g. 30d):' \
              '(-y --yes)'{-y,--yes}'[Do not ask for confirmation]' \
              '*:snapshot:_chrome_agent_snapshots' && ret=0
            ;;
          import-key) _arguments '--replace[Overwrite a different stored key]' && ret=0 ;;
        esac
      fi
      ;;
    *)
      # The first word was an instance name, so this is the one-shot form:
      #   chrome-agent <instance> Domain.method '{"param": "value"}'
      _chrome_agent_instance=$words[1]
      _arguments $target_specs \
        '1:CDP method:_chrome_agent_methods' \
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
