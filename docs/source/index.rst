======================================================================
TARDIS - The Transparent Adaptive Resource Dynamic Integration System
======================================================================

Welcome to the TARDIS documentation!
====================================

.. toctree::
   :hidden:
   :maxdepth: 2
   :caption: Contents:

   adapters/batchsystem
   adapters/site
   executors/executors
   plugins/plugins
   services/services
   CONTRIBUTING.md
   changelog
   Module Index <api/modules>

.. container:: left-col

    .. image:: ../pics/TARDIS_logo.svg
        :alt: TARDIS Logo
        :height: 150
        :align: left

    The ``TARDIS`` resource manager enables the dynamic integration of resources provided by different
    :ref:`resource providers<ref_site_adapter>` into one :ref:`overlaybatch system<ref_batch_system_adapter>`.
    ``TARDIS`` relies on `COBalD - the Opportunistic Balancing Daemon <https://cobald.readthedocs.io/en/stable>`_ in order
    to balance opportunistic resources. Hence, ``TARDIS`` is implemented as a ``COBalD`` service.

Installation
============

.. content-tabs:: left-col

    The ``TARDIS`` resource manager is available via `PyPI <https://pypi.org/project/cobald-tardis/>`_, so you can use
    `pip` to install ``TARDIS`` and all its dependencies.

.. code-block::

    python3 -m pip install cobald-tardis

Configuration of COBalD
=======================

.. content-tabs:: left-col

    In order to run ``TARDIS`` a ``COBalD`` configuration is needed. Details about the available options and syntax can
    be found in the `COBalD component configuration
    <https://cobald.readthedocs.io/en/stable/source/daemon/config.html#component-configuration>`_ documentation.

    The `pools <https://cobald.readthedocs.io/en/stable/source/model/overview.html#resource-and-control-model>`_ to be
    managed by ``TARDIS`` are created by a factory function
    :py:func:`~tardis.resources.poolfactory.create_composite_pool`, which is registered as a
    `COBalD YAML plugin <https://cobald.readthedocs.io/en/latest/source/custom/package.html#configuration-plugins>`_
    and, therefore, can be included using the ``!TardisPoolFactory`` YAML tag.

.. content-tabs:: right-col

    .. rubric:: Example configuration
    .. code-block:: yaml

        pipeline:
          # Makes decision to add remove resources based utilisation and allocation
          - !LinearController
            low_utilisation: 0.90
            high_allocation: 0.90
            rate: 1
          # Limits the demand for a resource
          - !Limiter
            minimum: 1
          # Log changes
          - !Logger
            name: 'changes'
          # Factory function to create composite resource pool
          - !TardisPoolFactory
            configuration: 'tardis.yml'

Configuration of TARDIS
=======================
.. content-tabs:: left-col

    In addition to the above mentioned ``COBalD`` configuration a ``TARDIS`` configuration is necessary as well,
    which is provided to the factory function :py:func:`~tardis.resources.poolfactory.create_composite_pool` via
    its `configuration` parameter.

    The ``TARDIS`` YAML configuration supports the following sections:

    +----------------+---------------------------------------------------------------------------------------------------------------------+-----------------+
    | Section        | Short Description                                                                                                   | Requirement     |
    +================+=====================================================================================================================+=================+
    | Plugins        | Configuration of the Plugins to use (see :ref:`Plugins<ref_plugins>`)                                               |  **Optional**   |
    +----------------+---------------------------------------------------------------------------------------------------------------------+-----------------+
    | BatchSystem    | The overlay batch system to use (see :ref:`BatchSystemAdapter<ref_batch_system_adapter>`)                           |  **Required**   |
    +----------------+---------------------------------------------------------------------------------------------------------------------+-----------------+
    | Sites          | List of sites to create (see :ref:`Generic Site Configuration<ref_generic_site_adapter_configuration>`)             |  **Required**   |
    +----------------+---------------------------------------------------------------------------------------------------------------------+-----------------+
    | Site Sections  | Configuration options for each site (see :ref:`Generic Site Configuration<ref_generic_site_adapter_configuration>`) |  **Required**   |
    +----------------+---------------------------------------------------------------------------------------------------------------------+-----------------+

.. content-tabs:: right-col

    .. rubric:: Example configuration
    .. code-block:: yaml

        Plugins:
          SqliteRegistry:
            db_file: drone_registry.db

        BatchSystem:
          adapter: FakeBatchSystem
          allocation: 1.0
          utilisation: !TardisPeriodicValue
                       period: 3600
                       amplitude: 0.5
                       offset: 0.5
                       phase: 0.
          machine_status: Available

        Sites:
          - name: Fake
            adapter: FakeSite
            quota: 8000 # CPU core quota

        Fake:
          api_response_delay: !TardisRandomGauss
                              mu: 0.1
                              sigma: 0.01
          resource_boot_time: !TardisRandomGauss
                              mu: 60
                              sigma: 10
          MachineTypes:
            - m1.infinity
          MachineTypeConfiguration:
            m1.infinity:
          MachineMetaData:
            m1.infinity:
              Cores: 8
              Memory: 16
              Disk: 160

Unified Configuration
=====================

.. content-tabs:: left-col

    Alternatively a unified ``COBalD`` and ``TARDIS`` configuration can be used. In this case, the ``TARDIS``
    part of the configuration is represented by a ``tardis`` MappingNode.

    .. warning::
        In case of the unified configuration you can currently not use the yaml tag ``!TardisPoolFactory`` to initialize
        the pool factory, please use the `COBalD` legacy object initialisation
        ``__type__: tardis.resources.poolfactory.create_composite_pool`` instead!

.. content-tabs:: right-col

    .. rubric:: Example configuration
    .. code-block:: yaml

        pipeline:
          # Makes decision to add remove resources based utilisation and allocation
          - !LinearController
            low_utilisation: 0.90
            high_allocation: 0.90
            rate: 1
          # Limits the demand for a resource
          - !Limiter
            minimum: 1
          # Log changes
          - !Logger
            name: 'changes'
          # Factory function to create composite resource pool
          - __type__: tardis.resources.poolfactory.create_composite_pool
        tardis:
            Plugins:
              SqliteRegistry:
                db_file: drone_registry.db

            BatchSystem:
              adapter: FakeBatchSystem
              allocation: 1.0
              utilization: !TardisPeriodicValue
                           period: 3600
                           amplitude: 0.5
                           offset: 0.5
                           phase: 0.
              machine_status: Available

            Sites:
              - name: Fake
                adapter: FakeSite
                quota: 8000 # CPU core quota

            Fake:
              api_response_delay: !TardisRandomGauss
                                  mu: 0.1
                                  sigma: 0.01
              resource_boot_time: !TardisRandomGauss
                                  mu: 60
                                  sigma: 10
              MachineTypes:
                - m1.infinity
              MachineTypeConfiguration:
                m1.infinity:
              MachineMetaData:
                m1.infinity:
                  Cores: 8
                  Memory: 16
                  Disk: 160

Start-up your instance
======================

.. content-tabs:: left-col

    To start-up your instance you can run the following command:

.. code-block::

    python3 -m cobald.daemon cobald.yml

.. content-tabs:: left-col

    However, it is recommended to start ``COBalD`` using systemd as decribed in the
    `COBalD Systemd Configuration <https://cobald.readthedocs.io/en/stable/source/daemon/systemd.html>`_ documentation.

Running your instance in Docker
===============================

.. content-tabs:: left-col

    For your convenience and to try out ``COBalD``/``TARDIS`` ready to use docker containers are provided via Dockerhub.
    To start a demo setup managing fake resources and a fake batch system simply run the following command.

.. content-tabs:: right-col

    .. code-block::

        docker run matterminers/cobald-tardis:latest

.. content-tabs:: left-col

    To run your own ``COBalD``/``TARDIS`` configuration you can run the following command.

.. content-tabs:: right-col

    .. code-block::

        docker run --mount type=bind,source=</your_path/cobald.yml>,target=/srv/cobald.yml matterminers/cobald-tardis:latest

.. content-tabs:: left-col

    To use the Sqlite Database to persistently store the state of your resources you can export an entire path to the
    container by running the following command.

.. content-tabs:: right-col

    .. code-block::

        docker run -v </your_path>:/srv matterminers/cobald-tardis:latest

.. content-tabs:: left-col

    .. note::

        This path must contain a valid `cobald.yml` file. The persistent database will then be stored on the local machine.

Running your instance using HTCondor as overlay batch system in Docker
======================================================================

.. content-tabs:: left-col

    For your convenience and for systems without pre-compiled HTCondor support a ready to use docker container is
    provided via Dockerhub.

    You can configure ``COBalD``/``TARDIS`` as described in this documentation and bind mount the directory containing
    the configuration into the containers `/srv` directory.

    .. note::

        This path must contain at least a valid `cobald.yml` file.

.. content-tabs:: right-col

    .. code-block::

        docker run -v $PWD/configuration:/srv matterminers/cobald-tardis-htcondor:latest


HTCondor Token Support
----------------------

.. content-tabs:: left-col

    Starting with the production release series 9.0, HTCondor introduces a new security configuration, which is no
    longer host-based. The security configuration is now user-based and requires authentication to access the HTCondor
    pool. This is also true for read-only operations such as `condor_status`. Therefore, this docker image
    supports the `IDTOKENS` authentication method introduced with the HTCondor 9.0 series.

    In order to use ID tokens, add any tokens provided by the operator of the overlay batch system to a `tokens.d`
    directory and bind mount it to `/etc/condor/tokens.d`. HTCondor is automatically using them to authenticate against
    the pool.

.. content-tabs:: right-col

    .. code-block::

        docker run -v $PWD/configuration:/srv -v $PWD/tokens.d:/etc/condor/tokens.d matterminers/cobald-tardis-htcondor:latest

.. content-tabs:: left-col

    .. note::
        Since ``COBalD``/``TARDIS`` uses the `condor_status` command, the token added needs at least the `ALLOW_READ`
        privilege to access the HTCondor Collector and to query the status of resources.

        In addition, ``COBalD``/``TARDIS`` uses the `condor_drain` command to release under utilized resources.
        Therefore, a second token to access the HTCondor StartD of the Drone is needed.

        Usually, both tokens are provided by the operator of the HTCondor overlay batch system.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
