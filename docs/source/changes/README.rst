Changelog Fragments
-------------------

This folder contains fragments for the ``dev_tools/change-log.py`` tool to
create formatted changelogs. Fragments are YAML files that contain meta-data
and human-readable descriptions of changes. Files are mappings that must contain
the fields ``category``, ``summary``, and ``description` and optionally the fields
``pull requests`` and ``issues``; the naming convention of files is
``<first pull request>.<topic>.yaml``.
Both ``summary`` and ``description`` fields are interpreted as reStructured Text.

.. code:: YAML

    # file `39.line_format.fixes.yaml`
    # any of 'added', 'changed', 'fixed', 'deprecated', 'removed', 'security'
    category: fixed
    # short description of changes
    summary: "fixed Line Protocol sending illegal content"
    # pull requests of this change
    pull requests:
      - 39
      - 44
    # issues solved by this change
    issues:
      - 42
    # long description of changes
    description: |
      The Line Protocol implementation has been extended to remove cases that
      previously led to illegal output. ``None`` values are
      forbidden, and strings are escaped in field values, tags, and measurements.

New changes are assigned to the "next" release. Release information is added
automatically when a release is prepared.
