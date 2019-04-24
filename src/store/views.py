from django.conf import settings
from rest_framework import viewsets
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

import cbri.settings as settings
from cbri.context_processors import selected_settings
from .serializers import *


class SettingsAPIView(APIView):

    permission_classes = (AllowAny,)

    def get(self, request, format=None):
        return Response(selected_settings(request))


class SupportedLanguagesAPIView(APIView):

    def get(self, request, format=None):
        return Response(getattr(settings, 'SUPPORTED_LANGUAGES', []))


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all().order_by('name')
    serializer_class = OrganizationSerializer


class InsightUserViewSet(viewsets.ModelViewSet):
    queryset = InsightUser.objects.all()
    serializer_class = InsightUserSerializer


# Special path to create a user without authentication.
# We don't want to expose e.g. deleting and editing users, so
# separate from InsightUserViewSet
class CreateInsightUserView(CreateAPIView):
    queryset = InsightUser.objects.all()
    serializer_class = InsightUserSerializer
    permission_classes = (AllowAny,)


# Essentially translates the user's current token into
# the user object. Note that a ViewSet does more magic
# than we'd want for this case, so we get a little more
# nitty gritty with a View instead. -djc 2018-06-01
class CurrentUserView(APIView):
    def get(self, request, format=None):
        request_user = self.request.user

        # We might have an anonymous user if we turn off authentication
        # for testing. Return nothing rather than cause an exception. :P
        # -djc 2018-11-19
        if request_user.is_anonymous:
            return Response()
        else:
            user = InsightUser.objects.filter(user=request_user).first()
            serialized_user = InsightUserSerializer(user, context={'request': request})
            return Response(serialized_user.data)


class AllowedByEmail(BasePermission):
    """For repositories, be sure user's email is on the allowed list"""

    def has_object_permission(self, request, view, obj):
        # Assumes obj is a Repository
        return obj.allow_access(get_user_email(request))


class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all().order_by('name')
    serializer_class = RepositorySerializer

    def get_permissions(self):
        # We want to append one more to the defaults, in the case
        # that we are doing authentication at all.
        ret = [p() for p in self.permission_classes]

        if settings.ENABLE_AUTH:
            ret.append(AllowedByEmail())

        return ret

    def get_queryset(self):
        if settings.ENABLE_AUTH:
            # Have to get weird here, query sets want to do things in terms of DB
            # queries, so figure out what we want via objects and translate
            # back to DB world with query set stuff
            email = get_user_email(self.request)

            allowed_repos = (repo for repo in Repository.objects.all() if repo.allow_access(email))
            ids = list(map(lambda repo: repo.id, allowed_repos))

            return Repository.objects.filter(id__in=ids).order_by('name')
        else:
            return Repository.objects.all().order_by('name')


class MeasurementViewSet(viewsets.ModelViewSet):
    serializer_class = MeasurementSerializer

    def perform_create(self, serializer):
        repo = Repository.objects.filter(id=self.kwargs['repo']).first()
        serializer.save(repository=repo)

    def get_queryset(self):
        repo = self.kwargs['repo']
        return Measurement.objects.filter(repository=repo).exclude(architecture_type='UNDEFINED').order_by('date')


# Don't let API user create component measurements
class ComponentMeasurementViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ComponentMeasurementSerializer

    def get_queryset(self):
        measurement = self.kwargs['measurement']
        return ComponentMeasurement.objects.filter(measurement=measurement)


class MeasurementScoreViewSet(viewsets.ModelViewSet):
    serializer_class = MeasurementScoreSerializer

    def perform_create(self, serializer):
        measurement = Measurement.objects.filter(id=self.kwargs['measurement']).first()
        serializer.save(measurement=measurement)

    def get_queryset(self):
        measurement = self.kwargs['measurement']
        return MeasurementScore.objects.filter(measurement=measurement)


class BenchmarkViewSet(viewsets.ModelViewSet):
    serializer_class = BenchmarkSerializer

    def perform_create(self, serializer):
        repo = Repository.objects.filter(id=self.kwargs['repo']).first()
        serializer.save(repository=repo)

    def get_queryset(self):
        repo = self.kwargs['repo']
        return Benchmark.objects.filter(repository=repo)


class BenchmarkDescriptionViewSet(viewsets.ModelViewSet):
    serializer_class = BenchmarkDescriptionSerializer

    def perform_create(self, serializer):
        repo = Repository.objects.filter(id=self.kwargs['repo']).first()
        serializer.save(repository=repo)

    def get_queryset(self):
        repo = self.kwargs['repo']
        return BenchmarkDescription.objects.filter(repository=repo)