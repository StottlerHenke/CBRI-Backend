from abc import ABC, abstractmethod


class VcsHelper(ABC):
    """Handles VCS work. Closely related to UndVcsAnalysisManager.
    TODO: Better encapsulate VCS work.
    E.g. the analysis manager shouldn't have to worry about doing a clone.
    Instead it should call a method here like set_to_latest_rev, and if a
    clone needs to be done to make that happen, this class can worry about it.
    -djc 2018-11-12"""

    @abstractmethod
    def clone(self, repo_address: str, code_dir: str, token: str) -> str:
        """Clone the repo at repo_address to code_dir, return the revision_id"""

    @abstractmethod
    def get_latest_rev_at_date(self, code_dir: str, date: str) -> str:
        """Returns the revision identifier for the latest rev before the given date
        (in the form 2018-01-01). May return None if none found"""

    @abstractmethod
    def set_code_to_rev(self, code_dir: str, rev: str):
        """Set the the code in the code dir to the version at the given rev"""

    def get_safe_address(self, repo_address: str, token: str):
        """ Remove the token from the repo address for safe logging """
        if token and token in repo_address:
            return repo_address.replace(token, "<token redacted>")
        else:
            return repo_address