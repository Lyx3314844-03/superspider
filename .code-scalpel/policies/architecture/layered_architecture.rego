package code_scalpel.architecture

# Layered Architecture Policy
# Enforces clean separation between presentation, business, and data layers

import future.keywords.if
import future.keywords.in

# Define layer patterns
presentation_patterns := {
    "*/ui/*", "*/views/*", "*/controllers/*", "*/pages/*",
    "*/components/*", "*/routes/*", "*/middleware/*"
}

application_patterns := {
    "*/services/*", "*/usecases/*", "*/application/*",
    "*/handlers/*", "*/commands/*", "*/queries/*"
}

domain_patterns := {
    "*/domain/*", "*/entities/*", "*/models/*",
    "*/business/*", "*/core/*"
}

infrastructure_patterns := {
    "*/infrastructure/*", "*/persistence/*", "*/repositories/*",
    "*/database/*", "*/api/*", "*/adapters/*", "*/external/*"
}

# Check if a file belongs to a specific layer
is_in_layer(file_path, patterns) if {
    some pattern in patterns
    glob.match(pattern, [], file_path)
}

# Determine file's layer
file_layer(file_path) := "presentation" if {
    is_in_layer(file_path, presentation_patterns)
}

file_layer(file_path) := "application" if {
    is_in_layer(file_path, application_patterns)
}

file_layer(file_path) := "domain" if {
    is_in_layer(file_path, domain_patterns)
}

file_layer(file_path) := "infrastructure" if {
    is_in_layer(file_path, infrastructure_patterns)
}

# Violation: Presentation calling Infrastructure directly
violation[{"msg": msg, "severity": "HIGH"}] if {
    some imp in input.imports
    file_layer(input.file) == "presentation"
    file_layer(imp.target) == "infrastructure"
    msg := sprintf("Presentation layer (%s) cannot import Infrastructure layer (%s)", 
                   [input.file, imp.target])
}

# Violation: Domain calling any other layer
violation[{"msg": msg, "severity": "CRITICAL"}] if {
    some imp in input.imports
    file_layer(input.file) == "domain"
    file_layer(imp.target) != "domain"
    msg := sprintf("Domain layer (%s) must not import other layers (%s)", 
                   [input.file, imp.target])
}
