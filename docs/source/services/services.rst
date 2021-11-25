.. _ref_rest:

========
Services
========

.. container:: left-col

    ``TARDIS`` provides the possibility to start-up dedicated services along with its main process. Those services must
    be decorated with the ``service`` decorator implemented in the ``cobald.daemon`` module. The services are
    dynamically created and started during the ``yaml`` parsing of the configuration. All services are configured within
    the ``Services`` section of the ``TARDIS`` configuration using ``yaml`` tags. Using multiple services is supported
    by using a separate ``yaml`` MappingNode per service.

.. container:: content-tabs right-col

    .. code-block:: yaml

        Services:
            Service_1:
                !TardisService1
                option_1: my_option_1
            Service_2:
                !TardisService2
                option_123: my_option_123

REST Service
------------

.. content-tabs:: left-col

    The :py:class:`~tardis.rest.service.RestService` provides a REST API to access the information stored about the
    managed ``Drones`` inside the :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` plugin.

    .. warning::

        In order to enable the :py:class:`~tardis.rest.service.RestService`, the
        :py:class:`~tardis.plugins.sqliteregistry.SqliteRegistry` plugin has to be enabled as well.

Available configuration options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. content-tabs:: left-col

    +----------------+--------------------------------------------------------------+-----------------+
    | Option         | Short Description                                            | Requirement     |
    +================+==============================================================+=================+
    | host           | Hostname or IP the REST Service is listening on              |  **Required**   |
    +----------------+--------------------------------------------------------------+-----------------+
    | port           | Port the REST Service is listening on                        |  **Required**   |
    +----------------+--------------------------------------------------------------+-----------------+
    | secret_key     | Secret key to use to generate and validate JWTs              |  **Required**   |
    +----------------+--------------------------------------------------------------+-----------------+
    | algorithm      | Algorithm to use generate and validate JWTs (default: HS256) |  **Optional**   |
    +----------------+--------------------------------------------------------------+-----------------+

.. content-tabs:: right-col

    .. rubric:: Example configuration

    .. code-block:: yaml

        Services:
          restapi:
            !TardisRestApi
            host: 127.0.0.1
            port: 1234
            secret_key: 752e003f636f402cc23728e185ce8c9eef27b7e02cf509b3015f7757e625b8e4
            algorithm: HS256
            users:
              - user_name: tardis
                hashed_password: $2b$12$c9SSllh1U6tOhIo37sDWF.kdRIU5RQAAOHL9bVYMs2.HluyFE43Uq
                scopes:
                 - user:read
        Plugins:
          SqliteRegistry:
            db_file: drone_registry.db

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
