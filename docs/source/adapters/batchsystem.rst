.. _ref_batch_system_adapter:

=====================
Batch System Adapters
=====================

Fake Batch System Adapter
-------------------------

.. |FakeBatchSystemAdapter.get_utilization| replace:: :py:meth:`~tardis.adapters.batchsystems.fakebatchsystem.FakeBatchSystemAdapter.get_utilization`

.. |FakeBatchSystemAdapter.get_allocation| replace:: :py:meth:`~tardis.adapters.batchsystems.fakebatchsystem.FakeBatchSystemAdapter.get_allocation`

.. |FakeBatchSystemAdapter.get_machine_status| replace:: :py:meth:`~tardis.adapters.batchsystems.fakebatchsystem.FakeBatchSystemAdapter.get_machine_status`

The :py:class:`~tardis.adapters.batchsystems.fakebatchsystem.FakeBatchSystemAdapter`
implements a batch system adapter that mocks the response of hypothetical batch system.
It can be used for testing purposes and as a demonstrator in workshops and tutorials.

The mocked response to the |FakeBatchSystemAdapter.get_allocation|, |FakeBatchSystemAdapter.get_utilization| and
|FakeBatchSystemAdapter.get_machine_status| API calls is configurable statically in the adapter configuration.

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+---------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                   | Requirement     |
+================+=====================================================================+=================+
| adapter        | Name of the adapter (FakeBatchSystem)                               |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| allocation     | Mocked response to |FakeBatchSystemAdapter.get_allocation| call     |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| utilization    | Mocked response to |FakeBatchSystemAdapter.get_utilization| call    |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| machine_status | Mocked response to |FakeBatchSystemAdapter.get_machine_status| call |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+

Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    BatchSystem:
        adapter: FakeBatchSystem
        allocation: 1.0
        utilization: 1.0
        machine_status: Available

HTCondor Batch System Adapter
-----------------------------
.. |HTCondorAdapter.get_utilization| replace:: :py:meth:`~tardis.adapters.batchsystems.htcondor.HTCondorAdapter.get_utilization`

.. |HTCondorAdapter.get_allocation| replace:: :py:meth:`~tardis.adapters.batchsystems.htcondor.HTCondorAdapter.get_allocation`

.. |HTCondorAdapter.get_machine_status| replace:: :py:meth:`~tardis.adapters.batchsystems.htcondor.HTCondorAdapter.get_machine_status`

The :py:class:`~tardis.adapters.batchsystems.htcondor.HTCondorAdapter` implements the TARDIS interface to dynamically
integrate and manage opportunistic resources with the HTCondor batch system.

Information provider for the API calls |HTCondorAdapter.get_utilization|, |HTCondorAdapter.get_allocation| and
|HTCondorAdapter.get_machine_status| is the HTCondor ``condor_status`` command, which is called asynchronously and its
output is cached for a configurable time ``max_age``.

|HTCondorAdapter.get_machine_status| returns the status of the worker node by taking into account the HTCondor
ClassAds ``State`` and ``Activity``. It can take the states ``Available``, ``Draining``, ``Drained`` and
``NotAvailable``.

The allocation and utilization of a worker node is defined as maximum and minimum of the relative ratio of requested
over total resources such as CPU, Memory, Disk, respectively. Which resource ratios to take into account can be
configured via the ``ratios`` option. Any valid HTCondor expression that returns a floating point number is accepted.

Additional options for the condor_status call can be added by using the ``options`` option.

For example

.. code-block:: yaml

    options:
      pool: htcondor.example

translates into ``condor_status ... -pool htcondor.example``.

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+-------------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                       | Requirement     |
+================+=========================================================================+=================+
| adapter        | Name of the adapter (HTCondor)                                          |  **Required**   |
+----------------+-------------------------------------------------------------------------+-----------------+
| max_age        | Maximum age of the cached ``condor_status`` information in minutes      |  **Required**   |
+----------------+-------------------------------------------------------------------------+-----------------+
| ratios         | HTCondor expressions used to determine allocation and utilization       |  **Required**   |
+----------------+-------------------------------------------------------------------------+-----------------+
| options        | Additional command line options to add to the ``condor_status`` command |  **Optional**   |
+----------------+-------------------------------------------------------------------------+-----------------+


Example configuration
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    BatchSystem:
        adapter: HTCondor
        max_age: 1
        ratios:
            cpu_ratio: Real(TotalSlotCpus-Cpus)/TotalSlotCpus
            memory_ratio: Real(TotalSlotMemory-Memory)/TotalSlotMemory
        options:
            pool: my-htcondor.mysite.mydomain

Your favorite batch system is currently not supported?
Please, have a look at
:ref:`how to contribute.<ref_contribute_batch_system_adapter>`
