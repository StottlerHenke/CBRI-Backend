import os
import unittest
from enum import Enum
import git
import hgapi

class RepoType(Enum):
    """
    We have identified these types of repos. Some are real and do things,
    and some represent funny states. The ordering might be as nice as I'd like,
    but I'm reluctant to rearrange re: DB migrations. -djc 2018-10-18
    """
    GIT = 0
    HG = 1
    FILE = 2
    UNKNOWN = 3  # Address given, but we couldn't figure out what to do with it
    BLANK = 4  # No address given


def get_auth_address(address: str, token: str) -> str:
    """
    :return: an http or https address that combines the address and token
    """
    if not token:
        return address
    elif "http://" in address:
        return address.replace("http://", "http://" + token + "@")
    elif "https://" in address:
        return address.replace("http://", "http://" + token + "@")
    else:
        raise Exception("Tokens can only be applied to http or https repositories.")


def get_repo_type(address: str, token: str) -> RepoType:
    if address:
        if is_file_repo(address):
            return RepoType.FILE
        elif is_git_repo(address, token):
            return RepoType.GIT
        elif is_hg_repo(address, token):
            return RepoType.HG
        else:
            # If not blank, but not recognized, then unknown
            return RepoType.UNKNOWN
    else:
        return RepoType.BLANK


def is_file_repo(repo_address: str) -> bool:
    return 'file:///' in repo_address


def is_git_repo(address, token):
    try:
        # Check if there are references at the remote address
        address = get_auth_address(address, token)
        caller = git.cmd.Git()
        # Params for efficiency? -djc 2018-07-13

        ret = caller.ls_remote(address)
    except git.cmd.CommandError as e:
        return False

    # If we made it here, no exception.
    # XXX: Is that sufficient? Seems okay so far -djc 2018-07-13
    return True


def is_hg_repo(address, token):
    try:
        # id is a simple thing to ping the remote url
        address = get_auth_address(address, token)
        hgapi.Repo.command(".", os.environ, "id", address)
    except hgapi.HgException as e:
        return False

    # If we made it here, no exception.
    # XXX: Is that sufficient? Seems okay so far -djc 2018-07-13
    return True
