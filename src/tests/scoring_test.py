
import json
import pandas as pd

import django
from django.utils import timezone

from store.models import BenchmarkDescription, Repository, RepoType
from scoring.benchmarks import BenchmarkGenerator
from scoring.scores import ScoreGenerator
from scoring.similarity import topic_string_to_list, select_cases_topic

class SimilarityTest(django.test.TestCase):

    def test_conversion(self):
        topics = "A B-C D"
        l = topic_string_to_list(topics)
        print(l)
        self.assertTrue(len(l) == 3)

    def test(self):
        raw_data = {'name': ['A', 'B', 'C'],
                    'topics': ["['USA']", "['USA', 'France', 'UK']", "['UK']"],}
        df = pd.DataFrame(raw_data, columns=['name', 'topics'])
        cases = select_cases_topic(df, ['USA', 'java'])
        print(cases)
        self.assertTrue(cases.shape[0] == 2)


class BenchmarkTest(django.test.TestCase):
    """ Test that benchmarks are being created correctly """

    def print_benchmarks(self, list, description: BenchmarkDescription):
        for item in list:
            print(item)
            column_list = description.get_project_data_column(item['measurement_name'])
            print(column_list)

    def test(self):
        generator = BenchmarkGenerator(csv_dir="./src/scoring/resources/")
        repo = Repository.objects.create(name="Test", type=RepoType.FILE, description="None" )
        description = BenchmarkDescription.objects.create(repository=repo, date=timezone.now())

        list, grades = generator.get_benchmarks(40000, "Java", "android", True, description)
        print("Java")
        self.print_benchmarks(list, description)
        print(grades)
        list, grades = generator.get_benchmarks(120000, "C", "", False, description)
        print("C")
        self.print_benchmarks(list, description)
        print(grades)
        list, grades = generator.get_benchmarks(120000, "C++", "", False, description)
        print("C++")
        self.print_benchmarks(list, description)
        print(grades)

        try:
            list, grades = generator.get_benchmarks(40000, "Fortran", "", True, description)
            assert(False)
        except RuntimeError:
            print("Received runtime error as expected for unknown language.")
            assert(True)


class ScoreTest(django.test.TestCase):
    def test(self):

        generator = BenchmarkGenerator(csv_dir="./src/scoring/resources/")
        repo = Repository.objects.create(name="Test", type=RepoType.FILE, description="None")
        description = BenchmarkDescription.objects.create(repository=repo, date=timezone.now())

        benchmarks, grades = generator.get_benchmarks(34516, "Java", "", False, description)
        print("Java")
        for b in benchmarks:
            print(b)
        print(grades)

        measurement = dict()
        measurement['useful_comment_density'] = 18.4

        measurement['percent_files_overly_complex'] = 1.9
        measurement['percent_duplicate_uloc'] = 16.15

        measurement['core_size'] = 10.2
        measurement['propagation_cost'] = 14.4
        measurement['is_core'] = False

        scores, values, explanations = ScoreGenerator().get_scores(benchmarks, description, grades, measurement)
        print(json.dumps(scores, sort_keys=True, indent=4))
        print(values)
        print(json.dumps(explanations, sort_keys=True, indent=4))