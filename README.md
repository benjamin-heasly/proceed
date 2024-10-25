# Proceed
Declarative file processing with YAML and containers.

**Proceed** is a Python library and CLI tool for declarative batch processing.
It reads a **pipeline** specification declared in [YAML](https://yaml.org/).
A pipeline contains a list of **steps** that are based on [Docker](https://www.docker.com/) images and containers.

Each pipeline execution accepts values for declared **args**, allowing controlled, explicit configuration of steps at runtime.
Each execution produces an **execution record** that accounts for accepted arg values, step logs, and checksums of input and output files.

Hopefully, Proceed will allow you to express everything you need to know about your processing pipeline in a *"nothing up my sleeves"* way.  The pipeline specification should be complete enough to share with others who have Proceed and Docker installed.
The execution record should allow for auditing of expected outcomes and reproducibility.

## docs
Here are the [main docs](https://benjamin-heasly.github.io/proceed/index.html) for Proceed.

# Installation
Proceed requires [Python](https://www.python.org/) and [Docker](https://www.docker.com/) to be installed.
With those, it should be able to run a wide variety pipelines and steps via containers.

## pip
Proceed itself is available on [PyPI](https://pypi.org/project/proceed/).
This is the recommended way to install Proceed:

```
$ pip install proceed
```

## git and pip
You can also install Proceed from source.

```
$ pip install git+https://https://github.com/benjamin-heasly/proceed.git

# editable mode
$ git checkout https://github.com/benjamin-heasly/proceed.git
$ pip install -e ./proceed
```

## check installation
You can check if Proceed installed correctly using the `proceed` command.

```
$ proceed --version
Proceed x.y.z

$ proceed --help
usage etc...
```

## development and testing

You can set up a development environment with [conda](https://conda.io/projects/conda/en/latest/user-guide/install/index.html) and [dev-environment.yml](./dev-environment.yml).

```
conda env create -f dev-environment.yml
# or
conda env update -f dev-environment.yml
```

With that, you should be able to run through the Proceed unit and integration tests.

```
conda activate proceed-dev
hatch run test:cov
```
