import unittest

import pandas as pd
from pandas import DataFrame

from scoring.unwantedTopics import UNWANTED_TOPICS


def select_cases(df_cases, uloc, topics: str, core: bool, lang_settings, description):
    """ Select similar cases from the given set using the settings and topics
        Assume that topics is a space separated string at this point """

    min_cases = lang_settings['knearest']
    use_topics = lang_settings['use_topics']
    use_core = lang_settings['use_core']

    # Only keep cases where the core type matches
    if use_core:
        df_cases = df_cases[df_cases.core == core]

    # Convert topics string to a list
    topics_list = topic_string_to_list(topics)

    # Select based on topics and loc
    filtered_topics = [x for x in topics_list if x not in UNWANTED_TOPICS]
    if use_topics and len(filtered_topics) > 0:
        df_topics = select_cases_topic(df_cases, filtered_topics)
        df_topics_loc = select_cases_loc(df_topics, uloc, lang_settings)
        if len(df_topics_loc) >= min_cases:  # Enough similar cases based on topics and loc
            description.selection_type = "Topic and Similar LOC"
            return df_topics_loc

    # Select based on ULOC from all
    df_loc = select_cases_loc(df_cases, uloc, lang_settings)
    if len(df_loc) >= min_cases: # Enough similar cases based on loc only
        description.selection_type = "Similar LOC"
        return df_loc

    # Select based on min_cases
    df_nearest = select_cases_knearest(df_cases, min_cases, uloc)
    description.selection_type = "Nearest Projects"

    return df_nearest


def select_cases_knearest(df_cases, min_cases, uloc):
    """ Select the k nearest based on LOC """
    sub_df = df_cases.copy(False)
    sub_df['distance'] = abs(sub_df['useful_lines_of_code_(uloc)'] - uloc)
    return sub_df.nsmallest(min_cases, 'distance')


def select_cases_loc(df_cases, uloc, lang_settings):
    """ Select based on LOC similarity """
    diff = uloc * lang_settings['uloc']
    low = uloc - diff
    high = uloc + diff
    sub_df = df_cases.copy(False)
    sub_df = sub_df[sub_df['useful_lines_of_code_(uloc)'] < high]
    sub_df = sub_df[sub_df['useful_lines_of_code_(uloc)'] > low]

    return sub_df


def select_cases_topic(df_cases, topics: list) -> DataFrame:
    """ Return the subset of cases with matching topics """
    sub_df = df_cases.copy(False)
    sub_df = sub_df.loc[sub_df['topics'].apply(lambda x: topics_in_string(x, topics))]

    return sub_df


def topic_string_to_list(topics: str) -> list:
    """ Convert from the string representation to a a list """
    topic_list = []
    if topics:
        topics = topics.replace('[', '')
        topics = topics.replace(']', '')
        topics = topics.replace("'", "")
        topics = topics.replace(',', ' ')
        if len(topics) > 0:
            topic_list = topics.split(' ')

    return topic_list


def topics_in_string(topic_string: str, topics: list) -> bool:
    """ Return true if one or more items in topics is in the topics string """
    if not str:
        return False

    for topic in topics:
        if topic in topic_string:
            return True

    return False

