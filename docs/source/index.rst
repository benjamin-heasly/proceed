Proceed
=======

**Proceed** is a Python library and CLI tool for declarative batch processing.
It reads a **Pipeline** specification declared in `YAML <https://yaml.org/>`_.
A pipeline contains a list of **Steps** that are based on
`Docker <https://www.docker.com/>`_ images and containers.

Each pipeline execution accepts values for declared **args**, allowing controlled,
explicit configuration of steps at runtime.  Each execution produces an
**execution record** that accounts for accepted arg values, step logs, and
checksums of input and output files.

Hopefully, Proceed will allow you to express evertying you need to know about your
processing pipeline in a *"nothing up my sleeves"* way.  The pipeline specification
should be complete enough to share with others who have Proceed and Docker installed,
and the execution record should allow for auditing of expected outcomes and
reproducibility.


Contents
========

.. toctree::
   :maxdepth: 2

   usage
   api
