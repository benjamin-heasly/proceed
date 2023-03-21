# Proceed
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

# Installation
Proceed requires [Python](https://www.python.org/) and [Docker](https://www.docker.com/) to be installed.
With those, it should be able to run a wide variety pipelines and steps via containers.

## pip
Proceed itself is not yet available on [PyPI](https://pypi.org/).
When it is, this will be the recommended way to install Proceed:

```
pip install proceed # TODO
```

## git and pip
You can also install Proceed from source if you want.

```
git checkout https://github.com/benjamin-heasly/proceed.git
pip install ./proceed
```

## check installation
You can check if proceed installed correctly using the `proceed` command.

```
proceed --version
proceed --help
```

# Quick Start
Here's a "hello world" for Proceed.
