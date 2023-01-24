"""
    The app needs to hold an in-memory graph that is initilaized only once.
    This module creates and distributes the state as a singleton
"""
# pylint: disable=missing-function-docstring

import os
from typing import Union, Dict
from src.pipeline_explorer.explorer import (
    PipelineDependencyVisualizer,
    PipelineUniverseMap,
)

_PAT = os.environ.get("PAT")
_ORGANIZATION_NAME = os.environ.get("ORGANIZATION_NAME")
_PROJECT = os.environ.get("PROJECT")

_CONSTRUCTED_PIPELINE_DEPENDENCY_VISUALIZER: Union[
    PipelineDependencyVisualizer, None
] = None


def get_state(force=False) -> Dict[str, PipelineDependencyVisualizer]:
    global _CONSTRUCTED_PIPELINE_DEPENDENCY_VISUALIZER

    state = {}

    pat = _PAT
    organization_name = _ORGANIZATION_NAME
    project = _PROJECT

    if _CONSTRUCTED_PIPELINE_DEPENDENCY_VISUALIZER is None or force:
        print("initial boot up, building graph...")
        pipeline_universe_map = PipelineUniverseMap(pat, organization_name, project)
        pipeline_universe_map.create_mappings()
        _CONSTRUCTED_PIPELINE_DEPENDENCY_VISUALIZER = PipelineDependencyVisualizer(
            pipeline_universe_map
        )
        _CONSTRUCTED_PIPELINE_DEPENDENCY_VISUALIZER.build_graph()

    state[
        "pipeline_dependency_visualizer"
    ] = _CONSTRUCTED_PIPELINE_DEPENDENCY_VISUALIZER
    return state
