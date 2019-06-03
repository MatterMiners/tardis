=======
Plugins
=======

.. code-block:: yaml

    Plugins:
        Plugin_1:
            option_1: my_option_1
        Plugin_2:
            option_123: my_option_123

Sqlite Registry
---------------
:py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry`

.. code-block:: yaml

    Plugins:
      SqliteRegistry:
        db_file: drone_registry.db

Telegraf Monitoring
-------------------
:py:class:`~tardis.plugins.telegrafmonitoring.TelegrafMonitoring`

.. code-block:: yaml

    Plugins:
      TelegrafMonitoring:
        host: der_telegraf.foo.bar
        port: 8092

Your favorite monitoring is currently not supported?
Please, have a look at
:ref:`how to contribute.<ref_contribute_plugin>`