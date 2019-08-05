from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.relations import HyperlinkedRelatedField, HyperlinkedIdentityField
from rest_framework.validators import UniqueValidator
from rest_framework_nested.relations import NestedHyperlinkedIdentityField, NestedHyperlinkedRelatedField

from analysis import understand_analysis
from analysis.manager.analysis_manager_factory import get_analysis_manager
from analysis.manager.fake_analysis_manager import FakeAnalysisManager
from analysis.tree_helper import make_tree_map, empty_tree
from cbri.reporting import UserNotification, logger, log_to_repo
from store.requests import get_user_email
from vcs.repo_type import get_repo_type
from .models import *
from .background import create_history, update_repo

# Commonly used
URL = 'url'

# For InsightUser
USER = 'user'
USERNAME = 'username'
PASSWORD = 'password'
EMAIL = 'email'
FIRST_NAME = 'first_name'
LAST_NAME = 'last_name'
ORGANIZATION = 'organization'


class OrganizationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Organization
        fields = (URL, 'name', 'users', 'repositories')


# Need a special serializer since we hold a special User object
class InsightUserSerializer(serializers.HyperlinkedModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email',
                                  validators=[UniqueValidator(queryset=User.objects.all(), message="The specified email address is already in use.")])
    password = serializers.CharField(source='user.password', write_only=True)
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    class Meta:
        model = InsightUser
        fields = (URL, USERNAME, PASSWORD, EMAIL, FIRST_NAME, LAST_NAME, ORGANIZATION)

    def create(self, validated_data):
        # XXX: Handling if things don't go right? I.e. no nested user dict :P
        # -djc 2018-04-23
        user = User.objects.create_user(username=validated_data.get(USER).get(USERNAME),
                                        email=validated_data.get(USER).get(EMAIL),
                                        password=validated_data.get(USER).get(PASSWORD),
                                        first_name=validated_data.get(USER).get(FIRST_NAME),
                                        last_name=validated_data.get(USER).get(LAST_NAME))

        return InsightUser.objects.create(user=user, organization=validated_data.get('organization'))

    def update(self, instance, validated_data):
        user_dict = validated_data.get(USER)
        if user_dict:
            user = instance.user
            user.username = user_dict.get(USERNAME, user.username)
            user.email = user_dict.get(EMAIL, user.email)
            user.first_name = user_dict.get(FIRST_NAME, user.first_name)
            user.last_name = user_dict.get(LAST_NAME, user.last_name)

            new_pass = user_dict.get(PASSWORD)
            if new_pass:
                user.set_password(new_pass)

            user.save()

        instance.organization = validated_data.get(ORGANIZATION, instance.organization)
        instance.save()

        return instance


# Nest location
class RepositorySerializer(serializers.HyperlinkedModelSerializer):
    measurements = HyperlinkedIdentityField(
        view_name='measurement-list',
        lookup_url_kwarg='repo'
    )

    benchmarks = HyperlinkedIdentityField(
        view_name='benchmark-list',
        lookup_url_kwarg='repo'
    )

    benchmarkdescription = HyperlinkedIdentityField(
        view_name='benchmark_description-list',
        lookup_url_kwarg='repo'
    )

    allowed_emails = serializers.ListField(child=serializers.CharField(), required=False, default=[])

    class Meta:
        model = Repository
        fields = (URL, 'id', 'name', 'organization', 'description', 'topics', 'language', 'address',
                  'allowed_emails', 'measurements', 'benchmarks', 'benchmarkdescription', 'token', 'log')
        extra_kwargs = {
            'token': {'write_only': True}
        }

    @staticmethod
    def validate_language(value):
        """ Verify the language of the repo is supported """
        if value not in understand_analysis.SUPPORTED_LANGUAGES:
            msg = "Language " + value + " is not supported by understand"
            logger.warning(msg);
            raise serializers.ValidationError(msg)
        return value

    def get_current_user_email(self):
        """ Return the email listed for the current user """
        return get_user_email(self.context.get("request"))

    def create(self, validated_data):

        # Remove token from print version
        print_data = validated_data.copy()
        print_data['token'] = "..."

        log_msg = "Creating repo: " + str(print_data)
        logger.info(log_msg)

        # Clean up common little problems with address
        address = validated_data.get("address")
        if address:
            if address.endswith("/"):
                address = address[:-1]

            if address.endswith(".git"):
                address = address[:-4]

            validated_data["address"] = address

        # Figure out type of repo from address
        validated_data["type"] = get_repo_type(address, validated_data.get("token"))

        # Add the current user as the only person that can access
        # the new repo til they add more people
        current_user_email = self.get_current_user_email()
        if current_user_email:
            validated_data["allowed_emails"] = [current_user_email,]

        # Add in the log string
        validated_data['log'] = log_msg

        # Make the repo per usual
        repo = Repository.objects.create(**validated_data)
        create_history(str(repo.id), current_user_email)
        return repo


# Helps with logic dealing with the api user passing in measurement data:
# We want to be sure all these fields are included
MEASUREMENT_FIELDS = ('date', 'revision_id', 'architecture_type', 'propagation_cost',
                      'useful_lines_of_code', 'num_classes', 'num_files', 'core_size',
                      'num_files_in_core', 'num_files_overly_complex', 'percent_files_overly_complex',
                      'useful_lines_of_comments', 'useful_comment_density',
                      'duplicate_uloc', 'percent_duplicate_uloc', 'is_core', 'components_str')


class MeasurementSerializer(serializers.HyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(view_name='measurement-detail',
                                         parent_lookup_kwargs={'repo': 'repository__id'})

    repository = HyperlinkedRelatedField(read_only=True, view_name='repository-detail')

    component_measurements = NestedHyperlinkedIdentityField(
        view_name='component-list',
        parent_lookup_kwargs={'repo': 'repository__id'},
        lookup_url_kwarg='measurement',
        read_only=True
    )

    scores = NestedHyperlinkedIdentityField(
        view_name='score-list',
        parent_lookup_kwargs={'repo': 'repository__id'},
        lookup_url_kwarg='measurement'
    )

    is_core = serializers.BooleanField(write_only=True, allow_null=True)

    class Meta:
        model = Measurement
        fields = (URL, 'repository') + MEASUREMENT_FIELDS + ('component_measurements', 'scores', 'revision_id', 'is_baseline')
        extra_kwargs = {
            'components_str': {'write_only': True}
        }

    fake_weeks = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        context = kwargs.get('context', None)
        if context:
            request = kwargs['context']['request']

            if request:
                fake_param = request.data.get('fake_weeks')

                if fake_param:
                    self.fake_weeks = int(fake_param)

    # Turn off required for everything - we expect an empty post
    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            # XXX: Would probably also be nice to mark everything as read
            # only or something, but not worried about it since everything
            # is weird anyway. -djc 2018-06-05
            field.required = False
        return fields

    def get_current_user_email(self):
        """ Return the email listed for the current user """
        return get_user_email(self.context.get("request"))


    def create(self, validated_data):
        # The view figures out the right repo for us and adds it to validated_data
        repo = validated_data['repository']
        measurement = None

        if len(validated_data) > 1:
            # normal API type call to post a given measurement
            if not all(k in validated_data for k in MEASUREMENT_FIELDS):
                raise ValidationError('All fields must be provided, or no fields.')

            logger.info("Creating fully specified measurement")
            measurement = Measurement.create_from_dict(repo, validated_data)

        else:
            # No fields provided - either do fake or understand generation
            # has it been set and greater than 0
            if self.fake_weeks:
                logger.info("Creating %s fake measurements" % self.fake_weeks)
                faker = FakeAnalysisManager(repo, self.fake_weeks)
                history = faker.make_history()

                if history:
                    # Return the most recent fake measurement
                    measurement = history[-1]
            else:
                # Create an empty measurement with a task to fill it in later
                faker = FakeAnalysisManager(repo, 1)
                measurement = faker.make_zero_measurement()
                update_repo(str(repo.id), str(measurement.id), self.get_current_user_email())

        return measurement


class MeasurementScoreSerializer(serializers.HyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(view_name='score-detail',
                                         parent_lookup_kwargs={'measurement': 'measurement__id',
                                                               'repo': 'measurement__repository__id'})

    measurement = NestedHyperlinkedRelatedField(read_only=True, view_name='measurement-detail',
                                                parent_lookup_kwargs={'repo': 'repository__id'})

    class Meta:
        model = MeasurementScore
        fields = (URL, 'measurement', 'name', 'grade', 'grade_value')


class ComponentMeasurementSerializer(serializers.HyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(view_name='component-detail',
                                         parent_lookup_kwargs={'measurement': 'measurement__id',
                                                               'repo': 'measurement__repository__id'})

    measurement = NestedHyperlinkedRelatedField(read_only=True, view_name='measurement-detail',
                                                parent_lookup_kwargs={'repo': 'repository__id'})

    class Meta:
        model = ComponentMeasurement
        fields = (URL, 'measurement', 'node', 'parent', 'useful_lines', 'threshold_violations', 'full_name')


class BenchmarkSerializer(serializers.HyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(view_name='benchmark-detail',
                                         parent_lookup_kwargs={'repo': 'repository__id'})
    repository = HyperlinkedRelatedField(read_only=True, view_name='repository-detail')

    class Meta:
        model = Benchmark
        fields = (URL, 'repository', 'measurement_name', 'percentile_25', 'percentile_50',
                  'upper_threshold', 'num_cases')


class BenchmarkDescriptionSerializer(serializers.HyperlinkedModelSerializer):
    url = NestedHyperlinkedIdentityField(view_name='benchmark_description-detail',
                                         parent_lookup_kwargs={'repo': 'repository__id'})

    repository = HyperlinkedRelatedField(read_only=True, view_name='repository-detail')

    class Meta:
        model = BenchmarkDescription
        fields = (URL, 'repository', 'num_projects', 'selection_type', 'date', 'project_data')