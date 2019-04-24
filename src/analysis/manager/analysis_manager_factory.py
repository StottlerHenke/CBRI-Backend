from analysis.manager.analysis_manager import AnalysisManager
from analysis.manager.do_nothing_analysis_manager import DoNothingAnalysisManager
from analysis.manager.raise_error_analysis_manager import RaiseErrorAnalysisManager
from analysis.manager.und_file_analysis_manager import UndFileAnalysisManager
from analysis.manager.und_vcs_analysis_manager import UndVcsAnalysisManager
from store.models import Repository
from vcs.git_helper import GitHelper
from vcs.hg_helper import HgHelper
from vcs.repo_type import RepoType


def get_analysis_manager(repo: Repository) -> AnalysisManager:
    """Return the appropriate type of analysis manager for the given repo"""

    if repo.type is RepoType.FILE:
        return UndFileAnalysisManager(repo)
    elif repo.type is RepoType.GIT:
        return UndVcsAnalysisManager(repo, GitHelper())
    elif repo.type is RepoType.HG:
        return UndVcsAnalysisManager(repo, HgHelper())
    elif repo.type is RepoType.BLANK:
        # Someone makes a repo, but doesnt give a repo address, do nothing.
        # For now we have this in mind with Jenkins.
        # TODO: Think more about this case and the unknown case when
        # we let the user edit repo info to add the address later or
        # fix a typo. -djc 2018-10-18
        return DoNothingAnalysisManager()
    else:
        error_msg = "Could not clone repository. Is the address correct? " + repo.address
        return RaiseErrorAnalysisManager(error_msg)
