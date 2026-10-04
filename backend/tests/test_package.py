import researchgraph
from researchgraph import (
    api,
    core,
    infrastructure,
    models,
    repositories,
    schemas,
    services,
    workers,
)


def test_package_metadata() -> None:
    assert researchgraph.__version__ == "0.1.0"


def test_package_submodules() -> None:
    assert api is not None
    assert core is not None
    assert infrastructure is not None
    assert models is not None
    assert repositories is not None
    assert schemas is not None
    assert services is not None
    assert workers is not None
