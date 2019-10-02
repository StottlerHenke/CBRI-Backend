GITHUB_RESULTS_DIR = file.path("data-raw")
PROCESSED_RESULTS_DIR = file.path("data-processed")
LOWER_BOUND_COMMITS = 30
LOWER_BOUND_PROPAGATION = 0
LOWER_BOUND_RELEASES = 1
LOWER_BOUND_STARS = 100
LOWER_BOUND_ULOC = 1000
UPPER_BOUND_COMMENT_DENSITY = 100
UPPER_BOUND_ULOC = Inf
UPPER_BOUND_PERCENT_DULOC = 100

LOWER_BOUND_DEFECT_PRONENESS = 1

load_data = function(filename, lang) {
  csv_path = file.path(GITHUB_RESULTS_DIR, filename)
  read.csv(csv_path, header = T, 
           as.is = c("name", "owner", "url", "version", "creation.date", "description", "topics", "Project.Name")) %>% 
    mutate(language = lang) %>%
    rename_at(vars(everything()), ~ tolower(.)) %>%
    rename(uloc = useful.lines.of.code..uloc.,
           sloc = software.lines.of.code..sloc.,
           duloc = duplicate.useful.lines.of.code,
           percent.files.overly.complex = overly.complex.files) %>%
    mutate(percent.duloc = duloc / uloc * 100.0,
           percent_open_issues = ifelse(open.issues + closed.issues > 0, 100 * open.issues / (open.issues + closed.issues), 0))
}

filter_by_top_stars = function(df, n) {
  (df %>% arrange(desc(stars)))[1:n,]
}

filter_projects = function(df) {
  df %>% mutate(classes = ifelse(is.na(classes), 0, classes)) %>%
    filter(stars >= LOWER_BOUND_STARS,
           commits >= LOWER_BOUND_COMMITS,
           releases_count >= LOWER_BOUND_RELEASES,
           uloc >= LOWER_BOUND_ULOC,
           propagation.cost >= LOWER_BOUND_PROPAGATION,
           useful.comment.density <= UPPER_BOUND_COMMENT_DENSITY,
           percent.duloc <= UPPER_BOUND_PERCENT_DULOC,
           uloc <= UPPER_BOUND_ULOC) %>%
    mutate(contributors = ifelse(contributors == 0, 1, contributors),
           architecture.type = ordered(architecture.type, levels = c("Hierarchical", "Multi-Core", "Borderline Core-Periphery", "Core-Periphery"))) %>%
    select(-name, -owner, -url, -version, -creation.date, 
           -watches, -forks, -languages, -last.year.commit..,
           -description, -sloc) %>% 
    mutate_at(vars(stars, uloc, commits, contributors, open.issues, closed.issues, classes, files),
              list(log = ~ log2(.)))
}

load_processed_data = function(filename, lang) {
  csv_path = file.path(PROCESSED_RESULTS_DIR, filename)
  read.csv(csv_path, header = T, 
           as.is = c("topics", "project_name")) %>% 
    mutate(language = lang,
           core = ifelse(core == "True", T, F)) %>%
    rename_at(vars(everything()), ~ tolower(.)) %>%
    rename(uloc = useful_lines_of_code_.uloc.) %>%
    rename_at(vars(ends_with("score")), ~ paste0(., "_with_topics")) %>%
    mutate(percent_open_issues = ifelse(open_issues + closed_issues > 0, 100 * open_issues / (open_issues + closed_issues), 0),
           architecture_score = architecture_score_with_topics,
           complexity_score = complexity_score_with_topics,
           clarity_score = clarity_score_with_topics,
           overall_score = overall_score_with_topics)# %>%
    #filter(open_issues + closed_issues > 0)
}

csharp_results = load_data("csharp_.csv", "Csharp")
c_results = load_data("c_.csv", "c")
cpp_results = load_data("cpp_.csv", "cpp")
java_results = load_data("java_.csv", "java") %>% filter_by_top_stars(n = 1000)
javascript_results = load_data("javascript_.csv", "javascript")
python_results = load_data("python_.csv", "python")

all_results = rbind(csharp_results, c_results, cpp_results, java_results, javascript_results, python_results) %>%
  mutate_at(vars(language), as.factor) %>%
  mutate_at(vars(core), as.logical)
all_results_filtered = all_results %>% filter_projects()
all_results_filtered_more = all_results_filtered %>% 
  filter(defect_proneness >= LOWER_BOUND_DEFECT_PRONENESS) 

csharp_processed = load_processed_data("csharp_.csv", "Csharp")
c_processed = load_processed_data("c_.csv", "c")
cpp_processed = load_processed_data("cpp_.csv", "cpp")
java_processed = load_processed_data("java_.csv", "java")
javascript_processed = load_processed_data("javascript_.csv", "javascript")
python_processed = load_processed_data("python_.csv", "python")

all_results_processed = 
  rbind(csharp_processed, c_processed, cpp_processed, java_processed, javascript_processed, python_processed) %>% 
  mutate_at(vars(language), as.factor) %>%
  rename_at(vars(starts_with("log")), ~paste0(sub("log_", "", .), "_log10")) %>%
  mutate_at(vars(ends_with("log10")), list(log2 = ~ . / log10(2))) %>%
  rename_at(vars(ends_with("_log10_log2")), ~sub("_log10", "", .)) %>%
  mutate(log_uloc = uloc_log2, 
         log_contributors = contributors_log2)
