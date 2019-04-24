import os
import shutil
from abc import abstractmethod

from analysis.manager.analysis_manager import AnalysisManager
from analysis.understand_analysis import get_metrics_for_project_and_translate_fields, analyze_repo, REPO_CODE_BASE_DIR, \
    REPO_REPORTS_BASE_DIR, REPO_UNDERSTAND_BASE_DIR, remove_directories_for_project, on_rm_error, \
    get_directories_for_project
from store.models import Repository, Measurement
from cbri.reporting import logger
from vcs.repo_type import get_auth_address


class UndAnalysisManager(AnalysisManager):
    """Abstract class for doing analysis with Understand"""

    def __init__(self, repo: Repository):
        self.repo = repo

    def make_measurement(self) -> Measurement:
        try:
            # Prep the repo, analyze it, gather metrics, and then delete the intermediate files
            revision_id = self.prep_for_analysis()
            code_dir, data_dir, und_dir = analyze_repo(self.repo,
                                                       REPO_CODE_BASE_DIR,
                                                       REPO_REPORTS_BASE_DIR,
                                                       REPO_UNDERSTAND_BASE_DIR)
            metrics = get_metrics_for_project_and_translate_fields(self.repo.name, data_dir, revision_id=revision_id)
            # logger.info(str(metrics))
        finally:
            remove_directories_for_project(self.repo.name, REPO_CODE_BASE_DIR, REPO_REPORTS_BASE_DIR,
                                           REPO_UNDERSTAND_BASE_DIR)

        return Measurement.create_from_dict(self.repo, metrics)

    @abstractmethod
    def make_history(self) -> list:
        """Still for subclassses to figure out"""

    def prep_for_analysis(self) -> str:
        """Situate files for analysis! Return the revision_id if applicable"""

        code_dir, data_dir, und_dir = get_directories_for_project(self.repo.name, REPO_CODE_BASE_DIR,
                                                                  REPO_REPORTS_BASE_DIR,
                                                                  REPO_UNDERSTAND_BASE_DIR)

        # Delete that directory if it exists
        if os.path.isdir(code_dir):
            logger.info("\tDeleting " + str(code_dir))
            shutil.rmtree(code_dir, onerror=on_rm_error)

        # Then get the latest code in there!
        auth_address = get_auth_address(self.repo.address, self.repo.token)
        return self.stage_code(auth_address, code_dir, self.repo.token)

    @abstractmethod
    def stage_code(self, repo_address: str, code_dir: str, token: str) -> str:
        """Get the code to be analyzed into the proper directory for analysis
            Return the revision id (if applicable)"""