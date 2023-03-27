from pathlib import Path
from pytest import fixture
from proceed.aggregator import summarize_results


@fixture
def fixture_path(request):
    this_file = Path(request.module.__file__)
    return Path(this_file.parent, 'fixture_files')


# happy path with no file outputs

# happy path with file outputs
# capture file names and digests in summary

# mix of pipelines

# repeat runs with different args, changing file contents
# capture expected args in summary

# safely skip over malformed execution records / irrelevant yaml / yml

# repeat runs for skipping completed steps -- won't have a log file.
