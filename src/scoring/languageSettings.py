
SIMILARITY_FIELDS = ['upper_threshold', 'uloc_diff', 'knearest', 'use_topics']

def get_language_settings(lang : str) -> dict:
    '''
    :return the settings based on the language. For now, all languages use the same settings
    '''
    sim_settings = dict()

    sim_settings['upper_threshold'] = 75  # default value
    sim_settings['uloc'] = 0.4  # default_value
    sim_settings['knearest'] = 25  # default_value
    sim_settings['use_topics'] = True  # default_value
    sim_settings['use_core'] = False  # default_value

    return sim_settings