from proceed.model import Pipeline, Step

pipeline_spec = """
  version: 0.0.42
  args:
    arg_1: one
    arg_2: two
  volumes:
    /dir_shared: /foo/shared
  steps:
    - name: a
      image: image-a
      volumes:
        /dir_a_1: /foo/a1
        /dir_a_2: /bar/a2
      command: ["command", "a"]
    - name: b
      image: image-b
      volumes:
        /dir_b_1: {"bind": /foo/b1, "mode": "rw"}
        /dir_b_2: {"bind": /bar/b2, "mode": "ro"}
      command: ["command", "b"]
    """


def test_model_from_yaml():
    pipeline = Pipeline.from_yaml(pipeline_spec)
    assert pipeline.version == "0.0.42"
    assert pipeline.args == {"arg_1": "one", "arg_2": "two"}
    assert pipeline.volumes == {"/dir_shared": "/foo/shared"}

    assert len(pipeline.steps) == 2

    step_a = pipeline.steps[0]
    assert step_a.name == "a"
    assert len(step_a.volumes) == 2
    assert step_a.volumes["/dir_a_1"] == "/foo/a1"
    assert step_a.volumes["/dir_a_2"] == "/bar/a2"
    assert step_a.command == ["command", "a"]

    step_b = pipeline.steps[1]
    assert step_b.name == "b"
    assert len(step_b.volumes) == 2
    assert step_b.volumes["/dir_b_1"] == {"bind": "/foo/b1", "mode": "rw"}
    assert step_b.volumes["/dir_b_2"] == {"bind": "/bar/b2", "mode": "ro"}
    assert step_b.command == ["command", "b"]


def test_model_round_trip():
    pipeline_1 = Pipeline.from_yaml(pipeline_spec)
    pipeline_1_yaml = Pipeline.to_yaml(pipeline_1)
    pipeline_2 = Pipeline.from_yaml(pipeline_1_yaml)
    assert pipeline_1 == pipeline_2


def test_yaml_collection_style():
    pipeline = Pipeline.from_yaml(pipeline_spec)
    pipeline_yaml = Pipeline.to_yaml(pipeline)
    # want simple collections on one line, nested collections on multiple lines.
    assert "version: 0.0.42\n" in pipeline_yaml
    assert "  volumes: {/dir_a_1: /foo/a1, /dir_a_2: /bar/a2}\n" in pipeline_yaml
    assert "  volumes:\n" in pipeline_yaml
    assert "    /dir_b_1: {bind: /foo/b1, mode: rw}\n" in pipeline_yaml
    assert "    /dir_b_2: {bind: /bar/b2, mode: ro}\n" in pipeline_yaml


def test_apply_args_to_step():
    step = Step(
        name="$name",
        image="$org/$repo:$tag",
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
        "simple": "path_a",
        "complex": "path_b",
        "executable": "command_executable",
        "arg_1": "command_first_arg",
        "arg_2_prefix": "command_second_arg_prefix"
    }
    step_with_args_applied = step.with_args_applied(args)
    expected_step = step = Step(
        name="step_name",
        image="image_org/image_repo:image_tag",
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
    combined_args = pipeline.combine_args(args)
    expected_args = {
        "keep_default": "default",
        "replace": "I was replaced",
    }
    assert combined_args == expected_args


def test_apply_args_to_pipeline():
    pipeline = Pipeline(
        version="0.0.$foo",
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
    # They should not apply to the pipeline's own version or args (these remain $placeholders in this example)
    # The new pipeline.args should reflect all the declared and given args, combined.
    pipeline_with_args_applied = pipeline.with_args_applied(args)
    expected_pipeline = Pipeline(
        version="0.0.$foo",
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
