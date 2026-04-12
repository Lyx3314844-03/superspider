#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
mvn -q -DskipTests compile dependency:copy-dependencies
java -cp "target/classes:target/dependency/*" com.javaspider.EnhancedSpider "$@"
