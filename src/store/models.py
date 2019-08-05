import uuid
from io import StringIO

import pandas as pd

from django.contrib.auth.models import User
from django.db import models
from django_bleach.models import BleachField
from django.utils import timezone
from enumfields import EnumField
from multi_email_field.fields import MultiEmailField

from analysis.tree_helper import make_tree_map, empty_tree
import scoring.benchmarks as benchmarks
from scoring.scores import ScoreGenerator
from vcs.repo_type import RepoType
from cbri.reporting import logger

DEFAULT_CHAR_LENGTH = 200

# TODO: DB Indexing? -djc 2018-02-26


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = BleachField(max_length=DEFAULT_CHAR_LENGTH)

    def __str__(self):
        return self.name


class InsightUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, related_name='users', null=True, on_delete=models.PROTECT)

    def __str__(self):
        return self.user.get_username()


class Repository(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, related_name='repositories', null=True, on_delete=models.PROTECT)
    name = BleachField(max_length=DEFAULT_CHAR_LENGTH)
    # Not exposed to API
    # Attached to the RepoType enum. Doesn't need to be a BleachField since not exposed to user.
    type = EnumField(RepoType)
    description = BleachField()
    token = BleachField(blank=True, max_length=DEFAULT_CHAR_LENGTH)
    # Console-like logging
    log = BleachField(max_length=DEFAULT_CHAR_LENGTH, default="")
    # Space separated list of topics as seen on github
    topics = BleachField(blank=True)
    # TODO: Use choices rather than free text? -djc 2018-02-26
    language = BleachField(max_length=DEFAULT_CHAR_LENGTH)
    address = BleachField(blank=True, max_length=DEFAULT_CHAR_LENGTH)
    # Users with these email addresses can access the repo, or any user
    # if empty
    allowed_emails = MultiEmailField()

    class Meta:
        verbose_name_plural = 'Repositories'

    def __str__(self):
        return self.name

    def allow_access(self, email):
        """Should we allow access to a user with the given email?"""
        ret = False

        if self.allowed_emails:
            if email:
                ret = email in self.allowed_emails
        else:  # if no list of emails, allow
            ret = True

        return ret

    def get_benchmarks(self, uloc: int, core: bool) -> list:
        """ Return a list of benchmarks for this repo, based on predicted or actual lines of code """
        generator = benchmarks.BenchmarkGenerator('src/scoring/resources/')
        BenchmarkDescription.objects.filter(repository=self).delete()
        description = BenchmarkDescription.objects.create(repository=self, date=timezone.now())
        try:
            a, b = generator.get_benchmarks(uloc, self.language, self.topics, core, description)
            return a, b, description
        except RuntimeError as error:
            # We expect these values to always work, and assume giving a default is the right thing to do :P
            # -djc 2018-04-05
            logger.error("Unable to create benchmarks: " + str(error))

    def reset_benchmarks(self, uloc: int, core: bool) -> list:
        """Clear out existing benchmarks attached to this repository and create
        new ones based on predicted or actual lines of code"""
        Benchmark.objects.filter(repository=self).delete()

        new_benchmarks = []

        benchmark_list, grade_percentiles, description = self.get_benchmarks(uloc, core)
        for benchmark_dict in benchmark_list:
            benchmark_dict['repository'] = self
            bm = Benchmark.objects.create(**benchmark_dict)
            new_benchmarks.append(bm)

        return new_benchmarks, grade_percentiles, description


class Measurement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.ForeignKey(Repository, related_name='measurements', on_delete=models.CASCADE)
    date = models.DateTimeField()
    # TODO: Use choices rather than free text? -djc 2018-02-26
    architecture_type = BleachField(max_length=DEFAULT_CHAR_LENGTH)
    propagation_cost = models.FloatField()
    useful_lines_of_code = models.IntegerField()
    num_classes = models.IntegerField()
    num_files = models.IntegerField()
    num_files_in_core = models.IntegerField()
    core_size = models.FloatField()
    num_files_overly_complex = models.IntegerField()
    percent_files_overly_complex = models.FloatField()
    useful_lines_of_comments = models.IntegerField()
    useful_comment_density = models.FloatField()
    duplicate_uloc = models.IntegerField()
    percent_duplicate_uloc = models.FloatField()
    revision_id = BleachField(max_length=DEFAULT_CHAR_LENGTH, default="Not set")
    is_baseline = models.BooleanField(default=False)
    # Convenience for scoring logic, write only for the API
    is_core = models.BooleanField()
    components_str = models.TextField(default="", blank=True)

    def __str__(self):
        return self.date.strftime("%B %d, %Y")

    def create_component_measurements(self, component_dicts: list):
        """Turn a list of component measurements represented as dicts into ComponentMeasurement
        objects attached to this measurement.
        Safe if component_dicts is None."""
        if component_dicts:
            for component_dict in component_dicts:
                component_dict['measurement'] = self
                ComponentMeasurement.objects.create(**component_dict)

    def create_scores(self):
        """Creates MeasurementScores for this Measurement based on its Repo's Benchmarks"""

        # XXX: Temporary. For now we want to update benchmarks every time
        # we score, but we probably want a separate path for updating
        # benchmarks. -djc 2018-04-05

        benchmarks, grade_percentiles, description = self.repository.reset_benchmarks(self.useful_lines_of_code, self.is_core)
        benchmark_dicts = [b.__dict__ for b in benchmarks]
        (scores_dict, values_dict, explanations) = ScoreGenerator().get_scores(benchmark_dicts, description, grade_percentiles, self.__dict__)

        for name in scores_dict:
            score_to_make = {'measurement': self,
                             'name': name,
                             'grade': scores_dict[name],
                             'grade_value': float(values_dict[name])}

            MeasurementScore.objects.create(**score_to_make)

    @classmethod
    def create_from_dict(cls, repo: Repository, metrics: dict):
        """Create a Measurement object in the database and return it,
        with the given fields and component measurements.
        metrics is expected to not be None, and to use keys found in
        analysis code."""

        # Field names the model expects
        model_fields = {'repository': repo}
        measurement = None

        if 'num_files' in metrics:
            # Jenkins plugin provides a dict with all of the correct fields, but no component measures
            model_fields = metrics
            measurement = Measurement.objects.create(**model_fields)
            treemapdata = metrics.get('components_str')
            # Create the treemap, making an empty one if data not passed in by Jenkins
            if treemapdata:
                metrics['Components'] = make_tree_map(treemapdata)
            else:
                metrics['Components'] = make_tree_map(empty_tree)
        else:
            # Convert from Understand/Github fields to CBRI fields, along with the treemap component measures
            num_files = metrics["Files"]
            # Percentage
            core_size = metrics["Core Size"]
            num_files_in_core = str(int(round(int(num_files) * float(core_size) / 100)))

            uloc = int(metrics.get("Useful Lines of Code (ULOC)"))
            comment_density = metrics.get("Useful Comment Density")
            num_comment_lines = str(int(round(uloc * float(comment_density) / 100)))

            perc_complex = metrics.get("Overly Complex Files", 0)
            num_complex = str(int(round(int(num_files) * float(perc_complex) / 100)))

            model_fields['date'] = metrics.get("date")
            model_fields['architecture_type'] = metrics.get("Architecture Type")
            model_fields['propagation_cost'] = metrics.get("Propagation Cost")
            model_fields['useful_lines_of_code'] = uloc
            # XXX: Sometimes Understand will provide blank values, which mean 0
            # we might want to replicate this default for other fields? -djc 2018-06-12
            model_fields['num_classes'] = metrics.get("Classes", 0)
            model_fields['num_files'] = num_files
            model_fields['num_files_in_core'] = num_files_in_core
            model_fields['core_size'] = core_size
            model_fields['num_files_overly_complex'] = num_complex
            model_fields['percent_files_overly_complex'] = perc_complex
            model_fields['useful_lines_of_comments'] = num_comment_lines
            model_fields['useful_comment_density'] = comment_density
            model_fields['is_core'] = metrics.get("core")
            model_fields['duplicate_uloc'] = metrics.get("duplicate_uloc")
            model_fields['percent_duplicate_uloc'] = metrics.get("percent_duplicate_uloc")
            model_fields['revision_id'] = metrics.get("revision_id")
            if metrics.get("is_baseline"):
                model_fields['is_baseline'] = metrics.get("is_baseline")

            measurement = Measurement.objects.create(**model_fields)

        # Make component measurements
        measurement.create_component_measurements(metrics.get("Components"))

        # XXX: This makes new benchmarks for each measurement. We want to be smarter
        # and use the one right set of benchmarks against all measurements? -djc 2018-06-11
        measurement.create_scores()

        return measurement


class ComponentMeasurement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    measurement = models.ForeignKey(Measurement, related_name='component_measurements', on_delete=models.CASCADE)
    node = BleachField(max_length=DEFAULT_CHAR_LENGTH)
    parent = BleachField(max_length=DEFAULT_CHAR_LENGTH, blank=True)
    useful_lines = models.IntegerField()
    threshold_violations = models.IntegerField()
    full_name = BleachField(max_length=DEFAULT_CHAR_LENGTH)

    def __str__(self):
        return "ComponentMeasurement[%s]" % self.node


class MeasurementScore(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    measurement = models.ForeignKey(Measurement, related_name='scores', on_delete=models.CASCADE)
    name = BleachField(max_length=DEFAULT_CHAR_LENGTH)
    grade = BleachField(max_length=DEFAULT_CHAR_LENGTH)
    grade_value = models.FloatField()

    def __str__(self):
        return "Score[%s = %s (%.1f)]" % self.name, self.grade, self.grade_value


class Benchmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.ForeignKey(Repository, related_name='benchmarks', on_delete=models.CASCADE)
    measurement_name = BleachField(max_length=DEFAULT_CHAR_LENGTH)
    percentile_25 = models.FloatField()
    percentile_50 = models.FloatField()
    upper_threshold = models.FloatField()
    num_cases = models.IntegerField()

    def __str__(self):
        return "Benchmark[%s]" % self.measurement_name


class BenchmarkDescription(models.Model):
    """ A description of the how the benchmarks were generated """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    repository = models.ForeignKey(Repository, related_name='benchmark_descriptions', on_delete=models.CASCADE)

    num_projects = models.IntegerField(default=0)
    selection_type = BleachField(max_length=DEFAULT_CHAR_LENGTH, default="None")
    date = models.DateTimeField()
    project_data = BleachField(default="") # table of data in csv format

    def __str__(self):
        return "BenchmarkDescription[%s]" % self.selection_type

    def get_project_data_column(self, column_name):
        """ returns a column of data that corresponds to the given measurement name"""
        df = pd.read_csv(StringIO(self.project_data))
        if column_name in df:
            return df[column_name].tolist()
        else:
            return None
