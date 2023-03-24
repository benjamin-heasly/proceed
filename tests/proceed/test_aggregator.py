from pathlib import Path
from pytest import fixture
from proceed.aggregator import summarize_results


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


# def test_summarize_results(fixture_path):
    # mix of pipelines
    # repeat runs for skipping and different args
