# Known Socket Commands

Command | Arguments | Description
-- | -- | --
auth | [password] | Authenticate.
error | - | Error message.
exit | - | Exit the command processor
heartbeat | - | Prints an increasing hearbeat count.
log-updates start | - | Enable/diable log updates.
log-updates restart | - | Enable/diable log updates.
log-updates | stop | - | Enable/diable log updates.
quit | - | Exit the command processor
screensaver | - | Unpause all slots which are paused waiting for a screensaver and pause them again on disconnect.
updates add | <id> <rate> <expression> | Add subscription.
updates del | <id> | Delete Subscription.
updates list | - | List all Subscriptions.
updates clear | - | Clear all Subscriptions.
updates reset | - | Reset all Subscriptions.
always_on | [slot] | Set all or one slot(s) always on.
bond | <ip>:<port> <input> [output] [ip:port] | Bond a packet file to a outgoing debug socket connection.
configured | - | Return a PyON message indicating if the client has set a user, team or passkey.
do-cycle | - | Run one client cycle.
download-core | <type> <url> | Download a core.
finish | [slot] | Finish all or one slot(s).
get-info | <category> <key> | Print application information
info | - | Print application information in PyON format
inject | <ip>:<port> <input> [output] [ip:port] | Inject a packet file to a listening debug socket. Will wait until packet is processed.
mask-unit-state | - | Disable specified unit states.
num-slots | - | Get number of slots in PyON format.
on_idle | [slot] | Set all or one slot(s) on idle.
option | <name> [value] | Get or set a configuration option
options | - | See [Options](##Options)
pause | [slot] | Pause all or one slot(s).
ppd | - | Get current total estimated Points Per Day.
queue-info | - | Get work unit queue information in PyON format.
request-id  | - | Request an ID from the assignment server.
request-ws | - | Request work server assignment from the assignmentserver.
save | [file] | Save the configuration either to the specified file or to the file the configuration was last loaded from.
shutdown | - | Shutdown the application
simulation-info | <slot id> | Get current simulation information.
slot-add | <type> [<name>=<value>] | Add a new slot. Configuration options for the new slot can be provided.
slot-delete |<slot> | Delete a slot. If it is running a unit it will be stopped.
slot-info | - | Get slot information in PyON format.
slot-modify | <id> <type> [<name><! / =<value>>] | Modify an existing slot. Configuration options can be either set or reset using the same syntax used by the [Options](##Options) command.
slot-options | <slot> [-d / -a] / [name] | The first argument is the slot ID. See [Options](##Options) help for a description of the remaining arguments. trajectory | <slot id> | Get current protein trajectory.
unpause |[slot] | Unpause all or one slot(s).
uptime | - | Print application uptime
wait-for-units |- | Wait for all running units to finish.

## Options

List or set options with their values. If no name arguments are
given then all options with non-default values will be listed. If the
'-d' argument is given then even defaulted options will be listed.
If the '-a' option is given then unset options will also be listed.
Otherwise, if option names are provided only those options will be listed.
The special name '*' lists all options which have not yet been listed
and is affected by the '-d' and '-a' options. If a name argument is followed
directly by an equal sign then the rest of the arugment will be used to set the
option's value. If instead a name argument is followed immediately by a '!'
then the option will be reset to its default value. Options which are set or
reset will also be listed. Options are listed as a PyON format dictionary.
[-d / -a] / [<name>[! / =<value>]]...