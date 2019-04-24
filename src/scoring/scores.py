from scipy import stats


class ScoreGenerator:

    SCORING_FIELDS = ['architecture', 'complexity', 'clarity', 'overall', 'explanation']

    def get_scores(self, benchmarks: list, description, grade_percentiles, measurement: dict) -> dict:
        """ Given a list of benchmarks and a measurement, return:
        score - dict of letter grades
        values - dict of numeric values
        explanation - dict of explanations """

        score = dict()
        values = dict()
        explanations = dict()

        precision = 2 # Round to this many decimal points.

        clarity = self.get_clarity_score(benchmarks, description, measurement, explanation=explanations) # 0 or 1
        clarity = round(clarity, precision)
        values['clarity'] = clarity
        score['clarity'] = self.get_clarity_letter(clarity, grade_percentiles['clarity'])

        complexity = self.get_complexity_score(benchmarks, description, measurement, explanation=explanations) # 0, 1, or 2
        complexity = round(complexity, precision)
        values['complexity'] = complexity
        score['complexity'] = self.get_complexity_letter(complexity, grade_percentiles['complexity'])

        arch = self.get_architecture_score(benchmarks, description, measurement, explanation=explanations) # 0, 1, 2, or 3
        arch = round(arch, precision)
        values['architecture'] = arch
        score['architecture'] = self.get_architecture_letter(arch, grade_percentiles['architecture'])

        overall = clarity + complexity + arch
        overall = round(overall, precision)
        values['overall'] = overall
        score['overall'] = self.get_overall_letter(overall, grade_percentiles['overall'])

        return score, values, explanations

    def __get_letter(self, score, grades):
        """
        A letter grade based on the distribution of scores found in the benchmark data set.
        :return:
        """
        if score > grades['A']:
            grade = 'A'
        elif score > grades['B']:
            grade = 'B'
        elif score > grades['C']:
            grade = 'C'
        elif score > grades['D']:
            grade = 'D'
        else:
            grade = 'F'
        return grade

    def get_clarity_letter(self, score, grades):
        """ Clarity is a single score randing from 0-1 """
        grade = self.__get_letter(score, grades)
        return grade

    def get_complexity_letter(self, score, grades):
        """ Complexity combines two scores, ranging from 0-2 """
        grade = self.__get_letter(score, grades)
        return grade

    def get_architecture_letter(self, score, grades):
        """ Architecture combines two scores, ranging from 0-2 """
        grade = self.__get_letter(score, grades)
        return grade

    def get_overall_letter(self, score, grades):
        """ Overall combines all scores, ranging from 0-5"""
        grade = self.__get_letter(score, grades)
        return grade

    def compare_to_upper(self, benchmarks, description, measurement, field, explanation={}):
        """ Score a measurement relative to the benchmarks - lower score is better """
        field_value = float(measurement[field])

        score = 0
        benchmark = self.get_benchmark(benchmarks, field)
        if benchmark:
            # return the inverted percentile - higher is better
            data_column = description.get_project_data_column(field)
            percentile = stats.percentileofscore(data_column, field_value)
            score = (100 - percentile)/100
            explanation[field] = field + " percentile: " + str(percentile) + "(+" + str(score) + ")"
        else:
            explanation[field]= "No benchmark found for: " + field

        return score

    def get_clarity_score(self, benchmarks, description, measurement, explanation={}):
        """ Score comment density relative to the benchmarks - higher score is better """
        field = 'useful_comment_density'
        field_value = float(measurement[field])

        clarity = 0
        benchmark = self.get_benchmark(benchmarks, field)
        if benchmark:
            # return the percentile - higher is already better so do not invert
            data_column = description.get_project_data_column(field)
            percentile = stats.percentileofscore(data_column,field_value)
            clarity = percentile/100
            explanation[field] = field + " percentile: " + str(percentile) + "(+" + str(clarity) + ")"
        else:
            explanation[field]= "No benchmark found for: " + field

        return clarity

    def get_complexity_score(self, benchmarks, description, measurement, explanation={}):
        complexity = 0;
        complexity += self.compare_to_upper(benchmarks, description, measurement, 'percent_files_overly_complex',
                                            explanation=explanation)
        complexity += self.compare_to_upper(benchmarks, description, measurement, 'percent_duplicate_uloc',
                                            explanation=explanation)
        return complexity

    def get_architecture_score(self, benchmarks, description, measurement, explanation={}):
        arch = 0
        arch += self.compare_to_upper(benchmarks, description, measurement, 'propagation_cost', explanation)

        if measurement['is_core'] is False:
            arch += 1.0
            explanation['core'] = "Core type of architecture is False, full credit for core size"
        else:
            explanation['core'] = "Core type of architecture is True, measuring core size"
            arch += self.compare_to_upper(benchmarks, description, measurement, 'core_size', explanation)

        return arch

    def get_benchmark(self, benchmarks, measurement_name):
        """ Get the benchmark corresponding to the given measurement name """
        for benchmark in benchmarks:
            if benchmark['measurement_name'] == measurement_name:
                return benchmark
        return None