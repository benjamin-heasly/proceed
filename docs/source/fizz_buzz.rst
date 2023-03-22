Tutorial: Fizz Buzz
===================

Here is a longer tutorial to follow on from the :doc:`hello_world` example.
It demonstrates additional Proceed features:

 - breaking down a task into several, explicit steps
 - using YAML to declare a pipeline with several steps
 - configuring the pipeline at runtime with :attr:`proceed.model.Pipeline.args` and a :attr:`proceed.model.Pipeline.prototype`
 - recording and auditing checksums for input and output files
 - skipping steps that are already complete

This example is based on the `Fizz Buzz <https://en.wikipedia.org/wiki/Fizz_buzz>`_ math game.

breaking down the task
----------------------

This pipeline will play Fizzbuzz for the numbers 1 - 100.
Its goal is to output a file that contains only the "fizzbuzz" numbers, which are the numbers divisible by both 3 (aka "fizz") and 5 (aka "buzz").
To achieve this it will factor the task into three steps.

input
  The input to the first step will be a text file with the numbers 1 - 100, one number per line.

  .. code-block:: text

    1
    2
    3
    ...
    90
    91
    92
    93
    94
    95
    96
    97
    98
    99
    100

step 1: "classify"
  This first step will classify each number depending on its divisibility: "fizz" for divisibility by 3, "buzz" for 5, and "fizzbuzz" for both.
  As output it will produce a new text file with the same numbers and lines as above, plus a classifying suffix "fizz", "buzz", or "fizzbuzz", on appropriate lines.

  .. code-block:: text

    1
    2
    3 fizz
    ...
    90 fizzbuzz
    91
    92
    93 fizz
    94
    95 buzz
    96 fizz
    97
    98
    99 fizz
    100 buzz

step 2: "filter fizz"
  This middle step will filter the results of the "classify" step.
  It will output a new text file with only the lines that contain the word "fizz".

  .. code-block:: text

    3 fizz
    ...
    90 fizzbuzz
    93 fizz
    96 fizz
    99 fizz

step 3: "filter buzz"
  The last step will filter the results of the "filter fizz" step, again.
  It will output a final text file with only the lines that contain the word "buzz".

  .. code-block:: text

    15 fizzbuzz
    30 fizzbuzz
    45 fizzbuzz
    60 fizzbuzz
    75 fizzbuzz
    90 fizzbuzz

  `filter_buzz_expected.txt <https://github.com/benjamin-heasly/proceed/blob/main/tests/fizzbuzz/fixture_files/filter_buzz_expected.txt>`_ is the expected "filter buzz" output -- the goal of the pipeline.

The implementation below shows how to express this high-level approach as a Proceed pipeline.

pipeline spec
-------------
Let's start with the whole pipeline spec in YAML.
Then below, we'll look at each part.

.. code-block:: yaml

    version: 0.0.1
    args:
      work_dir: "."
    prototype:
      image: ninjaben/fizzbuzz:test
      volumes:
        $work_dir: /work
    steps:
      - name: classify
        command: [/work/classify_in.txt, /work/classify_out.txt, classify]
        match_done: [classify_out.txt]
        match_in: [classify_in.txt]
        match_out: [classify_out.txt]
      - name: filter fizz
        command: [/work/classify_out.txt, /work/filter_fizz_out.txt, filter, --substring, fizz]
        match_done: [filter_fizz_out.txt]
        match_in: [classify_out.txt]
        match_out: [filter_fizz_out.txt]
      - name: filter buzz
        command: [/work/filter_fizz_out.txt, /work/filter_buzz_out.txt, filter, --substring, buzz]
        match_done: [filter_buzz_out.txt]
        match_in: [filter_fizz_out.txt]
        match_out: [filter_buzz_out.txt]

Here's what each section of the pipeline spec does:

``version``
  This is the version of Proceed itself.
  It allows Proceed to check for compatibility between the spec and the installed version of Proceed.

``args``
  This is a key-value mapping of expected arguments to the pipeline, and their default values.
  This example has only one arg mapping: ``work_dir``, with a default value of ``.`` (the current directory).
  Elsewhere in the spec placeholders like ``$work_dir`` or ``${$work_dir}``, will be replaced at runtime with the arg value.
  We'll see below in `pipeline execution`_ how to specify other arg values at runtime.

``prototype``
  This is a place to put step attributes that all steps have in common.
  Each prototype attribute will be applied to each of the ``steps`` below.

  ``image``
      We want all steps to use the same Docker ``image``, `ninjaben/fizzbuzz:test <https://hub.docker.com/repository/docker/ninjaben/fizzbuzz/general>`_.
      This image contains a Python runtime and a `Python script for playing Fizzbuzz <https://github.com/benjamin-heasly/proceed/blob/main/src/fizzbuzz/fizzbuzz.py>`_.

  ``volumes``
      We also want all steps to see the same filesystem ``volumes``.
      Our ``work_dir`` on the host will appear inside step's each container at the path ``/work``.
      At runtime we'll be able to choose any ``work_dir`` we want, but steps will always see it as ``/work``.
      This consistency simplifies the code running in steps.

``steps``
  Steps are the heart of the pipeline -- the list of processes to run, in order, to achieve the goal.

  ``name``
      Each step gets its own name, to tell it apart from others in logs and the execution record.

  ``image``
      Every step needs a container image to provide the runtime environment, dependencies, and processing code.
      These steps all inherit their image from the ``prototype``: `ninjaben/fizzbuzz:test <https://hub.docker.com/repository/docker/ninjaben/fizzbuzz/general>`_.

  ``command``
      Each step ``command`` runs insite its container.
      This means the command syntax can be anything supported by the ``image``.
      The commands in this example are passed to a `Python script for playing Fizzbuzz <https://github.com/benjamin-heasly/proceed/blob/main/src/fizzbuzz/fizzbuzz.py>`_.
      Each command specifies an input file, and output file, and an operation like "classify" or "filter".

  ``volumes``
      These steps all inherit their ``work_dir`` volume from the ``prototype``.

  ``match_done``
      Steps can use "done files" to mark when they're complete.
      Proceed will check for the existence of any done files before running each step, and skip the step if any are found.
      Each glob pattern in the ``match_done`` list will be matched against each step volume.

  ``match_in``
      Proceed will check for any "in" files before running each step, and record the checksums of these files in the execution record.
      These files don't affect step execution, but should support audits for things like reproducibility, etc.
      Each glob pattern in the ``match_in`` list will be matched against each step volume.

  ``match_out``
      Proceed will check for any "out" files after running each step, and record the checksums of these files in the execution record.
      These files don't affect step execution, but should support audits for things like reproducibility, etc.
      Each glob pattern in the ``match_out`` list will be matched against each step volume.

pipeline execution
------------------

If you have Proceed installed, you can run this pipeline.

First, create a file ``fizzbuzz.yaml`` that contains the YAML `pipeline spec`_ above.

Next, create a ``work_dir`` for the pipeline to use.
This can be any local directory, for example ``./my/work``.

.. code-block:: shell

    $ mkdir -p ./my/work

Create the input file that starts off the game of Fizzbuzz.
You can type the numbers 1-100 into ``/my/work/classify_in.txt`` by hand, or copy `classify_in.txt <https://github.com/benjamin-heasly/proceed/blob/main/tests/fizzbuzz/fixture_files/classify_in.txt>`_ right out of the Proceed integration tests.

.. code-block:: shell

    $ wget -O ./my/work/classify_in.txt https://raw.githubusercontent.com/benjamin-heasly/proceed/main/tests/fizzbuzz/fixture_files/classify_in.txt

Execute the pipeline using the ``proceed`` command, passing in a value for the ``work_dir`` arg:

.. code-block:: shell

    $ proceed fizzbuzz.yaml --args work_dir=./my/work

A successful run should produce log output similar to the following:

.. code-block:: shell

  2023-03-22 16:35:17,403 [INFO] Proceed 0.0.1
  2023-03-22 16:35:17,403 [INFO] Using output directory: proceed_out/fizzbuzz/20230322T203517UTC
  2023-03-22 16:35:17,403 [INFO] Parsing pipeline specification from: fizzbuzz.yaml
  2023-03-22 16:35:17,408 [INFO] Running pipeline with args: {'work_dir': './my/work'}
  2023-03-22 16:35:17,408 [INFO] Starting pipeline run.
  2023-03-22 16:35:17,408 [INFO] Step 'classify': starting.
  2023-03-22 16:35:17,408 [INFO] Computing content hash (sha256) for file: my/work/classify_in.txt
  2023-03-22 16:35:17,409 [INFO] Step 'classify': found 1 input files.
  2023-03-22 16:35:17,933 [INFO] Step 'classify': waiting for process to complete.
  2023-03-22 16:35:18,144 [INFO] Step 'classify': OK.

  2023-03-22 16:35:18,563 [INFO] Step 'classify': process completed with exit code 0
  2023-03-22 16:35:18,600 [INFO] Computing content hash (sha256) for file: my/work/classify_out.txt
  2023-03-22 16:35:18,601 [INFO] Step 'classify': found 1 output files.
  2023-03-22 16:35:18,601 [INFO] Step 'classify': finished.
  2023-03-22 16:35:18,618 [INFO] Step 'filter fizz': starting.
  2023-03-22 16:35:18,619 [INFO] Computing content hash (sha256) for file: my/work/classify_out.txt
  2023-03-22 16:35:18,621 [INFO] Step 'filter fizz': found 1 input files.
  2023-03-22 16:35:19,273 [INFO] Step 'filter fizz': waiting for process to complete.
  2023-03-22 16:35:19,378 [INFO] Step 'filter fizz': OK.

  2023-03-22 16:35:19,653 [INFO] Step 'filter fizz': process completed with exit code 0
  2023-03-22 16:35:19,696 [INFO] Computing content hash (sha256) for file: my/work/filter_fizz_out.txt
  2023-03-22 16:35:19,697 [INFO] Step 'filter fizz': found 1 output files.
  2023-03-22 16:35:19,697 [INFO] Step 'filter fizz': finished.
  2023-03-22 16:35:19,710 [INFO] Step 'filter buzz': starting.
  2023-03-22 16:35:19,711 [INFO] Computing content hash (sha256) for file: my/work/filter_fizz_out.txt
  2023-03-22 16:35:19,712 [INFO] Step 'filter buzz': found 1 input files.
  2023-03-22 16:35:20,271 [INFO] Step 'filter buzz': waiting for process to complete.
  2023-03-22 16:35:20,444 [INFO] Step 'filter buzz': OK.

  2023-03-22 16:35:20,743 [INFO] Step 'filter buzz': process completed with exit code 0
  2023-03-22 16:35:20,782 [INFO] Computing content hash (sha256) for file: my/work/filter_buzz_out.txt
  2023-03-22 16:35:20,783 [INFO] Step 'filter buzz': found 1 output files.
  2023-03-22 16:35:20,783 [INFO] Step 'filter buzz': finished.
  2023-03-22 16:35:20,793 [INFO] Finished pipeline run.
  2023-03-22 16:35:20,794 [INFO] Writing execution record to: proceed_out/fizzbuzz/20230322T203517UTC/execution_record.yaml
  2023-03-22 16:35:20,804 [INFO] Completed 3 steps without errors.
  2023-03-22 16:35:20,805 [INFO] OK.

Proceed logs its own intentions and actions, and incorporates the output from each step.

Below, we'll look at some of the auditable outputs from the pipeline run.

auditable outputs
-----------------
The Fizz Buzz pipeline should have produced several auditable outputs in is working subdirectory.

.. code-block:: shell

    proceed_out/
    │
    ├─ fizzbuzz/
    │  │
    │  ├─ 20230322T203517UTC/
    │  │  │
    │  │  ├─ proceed.log
    │  │  ├─ classify.log
    │  │  ├─ filter_fizz.log
    │  │  ├─ filter_buzz.log
    │  │  ├─ execution_record.yaml

step logs
.........

The ``*.log`` files are durable versions of the command output we saw above.

execution record
................

The ``execution_record.yaml`` has some new, interesting sections.
It's a long-ish document, so we'll focus on specific parts.

.. code-block:: yaml

  original:
    version: 0.0.1
    args: {work_dir: .}
    prototype:
      image: ninjaben/fizzbuzz:test
      volumes: {$work_dir: /work}
    steps:
      - name: classify
        command: [/work/classify_in.txt, /work/classify_out.txt, classify]
        match_done: [classify_out.txt]
        match_in: [classify_in.txt]
        match_out: [classify_out.txt]
      - name: filter fizz
        command: [/work/classify_out.txt, /work/filter_fizz_out.txt, filter, --substring, fizz]
        match_done: [filter_fizz_out.txt]
        match_in: [classify_out.txt]
        match_out: [filter_fizz_out.txt]
      - name: filter buzz
        command: [/work/filter_fizz_out.txt, /work/filter_buzz_out.txt, filter, --substring, buzz]
        match_done: [filter_buzz_out.txt]
        match_in: [filter_fizz_out.txt]
        match_out: [filter_buzz_out.txt]
  amended:
    version: 0.0.1
    args: {work_dir: ./my/work}
    prototype:
      image: ninjaben/fizzbuzz:test
      volumes: {./my/work: /work}
    steps:
      - name: classify
        image: ninjaben/fizzbuzz:test
        command: [/work/classify_in.txt, /work/classify_out.txt, classify]
        volumes: {./my/work: /work}
        match_done: [classify_out.txt]
        match_in: [classify_in.txt]
        match_out: [classify_out.txt]
      - name: filter fizz
        image: ninjaben/fizzbuzz:test
        command: [/work/classify_out.txt, /work/filter_fizz_out.txt, filter, --substring, fizz]
        volumes: {./my/work: /work}
        match_done: [filter_fizz_out.txt]
        match_in: [classify_out.txt]
        match_out: [filter_fizz_out.txt]
      - name: filter buzz
        image: ninjaben/fizzbuzz:test
        command: [/work/filter_fizz_out.txt, /work/filter_buzz_out.txt, filter, --substring, buzz]
        volumes: {./my/work: /work}
        match_done: [filter_buzz_out.txt]
        match_in: [filter_fizz_out.txt]
        match_out: [filter_buzz_out.txt]
  timing: {start: '2023-03-22T20:35:17.408306+00:00', finish: '2023-03-22T20:35:20.793819+00:00', duration: 3.385513}
  step_results:
    - name: classify
      image_id: sha256:151156923039c0e5582094f39c9cfa49c3a4619a8916d97c4ef3fa68ac5d2dca
      exit_code: 0
      log_file: proceed_out/fizzbuzz/20230322T203517UTC/classify.log
      timing: {start: '2023-03-22T20:35:17.408673+00:00', finish: '2023-03-22T20:35:18.601493+00:00', duration: 1.19282}
      files_in:
        ./my/work: {classify_in.txt: 'sha256:93d4e5c77838e0aa5cb6647c385c810a7c2782bf769029e6c420052048ab22bb'}
      files_out:
        ./my/work: {classify_out.txt: 'sha256:5038b8da5a03357397abcd9661dd19bf4ece2d14322e86a7461dda11866d842c'}
      skipped: false
    - name: filter fizz
      image_id: sha256:151156923039c0e5582094f39c9cfa49c3a4619a8916d97c4ef3fa68ac5d2dca
      exit_code: 0
      log_file: proceed_out/fizzbuzz/20230322T203517UTC/filter_fizz.log
      timing: {start: '2023-03-22T20:35:18.618975+00:00', finish: '2023-03-22T20:35:19.697549+00:00', duration: 1.078574}
      files_in:
        ./my/work: {classify_out.txt: 'sha256:5038b8da5a03357397abcd9661dd19bf4ece2d14322e86a7461dda11866d842c'}
      files_out:
        ./my/work: {filter_fizz_out.txt: 'sha256:d1b54ec5994f1c23df98986929c1cd44a991b39b60d7e610752d84f370916739'}
      skipped: false
    - name: filter buzz
      image_id: sha256:151156923039c0e5582094f39c9cfa49c3a4619a8916d97c4ef3fa68ac5d2dca
      exit_code: 0
      log_file: proceed_out/fizzbuzz/20230322T203517UTC/filter_buzz.log
      timing: {start: '2023-03-22T20:35:19.710451+00:00', finish: '2023-03-22T20:35:20.783412+00:00', duration: 1.072961}
      files_in:
        ./my/work: {filter_fizz_out.txt: 'sha256:d1b54ec5994f1c23df98986929c1cd44a991b39b60d7e610752d84f370916739'}
      files_out:
        ./my/work: {filter_buzz_out.txt: 'sha256:238ca7760c45f60dc0826b18cbd245749e0f3bc054c728297132300c5f386141'}
      skipped: false

``original``
  The ``original`` section is the parsed pipeline spec from ``fizzbuzz.yaml``.
  The YAML formatting might differ slightly, but the content is equivalent.

``amended``
  This is the original pipline spec, but with ``args`` and the ``prototype`` applied.
  The ``$work_dir`` placeholder has been replaced with the value supplied at runtime, ``./my/work``.
  The ``prototype`` attributes have been applied to each step.
  These amended steps are the ones that actually get executed.

``step_results``: ``files_in`` and ``files_out``
  Before and after running each step, Proceed checked for files matching the step's ``match_in`` and ``match_out`` patterns.
  It recorded the matching files, along with their checksums.

Here's a simple audit we can do using checksums.
Search this page for the text ``sha256:5038b8da``.
This checksum appears under ``files_out`` for the "classify" step and under ``files_in`` for "filter fizz" step.
So, the execution record has explicitly documented continuity between the steps.

repeat execution
------------------

Finally, let's try running the same pipeline again, without making changes.

.. code-block:: shell

    $ proceed fizzbuzz.yaml --args work_dir=./my/work

This time the loged output is shorter.

.. code-block:: shell

  2023-03-22 16:49:16,222 [INFO] Proceed 0.0.1
  2023-03-22 16:49:16,222 [INFO] Using output directory: proceed_out/fizzbuzz/20230322T204916UTC
  2023-03-22 16:49:16,222 [INFO] Parsing pipeline specification from: fizzbuzz.yaml
  2023-03-22 16:49:16,229 [INFO] Running pipeline with args: {'work_dir': './my/work'}
  2023-03-22 16:49:16,229 [INFO] Starting pipeline run.
  2023-03-22 16:49:16,230 [INFO] Step 'classify': starting.
  2023-03-22 16:49:16,230 [INFO] Computing content hash (sha256) for file: my/work/classify_out.txt
  2023-03-22 16:49:16,231 [INFO] Step 'classify': found 1 done files, skipping execution.
  2023-03-22 16:49:16,231 [INFO] Step 'filter fizz': starting.
  2023-03-22 16:49:16,231 [INFO] Computing content hash (sha256) for file: my/work/filter_fizz_out.txt
  2023-03-22 16:49:16,232 [INFO] Step 'filter fizz': found 1 done files, skipping execution.
  2023-03-22 16:49:16,232 [INFO] Step 'filter buzz': starting.
  2023-03-22 16:49:16,232 [INFO] Computing content hash (sha256) for file: my/work/filter_buzz_out.txt
  2023-03-22 16:49:16,232 [INFO] Step 'filter buzz': found 1 done files, skipping execution.
  2023-03-22 16:49:16,232 [INFO] Finished pipeline run.
  2023-03-22 16:49:16,233 [INFO] Writing execution record to: proceed_out/fizzbuzz/20230322T204916UTC/execution_record.yaml
  2023-03-22 16:49:16,243 [INFO] Completed 3 steps without errors.
  2023-03-22 16:49:16,244 [INFO] OK.

It's shorter because Proceed found the "done file" for each step and decided to skip re-executing the steps.

The ``step_results`` in the ``execution_record.yaml`` are also shorter in this case.

.. code-block:: yaml

  original:
    version: 0.0.1
    args: {work_dir: .}
    prototype:
      image: ninjaben/fizzbuzz:test
      volumes: {$work_dir: /work}
    steps:
    - name: classify
      command: [/work/classify_in.txt, /work/classify_out.txt, classify]
      match_done: [classify_out.txt]
      match_in: [classify_in.txt]
      match_out: [classify_out.txt]
    - name: filter fizz
      command: [/work/classify_out.txt, /work/filter_fizz_out.txt, filter, --substring, fizz]
      match_done: [filter_fizz_out.txt]
      match_in: [classify_out.txt]
      match_out: [filter_fizz_out.txt]
    - name: filter buzz
      command: [/work/filter_fizz_out.txt, /work/filter_buzz_out.txt, filter, --substring, buzz]
      match_done: [filter_buzz_out.txt]
      match_in: [filter_fizz_out.txt]
      match_out: [filter_buzz_out.txt]
  amended:
    version: 0.0.1
    args: {work_dir: ./my/work}
    prototype:
      image: ninjaben/fizzbuzz:test
      volumes: {./my/work: /work}
    steps:
      - name: classify
        image: ninjaben/fizzbuzz:test
        command: [/work/classify_in.txt, /work/classify_out.txt, classify]
        volumes: {./my/work: /work}
        match_done: [classify_out.txt]
        match_in: [classify_in.txt]
        match_out: [classify_out.txt]
      - name: filter fizz
        image: ninjaben/fizzbuzz:test
        command: [/work/classify_out.txt, /work/filter_fizz_out.txt, filter, --substring, fizz]
        volumes: {./my/work: /work}
        match_done: [filter_fizz_out.txt]
        match_in: [classify_out.txt]
        match_out: [filter_fizz_out.txt]
      - name: filter buzz
        image: ninjaben/fizzbuzz:test
        command: [/work/filter_fizz_out.txt, /work/filter_buzz_out.txt, filter, --substring, buzz]
        volumes: {./my/work: /work}
        match_done: [filter_buzz_out.txt]
        match_in: [filter_fizz_out.txt]
        match_out: [filter_buzz_out.txt]
  timing: {start: '2023-03-22T20:49:16.229881+00:00', finish: '2023-03-22T20:49:16.232928+00:00', duration: 0.003047}
  step_results:
    - name: classify
      timing: {start: '2023-03-22 20:49:16.230342+00:00'}
      files_done:
        ./my/work: {classify_out.txt: 'sha256:5038b8da5a03357397abcd9661dd19bf4ece2d14322e86a7461dda11866d842c'}
      skipped: true
    - name: filter fizz
      timing: {start: '2023-03-22 20:49:16.231499+00:00'}
      files_done:
        ./my/work: {filter_fizz_out.txt: 'sha256:d1b54ec5994f1c23df98986929c1cd44a991b39b60d7e610752d84f370916739'}
      skipped: true
    - name: filter buzz
      timing: {start: '2023-03-22 20:49:16.232366+00:00'}
      files_done:
        ./my/work: {filter_buzz_out.txt: 'sha256:238ca7760c45f60dc0826b18cbd245749e0f3bc054c728297132300c5f386141'}
      skipped: true

The ``step_results`` now have ``skipped: true`` to record the fact that they were not re-executed.
They also have ``files_done`` recording matches to their ``match_done`` patterns.

We can do another simple audit to check whether skipping was a good idea.
Search again for the text ``sha256:5038b8da``.
Note that the checksum appears again, under ``files_done`` for the "classify" step.
This tells us the output file *including its contents* are unchanged from the first execution.

If you have a pipeline with long-running steps, skipping re-execution with ``match_done`` might save you time and hassle.
You can use the recorded checksums to audit whether anything changed unexpectedly and/or confirm continuity between steps and pipeline runs.
