import django

from vcs.git_helper import GitHelper
from vcs.repo_type import is_git_repo, is_hg_repo, get_repo_type, RepoType


class TestGitHelper(django.test.TestCase):
    def test_clone(self):
        git = GitHelper()
        print(git.clone("https://github.com/StottlerHenkeAssociates/SimBionic.git", "./temp/code", None))


class RepoTypeTest(django.test.TestCase):
    http_git = 'https://github.com/joeyespo/grip'
    ssh_git = None # Set to a valid ssh address to test
    http_hg = None # 'Set to a valid http://... to test'
    file_dir = None # Set to a valid file address to test

    def test_is_git_repo(self):
        print('Test is git repo')
        self.assertTrue(is_git_repo(self.http_git, None))
        self.assertFalse(is_git_repo(self.http_git + '1', None))
        if(self.ssh_git):
            self.assertTrue(is_git_repo(self.ssh_git, None))

    def test_is_hg_repo(self):
        if self.http_hg:
            print('Test is hg repo')
            self.assertTrue(is_hg_repo(self.http_hg, None))
            self.assertFalse(is_hg_repo(self.http_hg + '1', None))
        else:
            print("Hg not tested")

    def test_get_repo_type(self):
        print('Test get repo type')
        print('\tGit')
        self.assertEqual(get_repo_type(self.http_git, None), RepoType.GIT)
        if self.http_hg:
            print('\tHg')
            self.assertEqual(get_repo_type(self.http_hg, None), RepoType.HG)
        if self.file_dir:
            print('\tFile')
            self.assertEqual(get_repo_type(self.file_dir, None), RepoType.FILE)
        print('\tSpecial Cases')
        self.assertEqual(get_repo_type('aaa', None), RepoType.UNKNOWN)
        self.assertEqual(get_repo_type('', None), RepoType.BLANK)
        self.assertEqual(get_repo_type(None, None), RepoType.BLANK)