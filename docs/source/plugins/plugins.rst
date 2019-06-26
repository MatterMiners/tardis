=======
Plugins
=======

All plugins are configured within the `plugins` section of the TARDIS configuration. Using multiple plugins are
supported by using a separate MappingNode per plugin.

.. code-block:: yaml

    Plugins:
        Plugin_1:
            option_1: my_option_1
        Plugin_2:
            option_123: my_option_123

Sqlite Registry
---------------
The :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` implements a persistent storage of all Drone states in a
Sqlite database. The usage of this module is recommended in order to recover the last state of TARDIS in case the
service has to be restarted.

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+-----------------------------------+-----------------+
| Option         | Short Description                 | Optionality     |
+================+===================================+=================+
| db_file        | Location of the Sqlite database.  |  **Required**   |
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
of the Drones in a telegraf service running an UDP input module.

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+---------------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                         | Optionality     |
+================+===========================================================================+=================+
| host           | Hostname or IP address of the telegraf UDP input module is listening to.  |  **Required**   |
+----------------+---------------------------------------------------------------------------+-----------------+
| port           | Port the telegraf UDP input module is listening on.                       |  **Required**   |
+----------------+---------------------------------------------------------------------------+-----------------+
| default_tags   | Tags that should included by default for all entries send to telegraf.    |  **Optional**   |
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