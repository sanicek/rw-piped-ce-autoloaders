[h1]Piped CE Autoloaders[/h1]

This project is under development. It provides three color-coded ammunition
pipe networks, each configured with a Combat Extended ammo set and exact round.
Each network also has independent 0.1x-5.0x reload speed and 100-10,000-round
magazine capacity settings. Configuration is validated at startup and remains fixed
until RimWorld restarts. Rebinding an existing network converts its stored pipe
resource and autoloader counts to the newly selected round and updates its input
filters; physical ammunition already on an input remains available to haul away.
Empty magazines before lowering their capacity.
Pipe-backed autoloaders retain native partial-transfer, shortage, and
cancellation behavior while excluding pawn refill, adjacent-turret manual
reload, and CE ammo-management interactions. Ammunition magazines occupy 2x2 cells,
and all network buildings use the compact Ammo Pipes architect category.
Each color also includes a hidden pipe. Hidden pipes take longer and cost more
steel to build, disappear when completed, and cannot be targeted or damaged by
attacks.
Existing 1x2 storage expands to a square 2x2 footprint after updating, so empty
and deconstruct old magazines first or inspect nearby structures after loading.

[h2]Compatibility[/h2]

Targets RimWorld 1.6 and requires Combat Extended and Vanilla Expanded
Framework.

[h2]Source and license[/h2]

Source: [url=https://github.com/sanicek/rw-piped-ce-autoloaders]github.com/sanicek/rw-piped-ce-autoloaders[/url]

License: [url=https://github.com/sanicek/rw-piped-ce-autoloaders/blob/main/LICENSE]MIT License[/url]
