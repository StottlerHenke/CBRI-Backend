from rest_framework.exceptions import ValidationError
from uuid import UUID

from analysis.manager.analysis_manager_factory import get_analysis_manager
from cbri.reporting import UserNotification, logger
from .models import Repository, Measurement

from background_task import background

"""
These tasks are expected to take a long time.
"""

@background(schedule=10)
def update_repo(repo_id: str, temp_measurement_id: str, current_user_email: str):

    # Make sure the repo hasn't been deleted in the meantime
    repo = Repository.objects.get(pk=UUID(repo_id))
    if not repo:
        return;

    # Delete the temp measurement if it exists
    temp_measurement = Measurement.objects.get(pk=UUID(temp_measurement_id))
    if temp_measurement:
        temp_measurement.delete()

    logger.info("Started update analysis for: " + repo.name)

    un = UserNotification()
    measurement_error = None

    try:
        measurement = get_analysis_manager(repo).make_measurement()
    except Exception as e:
        logger.exception(str(e))
        measurement_error = ValidationError("ANALYSIS ERROR: " + str(e))

    # Notify user of success or failure.
    try:
        if not measurement_error:
            un.send_repo_update_email(current_user_email, repo.name, str(repo.id))
        else:
            un.send_repo_update_failed_email(current_user_email, repo.name, str(measurement_error))
    except Exception as e:
        logger.exception(str(e))

    logger.info("Completed update analysis for: " + repo.name)


@background(schedule=10)
def create_history(repo_id: str, current_user_email: str):
    # Then make a history of measurement objects to kick start things
    repo = Repository.objects.get(pk=UUID(repo_id))
    if not repo:
        return;

    logger.info("Started history analysis for: " + repo.name)

    un = UserNotification()
    measurement_error = None
    try:
        get_analysis_manager(repo).make_history()
    except Exception as e:
        # If something went wrong with the history, don't make the
        # project because it's confusing to see it there Awaiting measurements
        # -djc 2018-07-20
        logger.exception(str(e))
        measurement_error = ValidationError("ANALYSIS ERROR: " + str(e))
        repo.delete()

    # Notify user of success or failure.
    try:
        if not measurement_error:
            un.send_repo_create_email(current_user_email, repo.name, str(repo.id))
        else:
            un.send_repo_create_failed_email(current_user_email, repo.name, str(measurement_error))
    except Exception as e:
        logger.exception(str(e))

    logger.info("Completed history analysis for: " + repo.name)