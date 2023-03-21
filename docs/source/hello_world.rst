Hello World
===========

Here is a "hello world" example for Proceed.
It will show you how to use `YAML <https://yaml.org/>`_ to declare a pipeline that has one step.
This should give you a feel for the syntax of Proceed's input pipeline spec and output execution record.

pipeline spec
-------------

Create a new file called ``hello.yaml`` with the following content:

.. code-block:: yaml

    steps:
      - name: hello world
        image: ubuntu
        command: echo "hello world"

This is about as simple as a Proceed pipeline can get.
It has a single step that prints "hello world" in an `Ubuntu <https://hub.docker.com/_/ubuntu>`_ container.

The Proceed API docs have more details about what can go in the :class:`proceed.model.Pipeline` spec.

pipeline execution
------------------

Execute the pipeline using the ``proceed`` command:

.. code-block:: shell

    $ proceed hello.yaml

Proceed logs to stdout what it intends to do next, what happened, and when.
If all goes well you won't need to know all of that.
But if something unexpected happens or if you are revisiting things at a later time, this level of detail should help.

.. code-block:: shell

    2023-03-21 14:48:56,598 [INFO] Proceed 0.0.1
    2023-03-21 14:48:56,598 [INFO] Using output directory: proceed_out/hello_world/20230321T184856UTC
    2023-03-21 14:48:56,598 [INFO] Parsing pipeline specification from: hello_world.yaml
    2023-03-21 14:48:56,600 [INFO] Running pipeline with args: {}
    2023-03-21 14:48:56,600 [INFO] Starting pipeline run.
    2023-03-21 14:48:56,600 [INFO] Step 'step one': starting.
    2023-03-21 14:48:56,600 [INFO] Step 'step one': found 0 input files.
    2023-03-21 14:48:57,129 [INFO] Step 'step one': waiting for process to complete.
    2023-03-21 14:48:57,137 [INFO] Step 'step one': hello world

    2023-03-21 14:48:57,417 [INFO] Step 'step one': process completed with exit code 0
    2023-03-21 14:48:57,441 [INFO] Step 'step one': found 0 output files.
    2023-03-21 14:48:57,441 [INFO] Step 'step one': finished.
    2023-03-21 14:48:57,451 [INFO] Finished pipeline run.
    2023-03-21 14:48:57,451 [INFO] Writing execution record to: proceed_out/hello_world/20230321T184856UTC/execution_record.yaml
    2023-03-21 14:48:57,456 [INFO] Completed 1 steps without errors.
    2023-03-21 14:48:57,457 [INFO] OK.

In this simple example, the key result is the "hello world" part in the middle:

.. code-block:: shell

    2023-03-21 14:48:57,137 [INFO] Step 'step one': hello world


auditable outputs
-----------------

In addition to the main log, Proceed writes several files into a working subdirectory.
These are indended to capture exactly what happened and to make the pipeline execution auditable.

.. code-block:: shell

    proceed_out/
    │
    ├─ hello_world/
    │  │
    │  ├─ 20230321T184856UTC/
    │  │  │
    │  │  ├─ proceed.log
    │  │  ├─ step_one.log
    │  │  ├─ execution_record.yaml

The subdirectories are named like this:

.. code-block:: shell

    proceed_out/
    │
    ├─ <name of the pipeline file>/
    │  │
    │  ├─ <execution datetime>/
    │  │  │
    │  │  ├─ *.log
    │  │  ├─ execution_record.yaml


This default scheme should keep the outputs reasonably organized and should prevent collisions between executions.
You can customize the output scheme if you want, see ``proceed --help`` for the options ``--out-dir``, ``--out-group``, and ``--out-id``.

proceed.log
...........

As shown above Proceed writes its runtime log to stdout.
It also writes a copy of the same log to the working subdirectory in ``proceed.log``.

.. code-block:: shell

    $ cat proceed_out/hello_world/20230321T184856UTC/proceed.log

    2023-03-21 11:35:44,951 [INFO] Proceed 0.0.1
    # ... a copy of the console log above ...
    2023-03-21 11:35:45,815 [INFO] OK.

step logs
.........

Proceed also writes the runtime log of each step to its own, separate file.
This includes the stdout and stderr of the step's container process.
You can see the same output copied into the main ``proceed.log``.
But the individual step logs are focused on their own steps and omit prefixes like ``[INFO]``.

.. code-block:: shell

    $ cat proceed_out/hello_world/20230321T184856UTC/step_one.log

    hello world

execution record
................

In addition to these log files, Proceed saves an execution record for each run.
This is an auditable record of facts like:

 - the pipeline spec that was used
 - results for each step like image id, exit code, timing, and checksums of input and ouput files
 - overall timing

.. code-block:: shell

    $ cat proceed_out/hello_world/20230321T184856UTC/execution_record.yaml

.. code-block:: yaml

    original:
      version: 0.0.1
      steps:
        - {name: step one, image: ubuntu, command: echo "hello world"}
    amended:
      version: 0.0.1
      steps:
        - {name: step one, image: ubuntu, command: echo "hello world"}
    timing: {start: '2023-03-21T18:48:56.600323+00:00', finish: '2023-03-21T18:48:57.451028+00:00', duration: 0.850705}
    step_results:
      - name: step one
        image_id: sha256:08d22c0ceb150ddeb2237c5fa3129c0183f3cc6f5eeb2e7aa4016da3ad02140a
        exit_code: 0
        log_file: proceed_out/hello_world/20230321T184856UTC/step_one.log
        timing: {start: '2023-03-21T18:48:56.600597+00:00', finish: '2023-03-21T18:48:57.441764+00:00', duration: 0.841167}
        skipped: false

Here is some explanation of this "hello world" execution record.

``original``
    This is the input pipeline spec, as parsed from ``hello_world.yaml``.
    The YAML formatting may differ somewhat from the input spec, but the content will be equivalent.

``amended``
    This is a version of the original, potentially altered at runtime by :attr:`proceed.model.Pipeline.args` and a :attr:`proceed.model.Pipeline.prototype`
    The ``amended`` version is what actually gets executed, so it's worth recording this explicitly.
    In this example, the ``original`` and ``amended`` versions are the same.

``timing``
    This records UTC datetimes when the pipeline started and finished, and the duration in seconds.

``step_results``
    This is a list of :class:`proceed.model.StepResult`, one for each of the input :attr:`proceed.model.Pipeline.steps`.
    These step results will contain many of the interesting, auditable facts like unique image id, process exit code, and checksums of input and ouput files.
    See the linked API docs for more details.

This example is about as simple as a Proceed execution record gets.
The API docs for :class:`proceed.model.ExecutionRecord` lead to more examples of what can be included.
