package code_scalpel.devsecops

# Secret Detection Policy
# Detects hardcoded secrets, API keys, tokens, and credentials

import future.keywords.if
import future.keywords.in

# AWS Access Keys
has_aws_key(content) if {
    regex.match("AKIA[0-9A-Z]{16}", content)
}

# GitHub Tokens
has_github_token(content) if {
    regex.match("ghp_[A-Za-z0-9]{36}", content)
}

# Generic API Keys
has_api_key(content) if {
    regex.match("(?i)api[_-]?key['\"]?\\s*[:=]\\s*['\"][A-Za-z0-9_\\-]{20,}['\"]", content)
}

# Private Keys
has_private_key(content) if {
    contains(content, "BEGIN RSA PRIVATE KEY")
}

has_private_key(content) if {
    contains(content, "BEGIN PRIVATE KEY")
}

# Violations
violation[{"msg": "AWS access key detected", "severity": "CRITICAL", "line": line}] if {
    some line
    has_aws_key(input.lines[line])
}

violation[{"msg": "GitHub token detected", "severity": "CRITICAL", "line": line}] if {
    some line
    has_github_token(input.lines[line])
}

violation[{"msg": "API key detected", "severity": "HIGH", "line": line}] if {
    some line
    has_api_key(input.lines[line])
}

violation[{"msg": "Private key detected", "severity": "CRITICAL", "line": line}] if {
    some line
    has_private_key(input.lines[line])
}
