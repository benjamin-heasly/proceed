Fizz Buzz
=========

Here is another example pipeline, more advanced than the previous "hello world" example.
It will deomstrate:

 - breaking a goal into several steps
 - declaring a pipeline with each of those step
 - configuring the steps at runtime with :attr:`proceed.model.Pipeline.args` and a :attr:`proceed.model.Pipeline.prototype`
 - matching input and output files so their checksums can be recorded
 - skipping steps that are already complete

This example is based on the `Fizzbuzz <https://en.wikipedia.org/wiki/Fizz_buzz>`_ math game / programming interview question.
The pipeline will play Fizzbuzz for the numbers 1 to 100 and output a file that contains only the multiples of 15.

(personal aside)
    Are Fizzbuzz and other "interview questions" good ways to find valued coworkers/collaborators/friends?
    Maybe?  Maybe not?
    Either way, the game seems like a handy way to demonstrate pipeline stuff.

pipeline spec
-------------

Create a new file called ``fizzbuzz_pipeline_spec.yaml`` with the following content:

.. code-block:: yaml

    version: 0.0.1
    args:
      data_dir: "./data_dir"
      work_dir: "./work_dir"
    prototype:
      volumes:
        "$data_dir": {"bind": /data, "mode": "ro"}
        "$work_dir": /work
    steps:
      - name: classify
        image: fizzbuzz:test
        command: ["/data/classify_in.txt", "/work/classify_out.txt", "classify"]
        match_done: ["classify_out.txt"]
        match_in: ["classify_in.txt"]
        match_out: ["classify_out.txt"]
      - name: filter fizz
        image: fizzbuzz:test
        command: ["/work/classify_out.txt", "/work/filter_fizz_out.txt", "filter", "--substring", "fizz"]
        match_done: ["filter_fizz_out.txt"]
        match_in: ["classify_out.txt"]
        match_out: ["filter_fizz_out.txt"]
      - name: filter buzz
        image: fizzbuzz:test
        command: ["/work/filter_fizz_out.txt", "/work/filter_buzz_out.txt", "filter", "--substring", "buzz"]
        match_done: ["filter_buzz_out.txt"]
        match_in: ["filter_fizz_out.txt"]
        match_out: ["filter_buzz_out.txt"]

WIP...

pipeline execution
------------------

Execute the pipeline using the ``proceed`` command:

.. code-block:: shell

    $ proceed fizzbuzz_pipeline_spec.yaml

WIP...

auditable outputs
-----------------

.. code-block:: shell

    proceed_out/
    │
    ├─ fizzbuzz_pipeline_spec/
    │  │
    │  ├─ 20230321T184856UTC/
    │  │  │
    │  │  ├─ proceed.log
    │  │  ├─ step_one.log
    │  │  ├─ execution_record.yaml

WIP...

step logs
.........

WIP...

execution record
................

WIP...

Amended!
Checksums!

repeat execution
------------------

WIP...

Done files!
skipped!
