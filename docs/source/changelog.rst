.. Created by changelog.py at 2023-10-04, command
   '/Users/giffler/.cache/pre-commit/repor6pnmwlm/py_env-python3.10/bin/changelog docs/source/changes compile --categories Added Changed Fixed Security Deprecated --output=docs/source/changelog.rst'
   based on the format of 'https://keepachangelog.com/'

#########
CHANGELOG
#########

[Unreleased] - 2023-10-04
=========================

Deprecated
----------

* Minimal Python version is 3.8

Fixed
-----

* Pin TARDIS to use pydantic version 1
* Fix missing `resource_status` attribute crashing Prometheus plugin on newly started drones

[0.7.1] - 2023-05-16
====================

Changed
-------

* Change pyauditor version to 0.1.0

Fixed
-----

* Disable change of drone_uuid after resource deployment in Moab adapter

[0.7.0] - 2023-02-24
====================

Added
-----

* Introduce a TARDIS REST API to query the state of resources from SqlRegistry
* Ensure python3.10 compatibility
* Added support for manual draining of drones using the REST API
* Add support for passing environment variables as executable arguments to support HTCondor grid universe
* Added support for application credentials of the OpenStack site adapter
* Added a new site adapter to use Lancium compute as resource provider

Changed
-------

* Adjust ElasticSearch plugin to support client versions >=7.17,<8.0.0
* Remove granularity in Standardiser to enable earlier creation of new drones
* Introduced Bulk Executor and HTCondor Bulk Operations
* SSHExecutor respects the remote MaxSessions via queueing
* Remove minimum core limit (Standardiser) from pool factory
* Change drone state initialisation and notification of plugins
* REST API cookie authentication and refactoring
* Adjust Prometheus plugin to the latest aioprometheus version 21.9.0

Fixed
-----

* Unique constraints in database schema have been fixed to allow same machine_type and remote_resource_uuid on multiple sites
* Update the remote_resource_uuid in sqlite registry on a each update
* REST API does not suppress KeyboardInterrupt
* Fixing recurrent cancellation of jobs TIMEOUTED in Slurm
* Fixed state transition for stopped workers

[0.6.0] - 2021-08-09
====================

Added
-----

* Added support for Kubernetes horizontal pod autoscaler
* Enable support for `msub` command line options in the Moab site adapter
* An optional and per site configurable drone heartbeat interval has been added
* Added support for executors in batch system adapters
* Added a new site adapter to use Kubernetes clusters as resource provider
* Added TARDIS docker images to matterminers@dockerhub

Fixed
-----

* Fixed pypy support of TARDIS
* Fixes a bug that get_resource_ratios raised a ValueError
* Fixed installation issues on Centos 7
* Fixes a bug that the drone_minimum_lifetime parameter is not working as described in the documentation
* Fixes a bug in the HTCondor Site Adapter which leads to wrong requirements when using non HTCondor OBS

[0.5.0] - 2020-12-09
====================

Added
-----

* Export tardis environment variable via slurm site adapter
* Added support for Slurm overlay batch system

[0.4.0] - 2020-06-03
====================

Added
-----

* Added an example HTCondor jdl for the HTCondor site adapter
* Added a prometheus monitoring plugin
* Enable support for `sbatch` command line options in the Slurm site adapter
* Add ssh connection sharing to `SSHExecutor` in order to re-use existing connection

Changed
-------

* Added log channels and adjusted log levels according to the conventions in `COBalD` documentation
* The Moab adapter can now be configured to use different startup commands for each machine type.
* The SLURM adapter can now be configured to use different startup commands for each machine type.

Fixed
-----

* Fixed the exception handling of `ConnectionResetError` in `SSHExecutor`
* Fixed the resource status translation of the moab site adapter

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
