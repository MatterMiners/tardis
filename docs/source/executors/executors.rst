.. _ref_executors:

=========
Executors
=========

.. container:: left-col

    All executors can be loaded using YAML tags using the (`!Tag`) syntax. More details are available in the
    `PyYAML documentation`_.

    Alternatively you can also use the legacy `COBalD object initialisation syntax`_ to construct executors.
    But it is discouraged.

    .. _PyYAML documentation: https://pyyaml.org/wiki/PyYAMLDocumentation
    .. _COBalD object initialisation syntax: https://cobald.readthedocs.io/en/latest/source/daemon/config.html#object-references

Shell Executor
--------------

.. content-tabs:: left-col

    The shell executor is used to execute shell commands asynchronously.

.. container:: content-tabs right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

      !TardisShellExecutor

    .. rubric:: Example configuration (`COBalD` legacy object initialisation)

    .. code-block:: yaml

        __type__: tardis.utilities.executors.shellexecutor.ShellExecutor

SSH Executor
------------

.. content-tabs:: left-col

    The ssh executor is used to asynchronously execute shell commands remotely via ssh. All parameters specified in the
    configuration are directly passed as keyword arguments to `asyncssh` `connect` call. You can find all available
    parameters in the `asyncssh documentation`_

    .. _asyncssh documentation: https://asyncssh.readthedocs.io/en/latest/api.html#connect

.. content-tabs:: right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

      !TardisSSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis

    .. rubric:: Example configuration (`COBalD` legacy object initialisation)

    .. code-block:: yaml

        __type__: tardis.utilities.executors.sshexecutor.SSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
