from pathlib import Path
from pytest import fixture

from proceed.aggregator import aggregate_results


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


def test_aggregate(fixture_path):
    results_path = Path(fixture_path, "proceed_out")
    summary = aggregate_results(results_path)

    assert summary == {"foo": "bar"}
