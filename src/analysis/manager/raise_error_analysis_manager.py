from analysis.manager.analysis_manager import AnalysisManager
from store.models import Measurement


class RaiseErrorAnalysisManager(AnalysisManager):
    """Raises an error when we try to do analysis. Currently used for the case
    that the user gives us some repo address we can't use with our current VCS
    code. E.g. the user entered a URL with a typo and no VCS server lives there.
    -djc 2018-11-11"""

    def __init__(self, error_msg: str):
        self.error_msg = error_msg

    def make_measurement(self) -> Measurement:
        raise RuntimeError(self.error_msg)

    def make_history(self) -> list:
        raise RuntimeError(self.error_msg)
