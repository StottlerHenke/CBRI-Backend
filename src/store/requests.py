from store.models import InsightUser


def get_insight_user(request):
    """Return InsightUser for the given request or None if it doesn't have one"""
    ret = None
    if request and hasattr(request, "user"):
        user = request.user
        # Watch out for anonymous user in case we're debugging during development
        if user.id:
            user_list = InsightUser.objects.filter(user=user)
            # If exactly one user, return.
            if len(user_list) == 1:
                ret = user_list[0]

    return ret


def get_user_email(request):
    """Return the email of the user for the given request, or None if not found"""
    ret = None

    insight_user = get_insight_user(request)
    if insight_user:
        return insight_user.user.email

    return ret
