import os

import numpy as np
import pandas as pd
from pandas import DataFrame

from scoring.languageSettings import get_language_settings
from scoring.similarity import select_cases
from cbri.reporting import logger

"""
Fields included in the generated benchmarks. Comments are for MIN_MEASUREMENT FIELDS - reverse for MAX_MEASUREMENT_FIELDS
BENCHMARK_FIELDS = ['measurement_name',  # from MEASUREMENT_FIELDS
                    'percentile_25',  # start of green
                    'percentile_50',  # end of green / start of yellow
                    'upper_threshold' # end of yellow
                    'number_cases']
"""

# If someone wants safe defaults, use these values -djc 2018-04-05
SAFE_LOC = 120000
SAFE_LANGUAGE = 'Java'


class BenchmarkGenerator:

    MIN_MEASUREMENT_FIELDS = ['core_size', 'propagation_cost', 'percent_files_overly_complex', 'percent_duplicate_uloc']

    MAX_MEASUREMENT_FIELDS = ['useful_comment_density']

    SUPPORTED_LANGUAGES = {'Java':'java.csv',
                           'C++':'cpp.csv',
                           'C':'c.csv',
                           'C#':'csharp.csv'}

    def __init__(self, csv_dir="resources"):
        self.csv_dir = csv_dir

    def get_benchmarks(self, uloc: int, language: str, topics: str, core: bool, description) -> list:
        """
        Return a list of benchmarks for this repo, based on predicted or actual lines of code,
        the language of the repo, and the identified topics
        """

        # Load in the case data for the given language
        df_cases = self.load_cases(language)

        grade_percentiles = self.get_grade_percentiles(df_cases)

        # Load in the similarity settings for the language
        lang_settings = get_language_settings(language)

        benchmarks = self.get_benchmarks_for_dataframe(df_cases, uloc, topics, core, lang_settings, description)

        # save the changes to the benchmark description
        description.save()

        if len(benchmarks) == 0:
            raise RuntimeError("Unable to create benchmarks - no similar cases found.")

        return benchmarks, grade_percentiles

    def get_benchmarks_for_dataframe(self, df_cases: DataFrame, uloc, topics: str, core: bool, lang_settings: dict, description) -> list:

        # Determine the set of similar cases
        df_cases = select_cases(df_cases, uloc, topics, core, lang_settings, description)

        # add data to the description object
        description.num_projects = len(df_cases)
        description_columns = ['project_name', 'useful_lines_of_code_(uloc)', 'core', 'core_size', 'propagation_cost',
                               'percent_files_overly_complex', 'percent_duplicate_uloc', 'useful_comment_density',
                               'overall_score','architecture_score','complexity_score','clarity_score',
                               'topics'] # Front end code assumes topics is last.
        description.project_data = df_cases[description_columns].to_csv()

        if len(df_cases) < 1:
            logger.info("No similar cases found for ULOC ", uloc)
            return []

        # Create benchmarks from cases
        return self.create_benchmarks(df_cases, lang_settings)

    def load_cases(self, language):
        """ Load in the case data for the given language into a dataframe """
        if not language in self.SUPPORTED_LANGUAGES.keys():
            raise RuntimeError("Unable to create benchmarks - " + language + " is not a supported language.")
        else:
            path = os.path.join(self.csv_dir, self.SUPPORTED_LANGUAGES[language])
            df_cases = pd.read_csv(path)
        return df_cases

    def create_benchmarks(self, df_cases, sim_settings) -> list:
        """ Return a set of benchmarks for each item in measurement fields"""
        benchmarks = []
        for measurement_name in self.MIN_MEASUREMENT_FIELDS:
            benchmark = dict()
            benchmark['measurement_name'] = measurement_name
            benchmark['percentile_25'] = self.getPercentile(df_cases, measurement_name, 25)
            benchmark['percentile_50'] = self.getPercentile(df_cases, measurement_name, 50)
            benchmark['upper_threshold'] = self.getPercentile(df_cases, measurement_name, sim_settings['upper_threshold'])
            benchmark['num_cases'] = len(df_cases)
            benchmarks.append(benchmark)

        for measurement_name in self.MAX_MEASUREMENT_FIELDS:
            benchmark = dict()
            benchmark['measurement_name'] = measurement_name
            benchmark['percentile_25'] = self.getPercentile(df_cases, measurement_name, 25) #100 - sim_settings['upper_threshold'])
            benchmark['percentile_50'] = self.getPercentile(df_cases, measurement_name, 50)
            benchmark['upper_threshold'] = self.getPercentile(df_cases, measurement_name, 75)
            benchmark['num_cases'] = len(df_cases)
            benchmarks.append(benchmark)
        return benchmarks

    def getPercentile(self, df_cases, measurement_name, percentile):
        """ Return the percentile value of the given column for the given cases """
        temp_df = df_cases[measurement_name].dropna()
        return np.percentile(temp_df, [percentile])


    def get_grade_percentiles(self, df_cases):
        """
        :return: A dict of dicts. For each score type ('architecture', 'complexity', 'clarity', 'overall') return a dict of A, B, C, D
        """
        grades = dict()

        list = ['architecture', 'complexity', 'clarity', 'overall']
        for index, item in enumerate(list):
            sub = dict()
            grades[item] = sub
            col = item + "_score"
            sub['A'] = df_cases[col].quantile(0.75)
            sub['B'] = df_cases[col].quantile(0.5)
            sub['C'] = df_cases[col].quantile(0.25)
            sub['D'] = df_cases[col].quantile(0.05)

        return grades