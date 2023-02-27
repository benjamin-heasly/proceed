from pipeline_stuff.model import Pipeline

pipeline_spec = """
  version: 0.0.42
  steps:
    - name: a
      image: image-a
      volumes:
        dir-a1: /foo/a1
        dir-a2: /bar/a2
      command: ["command", "a"]
    - name: b
      image: image-b
      volumes:
        dir-b1: {"bind": "/foo/b1", "mode": "rw"}
        dir-b2: {"bind": "/bar/b2", "mode": "ro"}
      command: ["command", "b"]
    """


def test_model_from_yaml():
    pipeline = Pipeline.from_yaml(pipeline_spec)
    assert pipeline.version == "0.0.42"

    assert len(pipeline.steps) == 2

    step_a = pipeline.steps[0]
    assert step_a.name == "a"
    assert len(step_a.volumes) == 2
    assert step_a.volumes["dir-a1"] == "/foo/a1"
    assert step_a.volumes["dir-a2"] == "/bar/a2"
    assert step_a.command == ["command", "a"]

    step_b = pipeline.steps[1]
    assert step_b.name == "b"
    assert len(step_b.volumes) == 2
    assert step_b.volumes["dir-b1"] == {"bind": "/foo/b1", "mode": "rw"}
    assert step_b.volumes["dir-b2"] == {"bind": "/bar/b2", "mode": "ro"}
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
    assert "  volumes: {dir-a1: /foo/a1, dir-a2: /bar/a2}\n" in pipeline_yaml
    assert "  volumes:\n" in pipeline_yaml
    assert "    dir-b1: {bind: /foo/b1, mode: rw}\n" in pipeline_yaml
    assert "    dir-b2: {bind: /bar/b2, mode: ro}\n" in pipeline_yaml
