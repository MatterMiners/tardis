============
Site Adapter
============

The site adapters provide interfaces to various Cloud APIs and batch systems in order to allow a on-demand provisioning
of resources and a dynamic orchestration of pre-built VM images and containers.

Sites are generally configured in the `Sites` configuration block. One has to specify a site name, the adapter to use
and a site quota in units of cores. Negative values for the site quota are interpreted as infinity. Multiple sites are
supported by using SequenceNodes.

Generic Site Adapter Configuration
----------------------------------

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+---------+----------------------------------------------------------------------------------+-----------------+
| Option  | Short Description                                                                | Optionality     |
+=========+==================================================================================+=================+
| name    | Name of the site                                                                 |  **Required**   |
+---------+----------------------------------------------------------------------------------+-----------------+
| adapter | Site adapter to use. Adapter will be auto-imported (class name without Adapter)  |  **Required**   |
+---------+----------------------------------------------------------------------------------+-----------------+
| quota   | Core quota to be used for this site. Negative values are interpreted as infinity |  **Required**   |
+---------+----------------------------------------------------------------------------------+-----------------+

For each site in the `Sites` configuration block. A site specific configuration block carrying the site name
has to be added to the configuration as well.

The site specific MappingNode contains site adapter specific configuration options that you can find below in
the particular site adapter documentation.

In addition, it is required to add the following MappingNodes:

* `MachineTypes` containing a SequenceNode of available machine types to be supported at the given site.
* `MachineTypeConfiguration` a MappingNode for each machine type containing machine type specific configurations,
  details can be found below in the particular site adapter documentation.
* `MachineTypeMetaData` containing a MappingNode for each machine type specifying the amount of Cores, Memory and Disk
  available


Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Sites:
      - name: MySiteName_1
        adapter: MyAdapter2Use
        quota: 123
      - name: MySiteName_2
        adapter: OtherAdapter2Use
        quota: 987

    MySiteName_1:
      general_adapter_option: something
      MachineTypes:
        - Micro
        - Fat
      MachineTypeConfiguration:
        Micro:
          machine_type_specific_option_1: 124234-1245-1345-15
          machine_type_specific_option_2: 4583453-3245-345-2345
        Fat:
          machine_type_specific_option_1: 0034532-345-234-2341
          machine_type_specific_option_2: 1345-134-1345-134-1
      MachineMetaData:
        Micro:
          Cores: 1
          Memory: 2
          Disk: 30
        Fat:
          Cores: 32
          Memory: 128
          Disk: 256

    MySiteName_2:
      general_adapter_option: something_else
      MachineTypes:
        - XL
      MachineTypeConfiguration:
        XL:
          machine_type_specific_option_1: 9847867-467846-468748BC
      MachineMetaData:
        XL:
          Cores: 128
          Memory: 256
          Disk: 1024

Cloud Stack Site Adapter
------------------------
The :py:class:`~tardis.adapters.sites.cloudstack.CloudStackAdapter` implements an interface to the CloudStack API.
The following general adapter configuration options are available.

Available adapter configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+---------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                   | Optionality     |
+================+=====================================================================+=================+
| api_key        | Your CloudStack API Key to authenticate yourself.                   |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| api_secret     | Your CloudStack API secret to authenticate yourself.                |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+
| end_point      | The end point of the CloudStack API to contact.                     |  **Required**   |
+----------------+---------------------------------------------------------------------+-----------------+

All configuration entries in the `MachineTypeConfiguration` section of the machine types are
directly added as keyword arguments to the CloudStack API `deployVirtualMachine` call. All available options are
described in the `CloudStack documentation`_

.. _CloudStack documentation: https://cloudstack.apache.org/api/apidocs-4.12/apis/deployVirtualMachine.html

Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Sites:
      - name: Hexascale
        adapter: CloudStack
        quota: 300

    Hexascale:
      api_key: BlaBlubbFooBar123456
      api_secret: AKshflajsdfjnASJFkajsfd
      end_point: https://api.hexascale.com/compute
      MachineTypes:
        - Micro
        - Tiny
      MachineTypeConfiguration:
        Micro:
          templateid: 909ce5b7-2132-4ff0-9bf8-aadbb423f7d9
          serviceofferingid: 71004023-bb72-4a97-b1e9-bc66dfce9470
          zoneid: 35eb7739-d19e-45f7-a581-4687c54d6d02
          securitygroupnames: "secgrp-WN,NFS-access,Squid-access"
          userdata: ini/hexascale.ini
          keypair: MG
          rootdisksize: 70
        Tiny:
          templateid: 909ce5b7-2132-4ff0-9bf8-aadbb423f7d9
          serviceofferingid: b6cd1ff5-3a2f-4e9d-a4d1-8988c1191fe8
          zoneid: 35eb7739-d19e-45f7-a581-4687c54d6d02
          securitygroupnames: "secgrp-WN,NFS-access,Squid-access"
          userdata: ini/hexascale.ini
          keypair: MG
          rootdisksize: 70

HTCondor Site Adapter
---------------------
The :py:class:`~tardis.adapters.sites.htcondor.HTCondorAdapter` implements an interface to the HTCondor batch system.
Regular batch jobs are submitted that start the actual Drone, which than is integrated itself in overlay batch system
using the chosen :ref:`BatchSystemAdapter.<ref_batch_system_adapter>`

.. |executor| replace:: :ref:`executor<ref_executors>`

Available adapter configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+----------------+-----------------------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                                 | Optionality     |
+================+===================================================================================+=================+
| max_age        | The result of the `condor_status` call is cached for `max_age` in minutes.        |  **Required**   |
+----------------+-----------------------------------------------------------------------------------+-----------------+
| executor       | The |executor| used to run submission and further calls to the Moab batch system. |  **Optional**   |
+                +                                                                                   +                 +
|                | Default: ShellExecutor is used!                                                   |                 |
+----------------+-----------------------------------------------------------------------------------+-----------------+

The only available option in the `MachineTypeConfiguration` section is a template jdl used to submit drones to the
HTCondor batch system. The template jdl is using the `Python template string`_ syntax.

.. _Python template string: https://docs.python.org/3.4/library/string.html#template-strings

Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Sites:
      - name: TOPAS
        adapter: HTCondor
        quota: 462

    TOPAS:
      max_age: 1
      MachineTypes:
        - wholenode
      MachineTypeConfiguration:
        wholenode:
          jdl: pilot_wholenode.jdl
      MachineMetaData:
        wholenode:
          Cores: 42
          Memory: 256
          Disk: 840

Moab Site Adapter
-----------------
The :py:class:`~tardis.adapters.sites.moab.MoabAdapter` implements an interface to the Moab batch system. Regular batch
jobs are submitted that start the actual Drone, which than is integrated itself in overlay batch system
using the chosen :ref:`BatchSystemAdapter.<ref_batch_system_adapter>`.

Available adapter configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+----------------+-----------------------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                                 | Optionality     |
+================+===================================================================================+=================+
| StatusUpdate   | The result of the status call is cached for `StatusUpdate` in minutes.            |  **Required**   |
+----------------+-----------------------------------------------------------------------------------+-----------------+
| StartUpCommand | The command executed in the batch job.                                            |  **Required**   |
+----------------+-----------------------------------------------------------------------------------+-----------------+
| executor       | The |executor| used to run submission and further calls to the Moab batch system. |  **Optional**   |
+                +                                                                                   +                 +
|                | Default: ShellExecutor is used!                                                   |                 |
+----------------+-----------------------------------------------------------------------------------+-----------------+

The available options in the `MachineTypeConfiguration` section are the expected `WallTime` of the placeholder jobs and
the requested `NodeType`. For details see the Moab documentation.

Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Sites:
      - name: moab-site
        adapter: Moab
        quota: 2000

    moab-site:
      executor: !SSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
      StartupCommand: startVM.py
      StatusUpdate: 2
      MachineTypes:
        - singularity_d2.large
        - singularity_d1.large
      MachineTypeConfiguration:
        singularity_d2.large:
          Walltime: '02:00:00:00'
          NodeType: '1:ppn=20'
        singularity_d1.large:
          Walltime: '01:00:00:00'
          NodeType: '1:ppn=20'
      MachineMetaData:
        singularity_d2.large:
          Cores: 20
          Memory: 120
          Disk: 196
        singularity_d1.large:
          Cores: 20
          Memory: 120
          Disk: 196

OpenStack Site Adapter
----------------------
The :py:class:`~tardis.adapters.sites.openstack.OpenStackAdapter` implements an interface to the OpenStack Cloud API.
The following general adapter configuration options are available.

Available adapter configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+---------------------+---------------------------------------------------------------------+-----------------+
| Option              | Short Description                                                   | Optionality     |
+=====================+=====================================================================+=================+
| auth_url            | The end point of the OpenStack API to contact.                      |  **Required**   |
+---------------------+---------------------------------------------------------------------+-----------------+
| username            | Your OpenStack API username to authenticate yourself.               |  **Required**   |
+---------------------+---------------------------------------------------------------------+-----------------+
| password            | Your OpenStack API password to authenticate yourself.               |  **Required**   |
+---------------------+---------------------------------------------------------------------+-----------------+
| user_domain_name    | The name of the OpenStack user domain.                              |  **Required**   |
+---------------------+---------------------------------------------------------------------+-----------------+
| project_domain_name | The name of the OpenStack project domain.                           |  **Required**   |
+---------------------+---------------------------------------------------------------------+-----------------+


All configuration entries in the `MachineTypeConfiguration` section of the machine types are
directly added as keyword arguments to the OpenStack API `create-server` call. All available options are
described in the `OpenStack documentation`_

.. _OpenStack documentation: https://developer.openstack.org/api-ref/compute/#create-server

Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Sites:
      - name: Woohoo
        adapter: OpenStack
        quota: 10 # CPU core quota

    Woohoo:
      auth_url: https://whoowhoo:13000/v3
      username: woohoo
      password: Woohoo123
      project_name: WooHoo
      user_domain_name: Default
      project_domain_name: Default
      MachineTypes:
        - m1.xlarge
      MachineTypeConfiguration:
        m1.xlarge:
          flavorRef: 5 # ID of m1.xlarge
          networks:
            - uuid: fe0317c6-0bed-488b-9108-13726656a0ea
          imageRef: bc613271-6a54-48ca-9222-47e009dc0c29
          key_name: MG
          user_data: tardis/cloudinit/woohoo.ini
      MachineMetaData:
        m1.xlarge:
          Cores: 8
          Memory: 16
          Disk: 160

Slurm Site Adapter
------------------
The :py:class:`~tardis.adapters.sites.slurm.SlurmAdapter` implements an interface to the SLURM batch system. Regular
batch jobs are submitted that start the actual Drone, which than is integrated itself in overlay batch system
using the chosen :ref:`BatchSystemAdapter.<ref_batch_system_adapter>`.

Available adapter configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+----------------+-----------------------------------------------------------------------------------+-----------------+
| Option         | Short Description                                                                 | Optionality     |
+================+===================================================================================+=================+
| StatusUpdate   | The result of the status call is cached for `StatusUpdate` in minutes.            |  **Required**   |
+----------------+-----------------------------------------------------------------------------------+-----------------+
| StartUpCommand | The command executed in the batch job.                                            |  **Required**   |
+----------------+-----------------------------------------------------------------------------------+-----------------+
| executor       | The |executor| used to run submission and further calls to the Moab batch system. |  **Optional**   |
+                +                                                                                   +                 +
|                | Default: ShellExecutor is used!                                                   |                 |
+----------------+-----------------------------------------------------------------------------------+-----------------+


Example configuration
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

    Sites:
      - name: hpc2000
        adapter: Slurm
        quota: 100

    hpc2000:
      executor: !SSHExecutor
        host: hpc2000.hpc.org
        username: billy
        client_keys:
         - /opt/tardis/ssh/tardis
      StartupCommand: pilot_clean.sh
      StatusUpdate: 2
      MachineTypes:
        - one_day
        - twelve_hours
      MachineTypeConfiguration:
        one_day:
          Walltime: '1440'
          Partition: normal
        twelve_hours:
          Walltime: '600'
          Partition: normal
      MachineMetaData:
        one_day:
          Cores: 20
          Memory: 62
          Disk: 480
        twelve_hours:
          Cores: 20
          Memory: 62
          Disk: 480

Your favorite site is currently not supported?
Please, have a look at
:ref:`how to contribute.<ref_contribute_site_adapter>`