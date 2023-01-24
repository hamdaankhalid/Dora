import os
import sys

import yaml
from dotenv import load_dotenv

from src.ado_client.ado_client import AdoClient

ACCEPTABLE_LATENCY = 15
SEPARATOR = "-" * 20

"""
Recursively search a yaml file for the existence of a string
yaml files support lists and dicts, this instructs our iteration
method. if it is a dict with terminal state we can perform a search for key
"""


def exhaustive_definition_search(definition, for_string) -> bool:
    # terminal state
    if isinstance(definition, str):
        return for_string == definition

    if isinstance(definition, list):
        for element in definition:
            if exhaustive_definition_search(element, for_string):
                return True

    if isinstance(definition, dict):
        for key in definition:
            if exhaustive_definition_search(definition[key], for_string):
                return True

    return False


def main():
    repository = sys.argv[1]
    if not repository:
        print("repository must be passed as argument number 1")
        exit(1)

    dotenv_path = "../.env"
    load_dotenv(dotenv_path)

    client = AdoClient(os.environ.get("ORGANIZATION_NAME"), os.environ.get("PROJECT"),
                       os.environ.get("PAT"), ACCEPTABLE_LATENCY)

    all_pipelines = client.get_all_pipelines()
    print(f"Parsing {len(all_pipelines)} pipelines to find which are triggered by {repository}")

    # array of pipeline link in ado and name
    dependent_pipelines = []
    for pipeline in all_pipelines:
        print(SEPARATOR)
        try:
            pipeline_name = pipeline["name"]
            link = pipeline["_links"]["self"]["href"]
            pipeline_detail_request_body = client.get_pipeline_metadata(link)
            pipeline_file_path = pipeline_detail_request_body["configuration"]["path"]
            pipeline_git_repo_id = pipeline_detail_request_body["configuration"]["repository"]["id"]
            pipeline_repository = client.get_repository(pipeline_git_repo_id)["name"]
            yml_data_res = client.get_pipeline_definition(pipeline_git_repo_id, pipeline_file_path)
            pipeline_definition = yaml.safe_load(yml_data_res)

            if "trigger" in pipeline_definition and pipeline_definition["trigger"] != "none" and \
                    repository == pipeline_repository:
                print("found a relevant trigger reference!")
                dependent_pipelines.append(
                    {"pipeline_name": pipeline_name, "found_in": "trigger", "details": pipeline_definition["trigger"]})

            if "trigger" not in pipeline_definition and repository == pipeline_repository:
                # YAML pipelines are configured by default with a CI trigger on all branches.
                print("found a relevant default trigger reference!")
                dependent_pipelines.append({"pipeline_name": pipeline_name, "found_in": "default_trigger"})

            if "pr" in pipeline_definition and repository == pipeline_repository:
                print("found a relevant PR trigger reference!")
                dependent_pipelines.append(
                    {"pipeline_name": pipeline_name, "found_in": "pr_trigger", "details": pipeline_definition["pr"]})

            # Search for any mention in yaml definition via exhaustive DFS
            if exhaustive_definition_search(pipeline_definition, repository):
                print(f"recursively found mention of {repository}, in definition!")
                print(pipeline_definition)
                dependent_pipelines.append({"pipeline_name": pipeline_name, "found_in": "recursive_definition_search"})

        except Exception as e:
            print(f"Error interacting with pipeline {pipeline['name']}: {e}")
            pass

    print(f"Pipelines triggered by repo: {repository}")
    already_printed = set()
    for pipeline in dependent_pipelines:
        if pipeline["pipeline_name"] not in already_printed:
            print(pipeline)
            already_printed.add(pipeline["pipeline_name"])


if __name__ == '__main__':
    main()
