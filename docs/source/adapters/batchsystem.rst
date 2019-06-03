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
It can be used for testing purposes as well as a demonstrator in workshops and tutorials.

The mocked response to the |FakeBatchSystemAdapter.get_allocation|, |FakeBatchSystemAdapter.get_utilization| and
|FakeBatchSystemAdapter.get_machine_status| API calls is configurable statically.

**Available configuration options:**

+----------------+---------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                   | Optionality     |
+================+=====================================================================+=================+
| adapter        | Name of the adapter (FakeBatchSystem)                               |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| allocation     | Mocked response to |FakeBatchSystemAdapter.get_allocation| call     |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| utilization    | Mocked response to |FakeBatchSystemAdapter.get_utilization| call    |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| machine_status | Mocked response to |FakeBatchSystemAdapter.get_machine_status| call |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+

**Example configuration:**

.. code-block:: yaml

    BatchSystem:
        adapter: FakeBatchSystem
        allocation: 1.0
        utilization: 1.0
        machine_status: Available

HTCondor Batch System Adapter
-----------------------------

Blubb
:py:class:`~tardis.adapters.batchsystems.htcondor.HTCondorAdapter`

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