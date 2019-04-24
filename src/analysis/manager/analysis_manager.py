from abc import ABC, abstractmethod

from store.models import Measurement


class AnalysisManager(ABC):
    """Knows how to perform analysis on a Repository. The main case would
    be running Understand on code from a VCS, but abstraction here helps
    to do cases like doing no analysis, or making up fake data."""

    @abstractmethod
    def make_measurement(self) -> Measurement:
        """Create and return a Measurement object in the database for the current state
        of the target repo (or not, if we don't know how for the repo)"""

    @abstractmethod
    def make_history(self) -> list:
        """Create and return a list of Measurement objects in the database for
        recent history of the target repo (or not, if we don't know how for the repo)"""