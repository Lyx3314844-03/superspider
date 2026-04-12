#!/usr/bin/env bash
set -euo pipefail

java -cp "../../../javaspider/target/classes:../../../javaspider/target/dependency/*" com.javaspider.EnhancedSpider job --file job.json
