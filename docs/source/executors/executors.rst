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

    The ssh executor is used to asynchronously execute shell commands remotely via ssh. The actual ssh connection to
    the host is preserved, recycled and automatically reestablished. Most parameters specified in the configuration are
    directly passed as keyword arguments to `asyncssh` `connect` call. You can find all available parameters in the
    `asyncssh documentation`_

    To handle unreliable connections, the ``SSHExecutor`` defaults to retrying commands failed due to lost connections.
    Use the parameter ``on_disconnect_retry`` to enable/disable this (``true`` / ``false``) or set an integer count
    how often each failed command may be retried.

    Additionally the ``SSHExecutor`` supports Multi-factor Authentication (MFA). In order to activate it, you need to
    add ``mfa_config`` as parameter to the ``SSHExecutor`` containing a list of command line prompt to TOTP secrets
    mappings.

    .. note::
        The prompt can be obtained by connecting to the server via ssh in a terminal. The prompt is the text the
        terminal is showing in order to obtain the second factor for the ssh connection. (e.g. "Enter 2FA Token:")

    .. _asyncssh documentation: https://asyncssh.readthedocs.io/en/latest/api.html#connect

.. content-tabs:: right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

      !TardisSSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
        on_disconnect_retry: true

    .. rubric:: Example configuration (Using Multi-factor Authentication)

    .. code-block:: yaml

      !TardisSSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
        mfa_config:
          - prompt: "Enter 2FA Token:"
            totp: "IMIZDDO2I45ZSTR6XDGFSPFDUY"


    .. rubric:: Example configuration (`COBalD` legacy object initialisation)

    .. code-block:: yaml

        __type__: tardis.utilities.executors.sshexecutor.SSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis

Duping SSH Executor
-------------------

.. content-tabs:: left-col

        The duping ssh executor is a special solution for High Performance Compute Centers,
        which offer the opportunity to register so called ssh command keys. That means you
        are able to register a ssh key that can access the cluster without multi-factor
        authentication, but that is restricted to execute one single command without any
        additional command line arguments.

        The duping ssh executor provides the possibility to register a command, a so-called
        wrapper, which itself executes commands that are passed over to the wrapper over
        standard input. The ``wrapper`` parameter is optional, if no ``wrapper`` parameter
        is specified, `/bin/bash` is chosen, which per default executes everything that is
        passed over by standard input.

    .. warning::
        Albeit this mechanism is weakening the security of the compute system, you could
        increase it by restricting the commands that are allowed to be executed by the
        wrapper to ones that are absolutely necessary for the integration. In case of the
        SLURM batch system, to the command `squeue`, `sbatch` and `scancel`. In particular,
        we recommend to **not** use the default `/bin/bash`.

.. content-tabs:: right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

      !TardisDupingSSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
        wrapper: /home/clown/my_script.sh

    .. rubric:: Example configuration (`COBalD` legacy object initialisation)

    .. code-block:: yaml

        __type__: tardis.utilities.executors.sshexecutor.DupingSSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
        wrapper: /home/clown/my_script.sh
