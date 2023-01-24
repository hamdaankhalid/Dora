from requests.auth import HTTPBasicAuth
import requests


class AdoClient:
    all_pipelines_url = "/_apis/pipelines?api-version=6.0-preview.1"

    def __init__(self, organization: str, project: str, pat: str, max_acceptable_latency: int) -> any:
        self._pat = pat
        self._max_acceptable_req_latency = max_acceptable_latency
        self.organization = organization
        self.project = project
        self._base_url = f"https://dev.azure.com/{organization}/{project}"

    def get_all_pipelines(self) -> any:
        resp = requests.get(
            self._base_url + AdoClient.all_pipelines_url,
            auth=self._basic_auth(),
            timeout=self._max_acceptable_req_latency,
        )
        resp.raise_for_status()
        return resp.json()["value"]

    def get_pipeline_metadata(self, target_link: str) -> any:
        pipeline_detail_request = requests.get(
            target_link,
            auth=self._basic_auth(),
            timeout=self._max_acceptable_req_latency,
        )
        if pipeline_detail_request.status_code != 200:
            print(f"Error accessing specific pipeline link: {pipeline_detail_request}")
            return
        return pipeline_detail_request.json()

    def get_pipeline_definition(self, pipeline_config_git_repo_id: str, pipeline_file_path: str) -> bytes:
        req_url = self._construct_file_download_url(
            pipeline_file_path, pipeline_config_git_repo_id
        )
        yml_data_res = requests.get(
            req_url, auth=self._basic_auth(), timeout=self._max_acceptable_req_latency
        )
        yml_data_res.raise_for_status()
        return yml_data_res.content

    def get_repository(self, repo_id):
        url = self._construct_get_repo_url(repo_id)
        resp = requests.get(
            url, auth=self._basic_auth(), timeout=self._max_acceptable_req_latency
        )
        resp.raise_for_status()
        return resp.json()

    def _basic_auth(self) -> HTTPBasicAuth:
        return HTTPBasicAuth('ado only checks your pat', self._pat)

    def _construct_file_download_url(self, filepath: str, git_repo_id: str) -> str:
        return (
                self._base_url
                + f"/_apis/git/repositories/{git_repo_id}/items?path={filepath}&api-version=6.0"
        )

    def _construct_get_repo_url(self, repo_id):
        return (self._base_url
                + f'/_apis/git/repositories/{repo_id}?api-version=4.1')
