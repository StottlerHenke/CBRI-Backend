
import configparser

def get_default_config_parser():
    """
    Creates a ConfigParser with default settings.
    """
    config = configparser.ConfigParser(
        allow_no_value=True, #Used for "list-like" sections
        interpolation=None, #Avoids interpolation when % is present in values
    )

    #Overrides the default of case insensitive option names.
    config.optionxform = str

    return config
