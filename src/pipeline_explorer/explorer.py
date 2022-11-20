"""
    This module is a tool for exploring pipeline dependencies for OpenEnergyPlatform
"""

from dataclasses import dataclass
import traceback
from threading import Thread, Lock
from typing import Union, Dict, List
from requests.auth import HTTPBasicAuth
import yaml
import requests


MAX_ACCEPTABLE_REQUEST_LATENCY = 15


@dataclass
class PipelineInfo:
    """
    Data object to encapsulate outputs
    """

    name: str
    link_to_ado: str


@dataclass
class TriggerRelation:
    """
    Data Object that abstracts trigger relationship betwen pipelines
    """

    triggerer: PipelineInfo
    triggers: Union[PipelineInfo, None]


@dataclass
class SagaTriggerRelation(TriggerRelation):
    """
    Data Object that abstracts trigger relationship betwen pipelines
    """

    level: Union[int, None]


class PipelineUnverseMap:
    """
    Given a personal access token, organization, and project.
    This class uses ADO api's to create a mapping of file to mulitple pipelines,
    a mapping of pipeline to file name, and a mapping of a file (of a pipeline)
    to to it's dependencies. These mappings can be interacted with various public get functions
    """

    def __init__(self, pat: str, organization: str, project: str) -> None:
        self._pat = pat
        self._base_url = f"https://dev.azure.com/{organization}/{project}"
        self._mutex = Lock()
        self._pipeline_to_file: Dict[str, str] = {}
        self._file_to_pipelines: Dict[str, List[str]] = {}
        self._file_to_triggerd_by_pipelines: Dict[str, List[str]] = {}
        self._pipeline_to_ado_link: Dict[str, str] = {}
        self._max_aceptable_req_latency = MAX_ACCEPTABLE_REQUEST_LATENCY

    def create_mappings(self) -> None:
        """
        This method is used to create various mappings for your
        project's pipelines. These mappings are stored for later access.
        """
        all_pipelines_url = "/_apis/pipelines?api-version=6.0-preview.1"
        resp = requests.get(
            self._base_url + all_pipelines_url,
            auth=self._basic_auth(),
            timeout=self._max_aceptable_req_latency,
        )
        if resp.status_code != 200:
            raise Exception(
                f"Error accessing pipelines api. Status: {resp.status_code}"
            )
        pipelines_data = resp.json()["value"]
        self._hydrate_mappings(pipelines_data)

    def get_file_names(self) -> str:
        """
        Get an List of all files corresponding to pipelines in your project
        """
        return self._file_to_pipelines.keys()

    def get_pipeline_names(self) -> List[str]:
        """
        Get an List of all pipeline names in your project
        """
        return self._pipeline_to_file.keys()

    def get_pipelines_for_file(self, file: str) -> List[PipelineInfo]:
        """
        get a List of all pipelineInfo objects corresponding to a file with definition
        """
        res = []
        for pipeline in self._file_to_pipelines[file]:
            link_to_ado = self._pipeline_to_ado_link[pipeline]
            res.append(PipelineInfo(name=pipeline, link_to_ado=link_to_ado))
        return res

    def get_file_for_pipeline(self, pipeline: str) -> str:
        """
        get the file that defines the yml confidg for the pipeline
        """
        return self._pipeline_to_file[pipeline]

    def get_triggered_by_for_file(self, file: str) -> List[PipelineInfo]:
        """
        get a List of pipelineInfo objects that are defined as triggerers for a file
        in its configuration
        """
        res = []
        for pipeline in self._file_to_triggerd_by_pipelines[file]:
            if pipeline not in self._pipeline_to_ado_link:
                continue
            link_to_ado = self._pipeline_to_ado_link[pipeline]
            res.append(PipelineInfo(name=pipeline, link_to_ado=link_to_ado))
        return res

    def contains_pipeline_for_file(self, file: str) -> bool:
        """
        check if a given file exists in files associated to pipelines in the project
        """
        return file in self._file_to_pipelines

    def contains_file_for_pipeline(self, pipeline: str) -> bool:
        """
        check if a given pipeline exists in your project
        """
        return pipeline in self._pipeline_to_file

    def get_pipeline_info_for_pipeline(self, pipeline: str) -> PipelineInfo:
        """
        Return a pipelineInfo object for a given pipeline name
        """
        return PipelineInfo(pipeline, self._pipeline_to_ado_link[pipeline])

    def _hydrate_mappings(self, pipelines_data: List[Dict[str, any]]) -> None:
        concurrent_tasks = []
        for pipeline_data in pipelines_data:
            build_mapping_task = Thread(
                target=self._pipeline_build_map_task, args=(pipeline_data,)
            )
            build_mapping_task.start()
            concurrent_tasks.append(build_mapping_task)
        for task in concurrent_tasks:
            task.join()

    def _pipeline_build_map_task(self, pipeline_data: Dict[str, any]) -> None:
        pipeline_name = pipeline_data["name"]
        target_link = pipeline_data["_links"]["self"]["href"]
        ado_pipeline_link = pipeline_data["_links"]["web"]["href"]
        pipeline_detail_request = requests.get(
            target_link,
            auth=self._basic_auth(),
            timeout=self._max_aceptable_req_latency,
        )
        if pipeline_detail_request.status_code != 200:
            print(f"Error accessing specific pipeline link: {pipeline_detail_request}")
            return
        pipeline_detail_request_body = pipeline_detail_request.json()
        pipeline_file_path = pipeline_detail_request_body["configuration"]["path"]
        pipeline_file_name = pipeline_file_path.split("/")[-1]
        self._mutex.acquire()
        try:
            if pipeline_name in self._pipeline_to_file:
                raise Exception(
                    f"Pipeline: {pipeline_name} has more than one files, this is not expected"
                )
            pipeline_git_repo_id = pipeline_detail_request_body["configuration"][
                "repository"
            ]["id"]
            if pipeline_file_name not in self._file_to_triggerd_by_pipelines:
                self._file_to_triggerd_by_pipelines[pipeline_file_name] = []
            pipelines_our_file_is_triggered_by = self._parse_and_find_trigger_pullers(
                pipeline_file_path, pipeline_git_repo_id
            )
            self._file_to_triggerd_by_pipelines[
                pipeline_file_name
            ] += pipelines_our_file_is_triggered_by
            self._pipeline_to_file[pipeline_name] = pipeline_file_name
            if pipeline_file_name not in self._file_to_pipelines:
                self._file_to_pipelines[pipeline_file_name] = []
            self._file_to_pipelines[pipeline_file_name].append(pipeline_name)
            self._pipeline_to_ado_link[pipeline_name] = ado_pipeline_link
        finally:
            self._mutex.release()

    def _parse_and_find_trigger_pullers(
        self, pipeline_file_path: str, pipeline_config_git_repo_id: str
    ) -> List[str]:
        req_url = self._construct_file_download_url(
            pipeline_file_path, pipeline_config_git_repo_id
        )
        yml_data_res = requests.get(
            req_url, auth=self._basic_auth(), timeout=self._max_aceptable_req_latency
        )
        try:
            if yml_data_res.status_code != 200:
                raise Exception(
                    f"Error making yaml file req. Status {yml_data_res.status_code}"
                )

            dependent_pipelines = yaml.safe_load(yml_data_res.content)["resources"][
                "pipelines"
            ]
            dependent_pipeline_names = []
            for pipeline_data in dependent_pipelines:
                dependent_pipeline_names.append(pipeline_data["pipeline"])
            return dependent_pipeline_names
        except Exception:
            return []

    def _basic_auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth("ADOONLYCHECKSPAT", self._pat)

    def _construct_file_download_url(self, filepath: str, git_repo_id: str) -> str:
        return (
            self._base_url
            + f"/_apis/git/repositories/{git_repo_id}/items?path={filepath}&api-version=6.0"
        )


class PipelineDependencyVisualizer:
    """
    Given pipeline to file mapping, file to pipeline name mapping, and file to dependency mapping
    This class builds and holds an in memory graph that can be used to run queries, and display
    visualizations from.
    """

    def __init__(self, pipeline_universe_mapper: PipelineUnverseMap) -> None:
        self._pipeline_universe_mapper = pipeline_universe_mapper
        self._graph: Dict[str, List[PipelineInfo]] = {
            pipeline: [] for pipeline in pipeline_universe_mapper.get_pipeline_names()
        }

    def build_graph(self) -> None:
        """
        Build the graph form mulitple relationship mappings.
        """
        files = self._pipeline_universe_mapper.get_file_names()
        for file in files:
            pipelines = self._pipeline_universe_mapper.get_pipelines_for_file(file)
            for pipeline in pipelines:
                try:
                    triggered_by = (
                        self._pipeline_universe_mapper.get_triggered_by_for_file(file)
                    )
                    for trigger_puller in triggered_by:
                        if trigger_puller.name not in self._graph:
                            print(
                                f"Missing file for pipeline '{trigger_puller}'. Pipeline '{pipeline}' expects to be triggered by '{trigger_puller}'."
                            )
                            continue
                        self._graph[trigger_puller.name].append(pipeline)
                except Exception:
                    print(
                        f"Exception building graph for {pipeline}. Skipping over parsing of this pipeline."
                    )
                    traceback.print_exc()

    def get_pipeline_names(self) -> List[str]:
        """
        Get all pipeline names that exist in our graph
        """
        return self._pipeline_universe_mapper.get_pipeline_names()

    def get_file_names(self) -> List[str]:
        """
        Get all names for files with pipeline definitions
        """
        return self._pipeline_universe_mapper.get_file_names()

    def get_pipelines_for_file(self, file: str) -> List[PipelineInfo]:
        """
        Get List of pipelines defined by a given file name
        """
        return self._pipeline_universe_mapper.get_pipelines_for_file(file)

    def get_file_for_pipeline(self, pipeline_name: str) -> Union[str, None]:
        """
        Get file that defines the pipeline
        """
        if self._pipeline_universe_mapper.contains_file_for_pipeline(pipeline_name):
            return self._pipeline_universe_mapper.get_file_for_pipeline(pipeline_name)

    def top_level_visualize(self) -> List[TriggerRelation]:
        """
        Display direct trigger relationship for every pipeline
        """
        res = []
        for trigger_puller, victims in self._graph.items():
            res.append(
                TriggerRelation(
                    self._pipeline_universe_mapper.get_pipeline_info_for_pipeline(
                        trigger_puller
                    ),
                    victims,
                )
            )
        return res

    def i_trigger_who_chain(self, pipeline: str) -> List[SagaTriggerRelation]:
        """
        Display entire trigger sequence for a given pipeline
        """
        result = []
        self._dfs(pipeline, 0, result)
        return result

    def who_all_triger_me(self, pipeline: str) -> List[PipelineInfo]:
        """
        Get a List of all pipelines that trigger a given pipeline
        """
        res = []
        for triggerer, triggered in self._graph.items():
            is_pipeline_in_triggered = (
                len([marker for marker in triggered if marker.name == pipeline]) > 0
            )
            if is_pipeline_in_triggered:
                res.append(
                    self._pipeline_universe_mapper.get_pipeline_info_for_pipeline(
                        triggerer
                    )
                )
        return res

    def _dfs(
        self, triggered: str, execution_level: int, res: List[SagaTriggerRelation]
    ) -> None:
        if not triggered or triggered not in self._graph:
            return

        triggered_pipeline = (
            self._pipeline_universe_mapper.get_pipeline_info_for_pipeline(triggered)
        )
        if len(self._graph[triggered]) == 0:
            res.append(
                SagaTriggerRelation(
                    level=execution_level, triggerer=triggered_pipeline, triggers=None
                )
            )
            return

        for trigger_pulled_on in self._graph[triggered]:
            res.append(
                SagaTriggerRelation(
                    level=execution_level,
                    triggerer=triggered_pipeline,
                    triggers=trigger_pulled_on,
                )
            )
            self._dfs(trigger_pulled_on.name, execution_level + 1, res)
