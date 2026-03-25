package code_scalpel.devops

# Dockerfile Security Policy
# Enforces Docker container security best practices

import future.keywords.if
import future.keywords.in

# Check for secrets in Dockerfile
has_secrets(content) if {
    regex.match("(?i)(password|api[_-]?key|secret|token|credential)\\s*=", content)
}

# Check for root user
uses_root_user(lines) if {
    not any([line | 
        line := lines[_]
        startswith(line, "USER ")
    ])
}

uses_root_user(lines) if {
    some line in lines
    line == "USER root"
}

# Check for :latest tag
uses_latest_tag(lines) if {
    some line in lines
    startswith(line, "FROM ")
    contains(line, ":latest")
}

# Violation: Secrets detected
violation[{"msg": "Dockerfile contains hardcoded secrets", "severity": "CRITICAL"}] if {
    has_secrets(input.content)
}

# Violation: Running as root
violation[{"msg": "Dockerfile must specify non-root USER", "severity": "HIGH"}] if {
    uses_root_user(input.lines)
}

# Violation: Using :latest tag
violation[{"msg": "Dockerfile must use specific image tags, not :latest", "severity": "MEDIUM"}] if {
    uses_latest_tag(input.lines)
}
