from analysis.manager.analysis_manager import AnalysisManager
from store.models import Measurement


class DoNothingAnalysisManager(AnalysisManager):
    """Silently does nothing when asked. Currently used for Repositories
    where no repo address has been given (expected via Jenkins) -djc 2018-10-18"""

    def make_measurement(self) -> Measurement:
        return None

    def make_history(self) -> list:
        return []
