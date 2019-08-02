=======
Plugins
=======

All plugins are configured within the `plugins` section of the TARDIS configuration. Using multiple plugins is
supported by using a separate MappingNode per plugin.

.. code-block:: yaml

    Plugins:
        Plugin_1:
            option_1: my_option_1
        Plugin_2:
            option_123: my_option_123

SQLite Registry
---------------
The :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` implements a persistent storage of all Drone states in a
SQLite database. The usage of this module is recommended in order to recover the last state of TARDIS in case the
service has to be restarted.

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+-----------------------------------+-----------------+
| Option         | Short Description                 | Requirement     |
+================+===================================+=================+
| db_file        | Location of the SQLite database.  |  **Required**   |
+----------------+-----------------------------------+-----------------+

Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Plugins:
      SqliteRegistry:
        db_file: drone_registry.db

Telegraf Monitoring
-------------------
The :py:class:`~tardis.plugins.telegrafmonitoring.TelegrafMonitoring` implements an interface to monitor state changes
of the Drones in a telegraf service running a UDP input module.

.. Note::
    By default the machine name of the host running tardis is added as default tag. It can be overwritten by adding
    `tardis_machine_name: 'something_else'` as `default_tag` in the configuration.

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+---------------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                         | Requirement     |
+================+===========================================================================+=================+
| host           | Hostname or IP address the telegraf UDP input module is listening to.     |  **Required**   |
+----------------+---------------------------------------------------------------------------+-----------------+
| port           | Port the telegraf UDP input module is listening on.                       |  **Required**   |
+----------------+---------------------------------------------------------------------------+-----------------+
| default_tags   | Tags that should be included by default for all entries sent to telegraf. |  **Optional**   |
+----------------+---------------------------------------------------------------------------+-----------------+

Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Plugins:
      TelegrafMonitoring:
        host: der_telegraf.foo.bar
        port: 8092
        default_tags:
          something_default: 'The Default Tag'

Your favorite monitoring is currently not supported?
Please, have a look at
:ref:`how to contribute.<ref_contribute_plugin>`
