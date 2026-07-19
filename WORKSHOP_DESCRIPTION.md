[h1]Piped CE Autoloaders[/h1]

Move Combat Extended ammunition through Vanilla Expanded Framework pipe
networks and into powered autoloaders that retain CE's native turret reload
behavior.

[h2]Features[/h2]

[list]
[*]Three independent Amber, Blue, and Green ammunition networks
[*]Exact CE ammo-set and physical-round binding under Mod Settings
[*]Per-network 0.1x-5.0x reload speed and 100-10,000-round magazine capacity
[*]Powered autoloaders with native partial reload, shortage, and cancellation behavior
[*]Normal and hidden pipes connected to the same network
[*]Simplified Chinese, French, German, Russian, and Spanish translations
[/list]

[h2]Requirements[/h2]

Targets RimWorld 1.6 and requires:

[list]
[*][url=https://steamcommunity.com/sharedfiles/filedetails/?id=2890901044]Combat Extended[/url]
[*][url=https://steamcommunity.com/workshop/filedetails/?id=2023507013]Vanilla Expanded Framework[/url]
[/list]

Use RimWorld's automatic mod sorting before starting the game.

[h2]Configuration[/h2]

Each network selects one CE ammo set and one exact physical round. Bindings,
reload speeds, and magazine capacities apply after restart and remain fixed for
that session. Invalid or duplicate round assignments disable only the affected
network.

[h2]Existing colonies[/h2]

Rebinding changes existing stored pipe resource and autoloader counts to the
newly selected round after restart. Physical ammunition already on an input
remains available to haul away.

[b]Empty magazines before lowering their configured capacity.[/b] VEF may
discard rounds above the reduced capacity during loading or serialization.

[h2]Problems and logs[/h2]

Reports can be left in the Workshop comments or opened as a
[url=https://github.com/sanicek/rw-piped-ce-autoloaders/issues]GitHub issue[/url].
Please include the RimWorld, CE, VEF, and mod versions; reproduction steps; mod
list and load order; and a link to the relevant Player.log. Link the log through
a paste or file-sharing service rather than posting the entire file in a comment.

[h2]Source, license, and AI assistance[/h2]

Source and manual releases:
[url=https://github.com/sanicek/rw-piped-ce-autoloaders]github.com/sanicek/rw-piped-ce-autoloaders[/url]

License:
[url=https://github.com/sanicek/rw-piped-ce-autoloaders/blob/main/LICENSE]MIT License[/url]

The preview incorporates Combat Extended's official third-party compatibility
badge under
[url=https://creativecommons.org/licenses/by-nc-sa/4.0/]CC BY-NC-SA 4.0[/url].

Parts of the code, documentation, artwork, and maintenance used AI-tool
assistance. Published changes are reviewed and tested by the maintainer.
