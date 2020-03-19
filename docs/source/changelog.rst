.. Created by changelog.py at 2020-03-19, command
   '/Users/giffler/.cache/pre-commit/repont7o94ca/py_env-python3.7/bin/changelog docs/source/changes compile --output=docs/source/changelog.rst'
   based on the format of 'https://keepachangelog.com/'

#########
CHANGELOG
#########

[0.3.0] - 2020-02-26
====================

Added
-----

* Add support for Python 3.8
* Register pool factory as `COBalD` yaml plugin
* Add support for COBalD legacy object initialisation
* The machine name has been added as a default tag in the telegraf monitoring plugin, can be overwritten.
* An optional and per site configurable drone minimum lifetime has been added
* Add the possibility to use an unified `COBalD` and `TARDIS` configuration

Fixed
-----

* Fix draining of slots having a startd name
* Fix the translation of cloud init scripts into base64 encoded strings
* Use utilisation as weight in composite pools
* Allow removal of booting drones if demand drops to zero
* The `CleanupState` is now taking into account the status of the resource for state transitions
* Improved logging of the `HTCondor` batch system adapter and the status changes of the drones
* Fix the handling of the termination of vanished resources
* Fix state transitions for jobs retried by HTCondor
* Fix state transitions and refactoring of the SLURM site adapter

[Unreleased] - 2020-03-19
=========================

Changed
-------

* The SLURM adapter can now be configured to use different startup commands for each machine type.
