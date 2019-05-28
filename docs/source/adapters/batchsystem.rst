=====================
Batch System Adapters
=====================

Fake Batch System Adapter
-------------------------

Bla
:py:class:`~tardis.adapters.batchsystems.fakebatchsystem.FakeBatchSystemAdapter`

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
            pool: cloud-htcondor.gridka.de

Your favorite batch system is currently not supported?
Please, have a look at
:ref:`how to contribute.<ref_contribute_batch_system_adapter>`