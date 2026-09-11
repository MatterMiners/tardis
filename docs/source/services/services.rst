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

.. content-tabs:: left-col

    The :py:class:`~tardis.rest.service.RestService` provides a REST API to access the information stored about managed
    ``Drones`` inside the :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` plugin. Currently access is read
    only and limited to either list all managed resources or to get the state of a particular resource. All supported
    REST API calls and their parameters are described in REST API documentation available on
    ``http://<hostname>:<port>/docs`` after starting the service. The REST service is using JSON Web Token (JWT) and
    OAuth2 scopes for authentication and authorization.

    .. note::

        The REST service currently supports only read access to the
        :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` using the ``resources:get`` OAuth2 scope. However,
        this could be extended in the future to support also DB updates and deletions using ``resources:put`` and
        ``resources:delete`` OAuth2 scopes. In addition, plans exist to store the ``TARDIS`` configuration in a
        database as well and allow to use the REST service to perform configuration updates at run time.


    .. warning::

        In order to enable the :py:class:`~tardis.rest.service.RestService`, the
        :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` plugin has to be enabled as well.


Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. content-tabs:: left-col

    .. table:: General options available to configure the REST service

        +----------------+-------------------------------------------------------------------+-----------------+
        | Option         | Short Description                                                 | Requirement     |
        +================+===================================================================+=================+
        | host           | Hostname or IP the REST Service is listening on                   |  **Required**   |
        +----------------+-------------------------------------------------------------------+-----------------+
        | port           | Port the REST Service is listening on                             |  **Required**   |
        +----------------+-------------------------------------------------------------------+-----------------+
        | users          | List of user entries allowed to use the REST service. (see below) | **Required**    |
        +----------------+-------------------------------------------------------------------+-----------------+

    .. table:: Options available to the user entries

        +-----------------+-------------------------------------------------+-----------------+
        | Option          | Short Description                               | Requirement     |
        +=================+=================================================+=================+
        | user_name       | The name of the user                            | **Required**    |
        +-----------------+-------------------------------------------------+-----------------+
        | hashed_password | The ``bcrypt`` hashed password of that user     | **Required**    |
        +-----------------+-------------------------------------------------+-----------------+
        | scopes          | List of scopes the user is allowed to request.  | **Required**    |
        +-----------------+-------------------------------------------------+-----------------+

.. content-tabs:: right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

        Services:
          restapi:
            !TardisRestApi
            host: 127.0.0.1
            port: 1234
            users:
              - user_name: tardis
                hashed_password: $2b$12$c9SSllh1U6tOhIo37sDWF.kdRIU5RQAAOHL9bVYMs2.HluyFE43Uq
                scopes:
                 - resources:get
        Plugins:
          SqliteRegistry:
            db_file: drone_registry.db

Available logging configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. content-tabs:: left-col

    The REST service uses ``uvicorn`` as ASGI server, which provides some additional logging functionality. By default
    the access and errors logs are written into the regular ``TARDIS`` logfile. However, it can be configured to write
    both access and error logs into a separate file. Therefore, an ``uvicorn`` logger needs to be configured. See the
    example logging configuration.

.. content-tabs:: right-col

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

Hash Credentials
""""""""""""""""

.. content-tabs:: left-col

    The ``hash_credentials`` command provides an easy way to create password hashes using `bcrypt` to be used in the
    REST service configuration (:ref:`see above<REST Service>`).

    .. table:: Arguments available to `hash_credentials`

        +-----------------+--------------------------------------------------------------+-----------------+
        | Argument        | Short Description                                            | Requirement     |
        +=================+==============================================================+=================+
        | password        | The password to be hashed using bcrypt                       | **Required**    |
        +-----------------+--------------------------------------------------------------+-----------------+

.. content-tabs:: right-col

    .. rubric:: Examples

    .. code-block:: shell

        hash_credentials TopSecretPassword
        #alternatively
        python -m tardis.rest.hash_credentials TopSecretPassword
