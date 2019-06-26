============
Site Adapter
============


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
:py:class:`~tardis.adapters.sites.cloudstack.CloudStackAdapter`

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
:py:class:`~tardis.adapters.sites.htcondor.HTCondorAdapter`

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
:py:class:`~tardis.adapters.sites.moab.MoabAdapter`

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
:py:class:`~tardis.adapters.sites.openstack.OpenStackAdapter`

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
:py:class:`~tardis.adapters.sites.slurm.SlurmAdapter`

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
      UpdateDnsName: True
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