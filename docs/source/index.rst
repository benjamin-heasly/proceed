Proceed
=======

**Proceed** is a Python library for declarative batch processing.
It reads a **Pipeline** specification declared in `YAML <https://yaml.org/>`_.
A pipeline contains a list of **Steps** based on `Docker <https://www.docker.com/>`_
images and containers.

Each pipeline execution accepts values for declared **args**, allowing limited,
explicit configuration of steps at runtime.  Each execution produces an
**execution record** that accounts for provided arg values and checksums of input
and output files.

Hopefully, Proceed allows you to express evertying you need to know about a your
processing pipeline in a "nothing up my sleeves" way: the pipeline specification
should be complete enough to share with others who have Proceed and Docker installed,
and the execution record should allow auditing of relevant file contents and logging.


Contents
========

.. toctree::
   :maxdepth: 1

   usage
   api
