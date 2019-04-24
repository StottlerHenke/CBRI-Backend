import hgapi

from vcs.vcs_helper import VcsHelper
from cbri.reporting import logger


class HgHelper(VcsHelper):

    def clone(self, repo_address: str, code_dir: str, token: str):
        logger.info("\tCloning Hg: " + self.get_safe_address(repo_address, token) + " to: " + code_dir)
        revision_id = None
        hgapi.hg_clone(repo_address, code_dir)

        #TODO: Determine date and id for Hg

        return revision_id

    def get_latest_rev_at_date(self, code_dir: str, date: str) -> str:
        repo = hgapi.Repo(code_dir)

        extra_args = {"--date": '<'+date}
        return repo.hg_log(limit=1, template="{node}", **extra_args)

    def set_code_to_rev(self, code_dir: str, rev: str):
        repo = hgapi.Repo(code_dir)
        repo.hg_update(reference=rev)
