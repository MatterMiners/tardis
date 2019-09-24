.. _ref_executors:

=========
Executors
=========

.. container:: left-col

    All executors can be loaded using YAML tags using the (`!Tag`) syntax. More details are available in the
    `PyYAML documentation`_

    .. _PyYAML documentation: https://pyyaml.org/wiki/PyYAMLDocumentation

Shell Executor
--------------

.. content-tabs:: left-col

    The shell executor is used to execute shell commands asynchronously.

.. container:: content-tabs right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

      !ShellExecutor

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

      !SSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis

