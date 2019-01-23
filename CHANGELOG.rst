CHANGELOG
=========

Version 0.3.2
-------------
Bugfixes + some added functionality.

- ENH: simplify metadata structure
- ENH: fix PAR headers of manually stopped scans (remove partial volumes)

Version 0.3.1
-------------
Hotfix pip install.

- FIX: add MANIFEST.in to fix pip install issue

Version 0.3
-------------
Version 0.3 of bidsify will be the first release after the major refactor.
It contains the following (major) changes:

- ENH: accepts both json and yaml config files
- ENH: major refactoring of package structure (now based on `shablona <https://github.com/uwescience/shablona>`_)
- ENH: writes out a (default) dataset_description.json and participants.tsv file
- ENH: option to run ``bidsify`` in a docker image!
- ENH: (should) work with ``.dcm`` files
- ENH: is now pip installable (``pip install bidsify``)

Versions < 0.3.0
----------------
The changelog for versions < 0.3.0 has not been documented.
