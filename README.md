# Proceed
Declarative file processing with YAML and containers.

[Main docs](https://benjamin-heasly.github.io/proceed/index.html)

**Proceed** is a Python library and CLI tool for declarative batch processing.
It reads a **pipeline** specification declared in [YAML](https://yaml.org/).
A pipeline contains a list of **steps** that are based on
[Docker](https://www.docker.com/) images and containers.

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
$ pip install proceed # TODO
```

## git and pip
You can also install Proceed from source.

```
$ git checkout https://github.com/benjamin-heasly/proceed.git
$ pip install ./proceed
```

## check installation
You can check if Proceed installed correctly using the `proceed` command.

```
$ proceed --version
Proceed x.y.z

$ proceed --help
usage etc...
```

# Hello World
Here's a "hello world" example for Proceed.
It will help you declare a pipeline with a single step.
It should give you a feel for the syntax of the input pipeline spec and the output execution record.

## pipeline spec
Create a new file called `hello.yaml` with the following content:

```
steps:
  - name: hello world
    image: ubuntu
    command: echo "hello world"
```

This is about as simple as a Proceed pipeline can get:
a single step that prints "hello world" in an [Ubuntu](https://hub.docker.com/_/ubuntu) container.

The Proceed API docs contain more details about what can go in the [pipeline spec](https://benjamin-heasly.github.io/proceed/generated/proceed.model.Pipeline.html#proceed.model.Pipeline).

## pipeline execution

Execute the specified pipeline using the `proceed` command:

```
$ proceed hello.yaml

2023-03-21 11:35:44,951 [INFO] Proceed 0.0.1
2023-03-21 11:35:44,952 [INFO] Using output directory: proceed_out/hello_world/20230321T153544UTC
2023-03-21 11:35:44,952 [INFO] Parsing proceed pipeline specification from: hello_world.yaml
2023-03-21 11:35:44,953 [INFO] Running pipeline with args: {}
2023-03-21 11:35:44,953 [INFO] Starting pipeline run.
2023-03-21 11:35:44,953 [INFO] Step 'hello world': starting.
2023-03-21 11:35:44,954 [INFO] Step 'hello world': found 0 input files.
2023-03-21 11:35:45,459 [INFO] Step 'hello world': waiting for process to complete.
2023-03-21 11:35:45,467 [INFO] Step 'hello world': hello world

2023-03-21 11:35:45,773 [INFO] Step 'hello world': process completed with exit code 0
2023-03-21 11:35:45,795 [INFO] Step 'hello world': found 0 output files.
2023-03-21 11:35:45,796 [INFO] Step 'hello world': finished.
2023-03-21 11:35:45,809 [INFO] Finished pipeline run.
2023-03-21 11:35:45,810 [INFO] Writing execution record to: proceed_out/hello_world/20230321T153544UTC/execution_record.yaml
2023-03-21 11:35:45,815 [INFO] Completed 1 steps without errors.
2023-03-21 11:35:45,815 [INFO] OK.
```

Proceed logs what it intends to do next, what happened, and when.
If all goes well you won't need to know all of that -- but if something unexpected happens this might help you track down where and why.

In addition to the main log, proceed writes several files into a local subdirectory.
These are indended to capture exactly what happened and to make the pipeline execution auditable.

The subdirectory is named like this:

`root folder` / `name of the pipeline file` / `UTC timestamp` /

This default scheme should keep the outputs reasonably organized and avoid collisions between executions.
You can customize the output scheme if you want, see `proceed --help` for the options `--out-dir`, `--out-group`, and `--out-id`.

## proceed.log
As in the example above, Proceed writes its runtime log to the console stdout.
It also writes a copy of the same log to the local subdirectory in a file called `proceed.log`.

In the example above, this would be `proceed_out/hello_world/20230321T153544UTC/proceed.log`.

```
$ cat proceed_out/hello_world/20230321T153544UTC/proceed.log
# ... a copy of the console log from above ...
```

## step logs
Proceed also writes the runtime log of each step to its own file.
This includes the stdout and stderr of the step's container process.
The same output is included within the main `proceed.log`,
but the individual log files omit all the `[INFO]` and other metadata for each line.

In the example above, this would be `proceed_out/hello_world/20230321T153544UTC/hello_world.log`.

```
$ cat proceed_out/hello_world/20230321T153544UTC/hello_world.log
hello world
```

## execution record
In addition to runtime log files, Proceed saves an execution record for each run.
This is a record of auditable facts about:
 - the pipeline spec that was run
 - step image ids, exit codes, and timing
 - checksums of input and ouput files

In the example above, this would be `proceed_out/hello_world/20230321T153544UTC/execution_record.yaml`.

```
$ cat proceed_out/hello_world/20230321T153544UTC/execution_record.yaml

original:
  version: 0.0.1
  steps:
  - {name: hello world, image: ubuntu, command: echo "hello world"}
amended:
  version: 0.0.1
  steps:
  - {name: hello world, image: ubuntu, command: echo "hello world"}
timing: {start: '2023-03-21T15:35:44.953877+00:00', finish: '2023-03-21T15:35:45.809363+00:00',
  duration: 0.855486}
step_results:
- name: hello world
  image_id: sha256:08d22c0ceb150ddeb2237c5fa3129c0183f3cc6f5eeb2e7aa4016da3ad02140a
  exit_code: 0
  log_file: proceed_out/hello_world/20230321T153544UTC/hello_world.log
  timing: {start: '2023-03-21T15:35:44.954140+00:00', finish: '2023-03-21T15:35:45.796326+00:00',
    duration: 0.842186}
  skipped: false
```

The `original` the input pipeline spec, as parsed from `hello_world.yaml`.  The formatting may differ somewhat, but the content will be equivalent.

The `amended` is a version of the original, potentially with [args](https://benjamin-heasly.github.io/proceed/generated/proceed.model.Pipeline.html#proceed.model.Pipeline.args) and a [prototype](https://benjamin-heasly.github.io/proceed/generated/proceed.model.Pipeline.html#proceed.model.Pipeline.prototype) applied at runtime.  The `amended` version is what's actually run, so it's worth recording this explicitly.  In this "hello world" example, the original and amended are the same.

The `timing` is the UTC times when the whole pipeline started and finished, and whatever that duration was.

The `step_results` is a list of outcomes, one for each of the original `steps`.

The Proceed API docs contain more details about what can go in the [execution record](https://benjamin-heasly.github.io/proceed/generated/proceed.model.ExecutionRecord.html#proceed.model.ExecutionRecord) and [step results](https://benjamin-heasly.github.io/proceed/generated/proceed.model.StepResult.html#proceed.model.StepResult).
