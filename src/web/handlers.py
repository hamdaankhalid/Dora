"""
    Routes are registered and handled here
"""
# pylint: disable=missing-function-docstring

import os
from flask import Blueprint, render_template, request
from src.internal_state import get_state

handlers = Blueprint("handlers", __name__, template_folder="../templates")

_state = get_state()

_MAINTAINER_EMAIL = os.environ.get("MAINTAINER_EMAIL")
_ORGANIZATION_NAME = os.environ.get("ORGANIZATION_NAME")


@handlers.route("/", methods=["GET"])
def index() -> str:
    return render_template(
        "index.html.jinja", title="Home", maintainer=_MAINTAINER_EMAIL
    )


@handlers.route("/pipeline-saga", methods=["GET", "POST"])
def pipeline_saga() -> str:
    pipeline_dependency_visualizer = _state["pipeline_dependency_visualizer"]
    pipeline_names = sorted(pipeline_dependency_visualizer.get_pipeline_names())
    if request.method == "GET":
        return render_template(
            "pipeline-saga.html.jinja",
            title="Pipeline-Saga",
            valid_pipeline_names=pipeline_names,
            maintainer=_MAINTAINER_EMAIL,
            saga_obj_graph_collection=[]
            )
    pipeline_name = request.form.get("pipelineName")
    pipeline_dependency_visualizer = _state["pipeline_dependency_visualizer"]
    graph_node_collection = []
    root_node = pipeline_dependency_visualizer.i_trigger_who_obj_graph(pipeline_name, graph_node_collection)
    who_triggers_me = pipeline_dependency_visualizer.who_all_triger_me(pipeline_name)
    return render_template(
        "pipeline-saga.html.jinja",
        title="Pipeline-Saga",
        valid_pipeline_names=pipeline_names,
        triggered_by=who_triggers_me,
        saga_obj_graph_collection=graph_node_collection, 
        maintainer=_MAINTAINER_EMAIL
    )


@handlers.route("/query", methods=["GET", "POST"])
def query() -> str:
    pipeline_dependency_visualizer = _state["pipeline_dependency_visualizer"]
    pipeline_names = sorted(pipeline_dependency_visualizer.get_pipeline_names())
    file_names = sorted(pipeline_dependency_visualizer.get_file_names())
    if request.method == "GET":
        return render_template(
            "query.html.jinja",
            title="Query",
            valid_pipeline_names=pipeline_names,
            valid_file_names=file_names,
            maintainer=_MAINTAINER_EMAIL,
        )

    file_name = request.form.get("fileName")
    pipeline_name = request.form.get("pipelineName")
    pipeline_defined_by_file, file_defining_pipeline = None, None
    if file_name:
        pipeline_defined_by_file = (
            pipeline_dependency_visualizer.get_pipelines_for_file(file_name)
        )
    if pipeline_name:
        file_defining_pipeline = pipeline_dependency_visualizer.get_file_for_pipeline(
            pipeline_name
        )
    return render_template(
        "query.html.jinja",
        title="Query",
        valid_pipeline_names=pipeline_names,
        valid_file_names=file_names,
        pipeline_defined_by_file=pipeline_defined_by_file,
        file_defining_pipeline=file_defining_pipeline,
        maintainer=_MAINTAINER_EMAIL,
    )


@handlers.route("/feature-request", methods=["GET"])
def feature_request() -> str:
    subject = f"Dora Pipeline Explore for {_ORGANIZATION_NAME}"
    return render_template(
        "feature-request.html.jinja",
        title="Feature-Request",
        maintainer=_MAINTAINER_EMAIL,
        subject=subject,
    )
