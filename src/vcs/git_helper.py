from git import Repo

from vcs.vcs_helper import VcsHelper
from cbri.reporting import logger


class GitHelper(VcsHelper):

    def clone(self, repo_address: str, code_dir: str, token: str) -> str:
        logger.info("\tCloning Git: " + self.get_safe_address(repo_address, token) + " to: " + code_dir)
        revision_id = None
        try:
            repo = Repo.clone_from(repo_address, code_dir)
            # If needed in future, use django.utils.timezone instead
            # revision_date = datetime.fromtimestamp(repo.head.commit.committed_date, timezone.utc)
            revision_id = str(repo.head.object.hexsha)
        except Exception as e:
            logger.error("Repo could not be cloned")
            logger.exception(e)
            raise

        return revision_id

    def get_latest_rev_at_date(self, code_dir: str, date: str) -> str:
        # HEAD is always set; better to use than master
        repo = Repo(code_dir)
        return repo.git.rev_list('HEAD', n='1', before=date)

    def set_code_to_rev(self, code_dir: str, rev: str):
        repo = Repo(code_dir)
        repo.git.checkout(rev)