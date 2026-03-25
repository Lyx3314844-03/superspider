# Code Scalpel Project Structure Policy
# Enforces consistent organization across the codebase

package project.structure

import future.keywords.if
import future.keywords.in

# Configuration loaded from .code-scalpel/project-structure.yaml
config := data.project_config

# FILE LOCATION RULES
violation[{"msg": msg, "severity": "HIGH", "file": file.path}] if {
    file := input.files[_]
    file_type := detect_file_type(file)
    file_type != "unknown"
    expected_dir := config.file_locations[file_type]
    expected_dir != null
    not path_matches(file.path, expected_dir)
    msg := sprintf("File type '%s' must be in '%s/', found in '%s'", 
                   [file_type, expected_dir, file.path])
}

# README REQUIREMENTS
violation[{"msg": msg, "severity": "MEDIUM", "directory": dir}] if {
    dir := input.directories[_]
    not is_excluded_dir(dir)
    not has_readme(dir)
    msg := sprintf("Directory '%s' must have README.md", [dir])
}

# Helper functions
detect_file_type(file) := "test_file" if {
    startswith(file.name, "test_")
    endswith(file.name, ".py")
}

detect_file_type(file) := "policy_file" if {
    endswith(file.name, ".rego")
}

detect_file_type(file) := "unknown" if {
    true
}

path_matches(path, pattern) if {
    glob.match(pattern, [], path)
}

is_excluded_dir(dir) if {
    excluded := {"__pycache__", ".pytest_cache", "node_modules", ".venv", ".git"}
    some ex in excluded
    contains(dir, ex)
}

has_readme(dir) if {
    some file in input.files
    file.path == concat("/", [dir, "README.md"])
}
