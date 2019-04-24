import collections
import datetime

from django.utils import timezone

from analysis.manager.und_analysis_manager import UndAnalysisManager
from analysis.understand_analysis import get_metrics_for_project_and_translate_fields, REPO_CODE_BASE_DIR, \
    REPO_REPORTS_BASE_DIR, REPO_UNDERSTAND_BASE_DIR, get_directories_for_project, run_understand, \
    remove_directories_for_project
from store.models import Repository, Measurement
from vcs.vcs_helper import VcsHelper
from cbri.reporting import logger


class UndVcsAnalysisManager(UndAnalysisManager):
    """Handles Understand analysis using a VCS helper."""

    def __init__(self, repo: Repository, vcs: VcsHelper):
        super().__init__(repo)
        self.vcs = vcs

    def stage_code(self, repo_address: str, code_dir: str, token: str):
        return self.vcs.clone(repo_address, code_dir, token)

    def make_history(self) -> list:
        history = []

        # try to clone - if clone fails, we don't really care about directory cleanup
        try:
            self.prep_for_analysis()
        except Exception as e:
            logger.error("Failed to prep for history.")
            logger.exception(e)
            raise

        try:
            metrics_list = self.get_historical_metrics(self.repo.name, self.repo.language,
                                                       REPO_CODE_BASE_DIR,
                                                       REPO_REPORTS_BASE_DIR,
                                                       REPO_UNDERSTAND_BASE_DIR)

            # XXX: Watch for case that one fails and cancel all or something?
            # -djc 2018-11-06
            for metrics in metrics_list:
                measurement = Measurement.create_from_dict(self.repo, metrics)
                history.append(measurement)
        finally:
            remove_directories_for_project(self.repo.name, REPO_CODE_BASE_DIR, REPO_REPORTS_BASE_DIR,
                                           REPO_UNDERSTAND_BASE_DIR)

        return history

    def get_historical_metrics(self, project_name, lang, code_base_dir, data_base_dir, und_base_dir):
        """ Generate a biweekly history for the project for the past ten weeks.
         Returns a list of dictionaries of the metrics from oldest to newest."""

        code_dir, data_dir, und_dir = get_directories_for_project(project_name, code_base_dir, data_base_dir, und_base_dir)

        # Get an in-order list of commits with their corresponding dates
        commit_to_date = self.get_rev_to_date(code_dir)

        # Compile a list of metrics. The first one is the baseline
        is_first = True
        metric_list = []
        for commit, date in commit_to_date.items():
            logger.info("Analyzing " + date.strftime("%Y-%m-%d"))
            metrics = self.get_metrics_for_rev(project_name, lang, commit, date, code_dir, data_dir, und_dir)
            if metrics:
                if is_first:
                    is_first = False
                    metrics['is_baseline'] = True
                metric_list.append(metrics)


        return metric_list

    def get_metrics_for_rev(self, project_name, lang, rev, rev_date, code_dir, data_dir, und_dir) -> dict:
        """ Check out to the given rev, perform the analysis, and return results """
        self.vcs.set_code_to_rev(code_dir, rev)

        logger.info("Get metrics for revision: " + rev)
        run_understand(project_name, lang, code_dir, data_dir, und_dir)
        return get_metrics_for_project_and_translate_fields(project_name, data_dir, date=rev_date, revision_id=rev)

    def get_rev_to_date(self, code_dir) -> collections.OrderedDict:
        """ Get an ordered dict from commit rev number to date, every two weeks for the past ten weeks, oldest first """

        # Get the list of days for the last ten weeks
        date_list = []
        # Want a full datetime (as opposed to date) at midnight, timezone aware to make django happy
        d = timezone.now().replace(minute=0, second=0, microsecond=0)
        delta = datetime.timedelta(weeks=8)
        # Limit to 6 measurements so it doesn't take as long to process
        for x in range(0, 6):
            date_list.append(d)
            d -= delta
        date_list.reverse()  # put in order from oldest to newest

        # Get the corresponding list of commits

        rev_to_date = collections.OrderedDict()
        for d in date_list:
            rev = self.vcs.get_latest_rev_at_date(code_dir, d.strftime("%Y-%m-%d %X %z"))
            if rev and rev not in rev_to_date.keys():
                rev_to_date[rev] = d

        return rev_to_date
