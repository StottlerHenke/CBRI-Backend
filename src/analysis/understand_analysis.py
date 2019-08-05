
import html
import json
import os
import re
import shlex
import shutil
import stat
import subprocess

import django.utils.timezone as timezone
from lxml import html

from cbri.reporting import logger

CBRI_PLUGIN_DIR = "./src/analysis/"

REPO_CODE_BASE_DIR = "./temp/code/"
REPO_REPORTS_BASE_DIR = "./temp/data/"
REPO_UNDERSTAND_BASE_DIR = "./temp/code/"

# Locations of executables for und and uperl
UND_ENV_VAR = "CBRI_UND"
UPERL_ENV_VAR = "CBRI_UPERL"

SUPPORTED_LANGUAGES = ["Ada", "Assembly", "C", "C#", "C++", "Cobol", "FORTRAN",
                       "Java", "JOVIAL", "Delphi", "Pascal", "Python",
                       "VHDL", "Visual", "Web"]

# Depending on version of Understand, it might say one of these things if license
# doesn't work. -djc 2018-11-01
UNDERSTAND_LICENSE_PROBLEMS = ["This license has expired.", "The provided installation Id does not match our records."]

UNDERSTAND_ULOC_FIELD = 'Useful Lines of Code (ULOC)'

# I'm not sure what the purpose of this list is since it isn't used.
# But it seems useful to keep around, these are the field names in
# Understand output. -djc 2018-11-05
UNDERSTAND_FIELDS = ["Project Name",
                     UNDERSTAND_ULOC_FIELD, "Software Lines of Code (SLOC)", "Duplicate Useful Lines of Code",
                     "Classes", "Files",
                     "Architecture Type", "Core", "Core Size", "Propagation Cost",
                     "Overly Complex Files", "Useful Comment Density"]

# Map from field names in Understand to keys that will match fields in a
# Measurement object. -djc 2018-11-05
UNDERSTAND_TO_SCORING = {"Useful Comment Density": "useful_comment_density",
                         "Core Size": "core_size",
                         "Propagation Cost": "propagation_cost",
                         "Overly Complex Files": "percent_files_overly_complex",
                         "Core": "core",
                         "Duplicate Useful Lines of Code": "duplicate_uloc"
                         }


def get_clean_project_name(project_name: str):
    """ Users can create a project name that does not translate into a file name.
        This method converts from arbitrary text into a valid name """
    return "".join(x for x in project_name if x.isalnum())


def get_metrics_for_project_and_translate_fields(project_name, data_dir, date=None, revision_id=None):
    """ Get metrics for a project and translate field names
        date should only be set when generating history; otherwise leave blank to use the current date for updates
        revision_id will only be set by vcs helpers """

    metrics = get_metrics_for_project(project_name, data_dir, {})

    # XXX: More robust check for failed analysis? -djc 2018-09-25
    success = True

    if not metrics:
        success = False
    else:
        uloc = metrics.get(UNDERSTAND_ULOC_FIELD, '0')
        if uloc == '0':
            success = False

    if not success:
        raise RuntimeError("Static code analysis did not produce meaningful results. A common cause is selecting a language that doesn't match the project.")

    add_tree_map_data(project_name, metrics, data_dir)
    metrics = append_translated_field_names(metrics)

    if not date:
        date = timezone.now().replace(microsecond=0)
    metrics['date'] = date

    if revision_id:
        metrics['revision_id'] = revision_id

    return metrics


def append_translated_field_names(metrics: dict) -> dict:
    """ Copy into the fields expected by the benchmark, but keep the user-friendly fields for export """
    for key, value in UNDERSTAND_TO_SCORING.items():
        metrics[value] = metrics[key]

    # Syntactic sugar for uloc (Jupyter)
    metrics['uloc'] = metrics[UNDERSTAND_ULOC_FIELD]
    # Calculate percent duplicate code
    metrics['percent_duplicate_uloc'] = (float(metrics['duplicate_uloc']) / float(metrics['uloc'])) * 100
    return metrics


def get_metrics_for_project(project_name, data_dir, output):

    if not os.path.isdir(data_dir):
        raise RuntimeError("Could not access understand results in directory: " + data_dir)

    # INTENTIONALLY USING FORWARD SLASH, THIS WORKS FOR WINDOWS
    # DO NOT CHANGE TO OS.PATH STUFF. UNDERSTAND WANTS FORWARD SLASHES
    # EVEN IN WINDOWS. -DJC 2018-06-08
    index_file = data_dir + '/index.html'
    if not os.path.isfile(index_file):
        raise RuntimeError("Understand results not found: ", index_file)

    with open(index_file) as htmlfile:
        logger.info("\tGathering metrics: " + index_file)

        output['Project Name'] = project_name
        # grab <head><script>
        block = html.tostring(html.parse(htmlfile).getroot()[0][0])
        myStr = block.decode()
        metrics = json.loads(myStr.split("metrics=")[1].split(';')[0])

        # Convert from name/value tags to dictionary
        metricsDict = {}
        for m in metrics:
            name = m['name']
            val = m['value']
            # If blank String, don't put it in so it's easier to catch later -djc 2018-03-19
            if name != "Project Name" and val:
                metricsDict[name] = val.replace('%', '')

        # Remove percentage information and only show core or central as appropriate
        core = True
        archType = metricsDict['Architecture Type']
        if archType == 'Hierarchical' or archType == 'Multi-Core':
            core = False;
        output['Core'] = core

        if core:
            for key, value in metricsDict.items():
                if key == "Overly Complex Central Files" or key == "Central Size":
                    continue  # i.e. don't print these two
                output[key] = value
        else:  # Swap Central into Core
            for key, value in metricsDict.items():
                if key == "Overly Complex Core Files" or key == "Core Size":
                    continue
                elif key == "Overly Complex Central Files":
                    output["Overly Complex Core Files"] = value
                elif key == "Central Size":
                    output["Core Size"] = value
                else:
                    output[key] = value

    return output


def add_tree_map_data(project: str, output: dict, data_dir: str):
    """ Pull in the tree map data and add to output """
    nodes = []

    try:
        with open(data_dir + "/treemap.html") as file:
            # Pull node info out
            # The first thing that looks like a node is just the names of the fields, ignore that
            first_node = True
            node_pattern = re.compile('\[([^\]]+)\]')

            for line in file:
                line = line.replace("'", "").replace('\\\\', '/')
                match = node_pattern.search(line)

                if match:
                    node_info = match.group(1).split(',')
                    if len(node_info) == 5:
                        if first_node:
                            first_node = False
                        else:
                            parent = node_info[1]
                            if 'null' == parent:
                                parent = ''

                            # These strings should match the field names in models.ComponentMeasurement
                            node_dict = {'node': node_info[0],
                                         'parent': parent,
                                         'useful_lines': node_info[2],
                                         'threshold_violations': node_info[3],
                                         'full_name': node_info[4]}

                            nodes.append(node_dict)
    except IOError as e:
        logger.warning("*** No tree map file for: " + project + " " + str(e))

    output["Components"] = nodes


def analyze_repo(repo, code_base_dir, data_base_dir, und_base_dir):
    """ Analyze the repo in the code_dir, store the understand file in the und_dir,
    and output the results to the data_dir """
    code_dir, data_dir, und_dir = get_directories_for_project(repo.name, code_base_dir, data_base_dir, und_base_dir)
    run_understand(repo.name, repo.language, code_dir, data_dir, und_dir)
    # return directories so the caller can delete
    return code_dir, data_dir, und_dir


def get_directories_for_project(project_name, code_base_dir, data_base_dir, und_base_dir):
    # INTENTIONALLY NOT USING OS.PATH STUFF, THIS WORKS FOR WINDOWS.
    # DO NOT CHANGE TO OS.PATH STUFF. UNDERSTAND WANTS FORWARD SLASHES
    # EVEN IN WINDOWS. -DJC 2018-06-08
    clean_project_name = get_clean_project_name(project_name);

    code_dir = code_base_dir + clean_project_name
    data_dir = data_base_dir + clean_project_name
    und_dir = und_base_dir + clean_project_name

    # Ensure the directories exist; create if needed.
    # Don't make the code directory, it will be made on cloning
    if not os.path.isdir(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    # Understand db now lives in the code directory, so do not create it.
    # if not os.path.isdir(und_dir):
    #     os.makedirs(und_dir, exist_ok=True)

    return code_dir, data_dir, und_dir


def run_understand(project_name, lang, code_dir, data_dir, und_dir):
    # Check for the environment variables
    und = os.getenv(UND_ENV_VAR)
    uperl = os.getenv(UPERL_ENV_VAR)
    if not und or not uperl:
        raise RuntimeError("UND and UPERL environment variables must be set!")

    # Check that the language is supported
    if lang not in SUPPORTED_LANGUAGES:
        raise RuntimeError("Unsupported language: " + lang)

    # Remove the understand db if it exists
    # INTENTIONALLY USING FORWARD SLASH, THIS WORKS FOR WINDOWS.
    # DO NOT CHANGE TO OS.PATH STUFF. UNDERSTAND WANTS FORWARD SLASHES
    # EVEN IN WINDOWS. -DJC 2018-06-08
    clean_project_name = get_clean_project_name(project_name)
    und_db = und_dir + "/" + clean_project_name + ".udb"
    if os.access(und_db, os.F_OK):
        os.remove(und_db)

    # Call Understand
    logger.info("\tSource analysis: " + str(code_dir))
    logger.info("\tUnderstand DB: "+ str(und_db))
    und_command = und \
                  + " -quiet create -languages " + lang \
                  + " add " + code_dir \
                  + " analyze " + und_db
    und_command_split = shlex.split(und_command)
    logger.info("Und command is:" + str(und_command))

    run_checking_stdout_for_license(und_command_split,
                                    "Understand error analyzing source: ")

    if os.access(und_db, os.F_OK):
        logger.info("\tDatabase exists at " + str(und_db))
    else:
        logger.error("\tDatabase does not exist at " + str(und_db))

    # Generate core metrics to the specified output
    logger.info("\tCore metrics: " + code_dir)
    uperl_command = uperl + " " + CBRI_PLUGIN_DIR + "CoreMetrics_v1.23.pl -db " + und_db + " -createMetrics -DuplicateMinLines 10 -outputDir " + data_dir
    uperl_command_split = shlex.split(uperl_command)
    logger.info("Uperl command is:" +  str(uperl_command))

    run_checking_stdout_for_license(uperl_command_split, "Understand error creating metrics: ")


def run_checking_stdout_for_license(split_command, error_message_prefix):
    """
    This method attempts to abstract how calls to Understand binaries are
    handled. Old versions of Understand (e.g. the legacy floating license server
    version used as late as 2018-04) would exit with nonzero error code on an
    invalid license; new versions exit "successfully", with diagnostic message
    in stdout instead.
    """
    # Uses default encoding of utf-8; this appears to work but was not
    # deliberately chosen. -jmm 2018-03-28

    # TODO: Investigate how Windows handles commands; it might be unsafe
    # to allow user input in command even with the default shell=False
    # hardening and using shlex to split the command. -jmm 2018-04-10
    process_result = subprocess.run(split_command, stderr=subprocess.STDOUT,
                                    stdout=subprocess.PIPE, encoding='utf-8')

    logger.info(process_result.stdout)

    for license_msg in UNDERSTAND_LICENSE_PROBLEMS:
        if license_msg in process_result.stdout:
            raise RuntimeError(error_message_prefix + "Error with Understand license")

    try:
        process_result.check_returncode()
    except subprocess.CalledProcessError as exc:
        logger.error("%s didn't exit normally, return code was: %s" % (split_command[0], process_result.returncode))
        raise RuntimeError(error_message_prefix + exc.output)


def remove_directories_for_project(project_name, code_base_dir, data_base_dir, und_base_dir):
    """ Remove all of the directories that would be created for a project """
    if project_name:
        code_dir, data_dir, und_dir = get_directories_for_project(project_name, code_base_dir, data_base_dir, und_base_dir)

        logger.info("\tDeleting the following 2 directories:\n\t%s\n\t%s"
              % (code_dir, data_dir))

        if os.path.isdir(code_dir):
            shutil.rmtree(code_dir, onerror=on_rm_error)
        if os.path.isdir(data_dir):
            shutil.rmtree(data_dir, onerror=on_rm_error)


def on_rm_error(func, path, exc_info):
    # path contains the path of the file that couldn't be removed
    # let's just assume that it's read-only and remove it.
    # https://stackoverflow.com/questions/4829043/how-to-remove-read-only-attrib-directory-with-python-in-windows
    os.chmod(path, stat.S_IWRITE)
    os.remove(path)