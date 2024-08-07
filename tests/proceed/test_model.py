from proceed.model import apply_args, Pipeline, Step

pipeline_spec = """
  version: 0.0.42
  description: Test of a pipeline
  args:
    arg_1: one
    arg_2: two
  prototype:
    description: Test of a step prototype
    environment:
      env_1: one
      env_2: two
    network_mode: none
    mac_address: "11:22:33:44:55:66"
    volumes:
      /dir_shared: /foo/shared
  steps:
    - name: a
      description: Test of a step -- a
      image: image-a
      volumes:
        /dir_a_1: /foo/a1
        /dir_a_2: /bar/a2
      environment:
        env_3: three-a
      network_mode: host
      mac_address: "aa:bb:cc:dd:ee:ff"
      command: ["command", "a"]
      working_dir: /foo/a1
    - name: b
      description: Test of a step -- b
      image: image-b
      environment:
        env_3: three-b
      gpus: True
      volumes:
        /dir_b_1: {"bind": /foo/b1, "mode": "rw"}
        /dir_b_2: {"bind": /bar/b2, "mode": "ro"}
      command: ["command", "b"]
    """


def test_model_from_yaml():
    pipeline = Pipeline.from_yaml(pipeline_spec)
    expected_pipeline = Pipeline(
        version="0.0.42",
        description="Test of a pipeline",
        args={"arg_1": "one", "arg_2": "two", },
        prototype=Step(
            description="Test of a step prototype",
            environment={"env_1": "one", "env_2": "two"},
            network_mode="none",
            mac_address="11:22:33:44:55:66",
            volumes={"/dir_shared": "/foo/shared"},
        ),
        steps=[
            Step(
                name="a",
                description="Test of a step -- a",
                image="image-a",
                environment={"env_3": "three-a"},
                network_mode="host",
                mac_address="aa:bb:cc:dd:ee:ff",
                volumes={"/dir_a_1": "/foo/a1", "/dir_a_2": "/bar/a2"},
                command=["command", "a"],
                working_dir="/foo/a1"
            ),
            Step(
                name="b",
                description="Test of a step -- b",
                image="image-b",
                environment={"env_3": "three-b"},
                gpus=True,
                volumes={"/dir_b_1": {"bind": "/foo/b1", "mode": "rw"}, "/dir_b_2": {"bind": "/bar/b2", "mode": "ro"}},
                command=["command", "b"]
            ),
        ]
    )
    assert pipeline == expected_pipeline


def test_model_round_trip():
    pipeline_1 = Pipeline.from_yaml(pipeline_spec)
    pipeline_1_yaml = Pipeline.to_yaml(pipeline_1)
    pipeline_2 = Pipeline.from_yaml(pipeline_1_yaml)
    assert pipeline_1 == pipeline_2


def test_yaml_collection_style():
    dump_args = {
        "sort_keys": False,
        "default_flow_style": None,
        "width": 1000
    }
    pipeline = Pipeline.from_yaml(pipeline_spec)
    pipeline_yaml = pipeline.to_yaml(dump_args=dump_args)
    # want simple collections on one line, nested collections on multiple lines.
    assert "version: 0.0.42\n" in pipeline_yaml
    assert "  volumes: {/dir_a_1: /foo/a1, /dir_a_2: /bar/a2}\n" in pipeline_yaml
    assert "  volumes:\n" in pipeline_yaml
    assert "    /dir_b_1: {bind: /foo/b1, mode: rw}\n" in pipeline_yaml
    assert "    /dir_b_2: {bind: /bar/b2, mode: ro}\n" in pipeline_yaml


def test_apply_args_to_step():
    step = Step(
        name="$name",
        description="A step named $name",
        image="$org/$repo:$tag",
        user="$user",
        volumes={
            "/host/$simple": "/container/$simple",
            "/host/$complex": {"bind": "/container/$complex", "mode": "rw"}
        },
        command=["$executable", "$arg_1", "${arg_2_prefix}_plus_some_suffix"]
    )
    args = {
        "name": "step_name",
        "org": "image_org",
        "repo": "image_repo",
        "tag": "image_tag",
        "user": "user_name",
        "simple": "path_a",
        "complex": "path_b",
        "executable": "command_executable",
        "arg_1": "command_first_arg",
        "arg_2_prefix": "command_second_arg_prefix"
    }
    step_with_args_applied = step._with_args_applied(args)
    expected_step = step = Step(
        name="step_name",
        description="A step named step_name",
        image="image_org/image_repo:image_tag",
        user="user_name",
        volumes={
            "/host/path_a": "/container/path_a",
            "/host/path_b": {"bind": "/container/path_b", "mode": "rw"}
        },
        command=["command_executable", "command_first_arg", "command_second_arg_prefix_plus_some_suffix"]
    )
    assert step_with_args_applied.name == expected_step.name
    assert step_with_args_applied == expected_step


def test_pipeline_accept_declared_args():
    pipeline = Pipeline(
        args={
            "keep_default": "default",
            "replace": "replace me",
        }
    )
    args = {
        "replace": "I was replaced",
        "ignore": "Ignore me"
    }
    combined_args = pipeline._combine_args(args)
    expected_args = {
        "keep_default": "default",
        "replace": "I was replaced",
    }
    assert combined_args == expected_args


def test_apply_args_to_pipeline():
    pipeline = Pipeline(
        version="0.0.$foo",
        description="A pipeline with two steps",
        args={
            "foo": "should go unused",
            "arg": "$foo",
            "step_name_1": "should get overridden",
            "step_name_2": "should get overridden"
        },
        steps=[
            Step(name="$step_name_1"),
            Step(name="$step_name_2")
        ]
    )
    args = {
        "step_name_1": "first step",
        "step_name_2": "second step"
    }

    # Given args should apply to all steps.
    # The new pipeline.args should reflect all the declared and given args, combined.
    pipeline_with_args_applied = pipeline._with_args_applied(args)
    expected_pipeline = Pipeline(
        version="0.0.$foo",
        description="A pipeline with two steps",
        args={
            "foo": "should go unused",
            "arg": "$foo",
            "step_name_1": "first step",
            "step_name_2": "second step"
        },
        steps=[
            Step(name="first step"),
            Step(name="second step")
        ]
    )
    assert pipeline_with_args_applied == expected_pipeline


def test_apply_args_to_string():
    original = "this is a template foo${variable}baz"
    args = {
        "variable": "bar"
    }
    amended = apply_args(original, args)
    assert amended == "this is a template foobarbaz"


def test_apply_args_to_dictionary():
    original = {"$variable": "the key for this value is $variable"}
    args = {
        "variable": "bar"
    }
    amended = apply_args(original, args)
    assert amended == {"bar": "the key for this value is bar"}


def test_apply_args_to_list():
    original = ["$variable", "constant", "$variable"]
    args = {
        "variable": "bar"
    }
    amended = apply_args(original, args)
    assert amended == ["bar", "constant", "bar"]


def test_apply_args_to_other():
    # Maybe we'll want to support sets some day.
    # For now, just use set as a no-op example.
    original = set("$variable")
    args = {
        "variable": "bar"
    }
    amended = apply_args(original, args)
    assert amended == original


def test_apply_args_recursively():
    original = {
        "string": "this is a template foo${variable}baz",
        "dictionary": {
            "$variable": "the key for this value is $variable",
            "nested list": ["$variable", "constant", "$variable"]
        },
        "list": ["$variable", "constant", "$variable"],
        "nested dictionary": [{"$variable": "the key for this value is $variable"}],
        "other": set("$variable")
    }
    args = {
        "variable": "bar"
    }
    amended = apply_args(original, args)
    expected = original = {
        "string": "this is a template foobarbaz",
        "dictionary": {
            "bar": "the key for this value is bar",
            "nested list": ["bar", "constant", "bar"]
        },
        "list": ["bar", "constant", "bar"],
        "nested dictionary": [{"bar": "the key for this value is bar"}],
        "other": set("$variable")
    }
    assert amended == expected


def test_apply_prototype_to_steps():
    pipeline = Pipeline(
        prototype=Step(
            name="prototype",
            description="A prototype description",
            environment={"prototype_env": "prototype", "common_env": "prototype"},
            volumes={"/prototype_dir": "/prototype", "/common_dir": "/prototype"},
            image="image:prototype",
            user="user_name"
        ),
        steps=[
            Step(
                name="step-a",
                description="A step description-- a",
                environment={"common_env": "step-a", "step_env": "step-a"},
                image="image:step-a",
                user="user_name"
            ),
            Step(
                name="step-b",
                volumes={"/common_dir": "/step-b", "/step_dir": "/step-b"},
                user="user_name"
            ),
        ]
    )
    amended = pipeline._with_prototype_applied()

    # The pipeline prototype can supply field values for each step.
    # Where a step has a default field value, it should take the corresponding value from the prototype.
    # Where a step has an explicit non-default value, the step shoudl keep its own value.
    # Dict fields should become the union of step and prototype entries, with the same precedence rule.
    expected = Pipeline(
        prototype=Step(
            name="prototype",
            description="A prototype description",
            environment={"prototype_env": "prototype", "common_env": "prototype"},
            volumes={"/prototype_dir": "/prototype", "/common_dir": "/prototype"},
            image="image:prototype",
            user="user_name"
        ),
        steps=[
            Step(
                name="step-a",
                description="A step description-- a",
                environment={"prototype_env": "prototype", "common_env": "step-a", "step_env": "step-a"},
                volumes={"/prototype_dir": "/prototype", "/common_dir": "/prototype"},
                image="image:step-a",
                user="user_name"
            ),
            Step(
                name="step-b",
                description="A prototype description",
                environment={"prototype_env": "prototype", "common_env": "prototype"},
                volumes={"/prototype_dir": "/prototype", "/common_dir": "/step-b", "/step_dir": "/step-b"},
                image="image:prototype",
                user="user_name"
            ),
        ]
    )
    assert amended == expected
