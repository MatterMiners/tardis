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
    the host is preserved, recycled and automatically reestablished. All parameters specified in the configuration are
    directly passed as keyword arguments to `asyncssh` `connect` call. You can find all available parameters in the
    `asyncssh documentation`_

    Additionally the ``SSHExecutor`` supports Multi-factor Authentication (MFA). In order to activate it, you need to
    add ``mfa_secrets`` as parameter to the ``SSHExecutor`` containing a list of command line prompt to TOTP secrets
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

    .. rubric:: Example configuration (Using Multi-factor Authentication)

    .. code-block:: yaml

      !TardisSSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
        mfa_secrets:
          - prompt: "Enter 2FA Token:"
            secret: "IMIZDDO2I45ZSTR6XDGFSPFDUY"


    .. rubric:: Example configuration (`COBalD` legacy object initialisation)

    .. code-block:: yaml

        __type__: tardis.utilities.executors.sshexecutor.SSHExecutor
        host: login.dorie.somewherein.de
        username: clown
        client_keys:
          - /opt/tardis/ssh/tardis
