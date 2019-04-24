import os

from django.apps import AppConfig

from analysis.understand_analysis import REPO_CODE_BASE_DIR, REPO_UNDERSTAND_BASE_DIR, REPO_REPORTS_BASE_DIR


class StoreConfig(AppConfig):
    name = 'store'

    def ready(self):
        # Make sure we have the folders we'll count on for Understand stuff
        os.makedirs(REPO_CODE_BASE_DIR, exist_ok=True)
        os.makedirs(REPO_UNDERSTAND_BASE_DIR, exist_ok=True)
        os.makedirs(REPO_REPORTS_BASE_DIR, exist_ok=True)
