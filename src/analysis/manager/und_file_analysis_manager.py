import shutil

from analysis.manager.und_analysis_manager import UndAnalysisManager
from store.models import Repository
from cbri.reporting import logger


class UndFileAnalysisManager(UndAnalysisManager):
    """Handler for  case to analyze  code that isn't in a vcs.
    I.e. no history info, just the source files."""

    def __init__(self, repo: Repository):
        super().__init__(repo)

    def stage_code(self, repo_address: str, code_dir: str, token: str) -> str:
        repo_address = repo_address.replace('file://', '')
        logger.info("Copying from " + str(repo_address) + " to " + str (code_dir))
        shutil.copytree(repo_address, code_dir)
        return "No VCS"

    def make_history(self) -> list:
        """For a file repo, the history is just what we see right now.
        I.e. same as taking current measurement"""
        return [self.make_measurement()]
