.. _ref_rest:

========
Services
========

.. container:: left-col

    ``TARDIS`` provides the possibility to start-up dedicated services along with its main process. Those services must
    be decorated with the ``service`` decorator implemented in the ``cobald.daemon`` module. In order to allow dynamic
    creation of those ``services`` via ``yaml`` tags, the service needs to be decorated with the
    ``@yaml_tag(eager=True)`` decorator as well. The services are then dynamically created and started during the
    ``yaml`` parsing of the configuration. All services are configured within the ``Services`` section of the
    ``TARDIS`` configuration using ``yaml`` tags. Using multiple services is supported by using a separate ``yaml``
    MappingNode per service.

.. container:: content-tabs right-col

    .. rubric:: Example implementation

    .. code-block:: python

        from cobald.daemon import service
        from cobald.daemon.plugins import yaml_tag


        @service(flavour=asyncio)
        @yaml_tag(eager=True)
        class ExampleService(object):
            def __init__(option_1):
                ...
            async def run():
                ...

    .. rubric:: Example configuration

    .. code-block:: yaml

        Services:
            ExampleService:
                !ExampleService
                option_1: my_option_1
            Service_2:
                !TardisService2
                option_123: my_option_123

REST Service
------------

.. container:: content-tabs left-col

    The :py:class:`~tardis.rest.service.RestService` provides a REST API to access the information stored about managed
    ``Drones`` inside the :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` plugin. The REST API supports
    listing resources, getting resource states, and draining resources. All supported REST API calls and their
    parameters are described in REST API documentation available on
    ``http://<hostname>:<port>/docs`` after starting the service. The REST service is using JSON Web Token (JWT) and
    OAuth2 scopes for authentication and authorization.

    .. note::

        The REST API supports two authentication methods:

        1. **Cookie-based** (default for browser clients) — ``POST /user/login``
           returns tokens as httponly cookies
        2. **Bearer token** (for programmatic access) — obtain token via
           ``POST /user/token`` and use in ``Authorization: Bearer <token>`` header


    .. warning::

        In order to enable the :py:class:`~tardis.rest.service.RestService`, the
        :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` plugin has to be enabled as well.

.. Ugly fix for the left column to be aligned with the right column. The left
   column is a bit higher than the right column, so we add some padding to the
   left column to make it look better. This is a temporary fix and should be
   removed when the left column is aligned with the right column.

.. raw:: html

   <h3 style="grid-column: 1 / -1; width: 100%; text-align: left; display: block; clear: both; margin-top: 2rem;">Available configuration options</h3>

.. container:: content-tabs left-col

    .. table:: General options available to configure the REST service

        +----------------+-------------------------------------------------------------------+-----------------+
        | Option         | Short Description                                                 |   Requirement   |
        +================+===================================================================+=================+
        | host           | Hostname or IP the REST Service is listening on                   |  **Required**   |
        +----------------+-------------------------------------------------------------------+-----------------+
        | port           | Port the REST Service is listening on                             |  **Required**   |
        +----------------+-------------------------------------------------------------------+-----------------+
        | user_db_url    | SQLAlchemy database URL for user storage                          |  **Required**   |
        +----------------+-------------------------------------------------------------------+-----------------+

    .. note::

        The ``user_db_url`` uses SQLAlchemy async database URL syntax.
        For SQLite: ``sqlite+aiosqlite:///path/to/users.db``

.. container:: content-tabs right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

        Services:
          restapi:
            !TardisRestApi
            host: 127.0.0.1
            port: 1234
            user_db_url: sqlite+aiosqlite:///users.db
        Plugins:
          SqliteRegistry:
            db_file: drone_registry.db

REST API Endpoints
~~~~~~~~~~~~~~~~~~

.. container:: content-tabs left-col

    .. table:: User endpoints

        +--------+------------------+----------------------------------------------+-----------------+
        | Method | Endpoint         | Description                                  | Required Scope  |
        +========+==================+==============================================+=================+
        | POST   | /user/login      | Authenticate (browser clients using cookies) | —               |
        +--------+------------------+----------------------------------------------+-----------------+
        | POST   | /user/token      | Get bearer token (non-browser clients)       | —               |
        +--------+------------------+----------------------------------------------+-----------------+
        | POST   | /user/logout     | Clear authentication cookies                 | Requires auth   |
        +--------+------------------+----------------------------------------------+-----------------+
        | POST   | /user/refresh    | Refresh access token (cookies)               | Requires auth   |
        +--------+------------------+----------------------------------------------+-----------------+
        | GET    | /user/me         | Get current user info                        | user:get        |
        +--------+------------------+----------------------------------------------+-----------------+
        | GET    | /user/scopes     | Get current user's scopes                    | Requires auth   |
        +--------+------------------+----------------------------------------------+-----------------+

    .. table:: Resource endpoints

        +--------+-------------------------------+------------------+-----------------+
        | Method | Endpoint                      | Description      | Required Scope  |
        +========+===============================+==================+=================+
        | GET    | /resources/                   | List resources   | resources:get   |
        +--------+-------------------------------+------------------+-----------------+
        | GET    | /resources/{uuid}/state       | Get state        | resources:get   |
        +--------+-------------------------------+------------------+-----------------+
        | PATCH  | /resources/{uuid}/drain       | Drain resource   | resources:patch |
        +--------+-------------------------------+------------------+-----------------+

    .. table:: Types endpoints

        +--------+---------------------------+------------------------------+-----------------+
        | Method | Endpoint                  | Description                  | Required Scope  |
        +========+===========================+==============================+=================+
        | GET    | /types/states             | List available states        | resources:get   |
        +--------+---------------------------+------------------------------+-----------------+
        | GET    | /types/sites              | List available sites         | resources:get   |
        +--------+---------------------------+------------------------------+-----------------+
        | GET    | /types/machine_types      | List available machine types | resources:get   |
        +--------+---------------------------+------------------------------+-----------------+

    **Quick start:**

    1. Configure the REST service with ``user_db_url`` pointing to your user database
    2. Create a user: ``tardis-rest-admin add --user-db-url <url> --username <user> --password <pass> --scopes resources:get,resources:patch,user:get``
    3. Authenticate: ``POST /user/login`` with credentials to obtain cookies
    4. Make API requests using the session cookies

.. container:: content-tabs right-col

    .. rubric:: Example API calls

    **Login (receives tokens as httponly cookies):**

    .. code-block:: bash

        curl -X POST http://127.0.0.1:1234/user/login \
          -H "Content-Type: application/json" \
          -d '{"user_name": "tardis", "password": "secret"}' \
          -c cookies.txt

    **Get access token as JSON (alternative to login):**

    .. code-block:: bash

        curl -X POST http://127.0.0.1:1234/user/token \
          -H "Content-Type: application/json" \
          -d '{"user_name": "tardis", "password": "secret"}'

    **Use token from JSON response:**

    .. code-block:: bash

        curl http://127.0.0.1:1234/resources/ \
          -H "Authorization: Bearer <access_token>"

    **Access with cookies:**

    .. code-block:: bash

        curl http://127.0.0.1:1234/resources/ -b cookies.txt

    **Logout:**

    .. code-block:: bash

        curl -X POST http://127.0.0.1:1234/user/logout -b cookies.txt

Available logging configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. container:: content-tabs left-col

    The REST service uses ``uvicorn`` as ASGI server, which provides some additional logging functionality. By default
    the access and errors logs are written into the regular ``TARDIS`` logfile. However, it can be configured to write
    both access and error logs into a separate file. Therefore, an ``uvicorn`` logger needs to be configured. See the
    example logging configuration.

.. container:: content-tabs right-col

    .. rubric:: Example logging configuration

    .. code-block:: yaml

           logging:
             version: 1
             loggers:
               root:
                 level: DEBUG
                 handlers: [console, file]
               uvicorn:
                 level: INFO
                 handlers: [ uvicorn_file ]
                 propagate: False
             formatters:
               precise:
                 format: '%(name)s: %(asctime)s %(message)s'
                 datefmt: '%Y-%m-%d %H:%M:%S'
             handlers:
               console:
                 class : logging.StreamHandler
                 formatter: precise
                 stream  : ext://sys.stdout
               file:
                 class : logging.handlers.RotatingFileHandler
                 formatter: precise
                 filename: tardis.log
                 maxBytes: 10485760
                 backupCount: 3
               uvicorn_file:
                 class: logging.handlers.RotatingFileHandler
                 formatter: precise
                 filename: uvicorn.log
                 maxBytes: 10485760
                 backupCount: 3

Convenience Tools
~~~~~~~~~~~~~~~~~

User Management
"""""""""""""""

.. container:: content-tabs left-col

    The ``tardis-rest-admin`` command provides user management functionality for the REST API.

    .. table:: Available commands

        +------------+------------------------------------------------+-----------------------------------------+
        | Command    | Short Description                              | Available Options                       |
        +============+================================================+=========================================+
        | add        | Create a new user                              | --username, --password, --scopes <list> |
        +------------+------------------------------------------------+-----------------------------------------+
        | list-users | List all users                                 |                                         |
        +------------+------------------------------------------------+-----------------------------------------+
        | delete     | Delete a user                                  | --username                              |
        +------------+------------------------------------------------+-----------------------------------------+

    All commands require ``--user-db-url`` to specify the user database.

.. container:: content-tabs right-col

    .. rubric:: Example usage

    .. code-block:: bash

        # Add user
        tardis-rest-admin --user-db-url sqlite+aiosqlite:///users.db \
          add \
          --username admin --password secret \
          --scopes resources:get,resources:patch,user:get

    .. code-block:: bash

        # List users
        tardis-rest-admin --user-db-url sqlite+aiosqlite:///users.db \
          list-users

    .. code-block:: bash

        # Delete user
        tardis-rest-admin --user-db-url sqlite+aiosqlite:///users.db \
          delete \
          --username admin
