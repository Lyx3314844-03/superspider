import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class DatasetEnvelope:
    rows: List[Dict[str, Any]]
    output_format: str
    path: str
    artifact_refs: List[str] = field(default_factory=list)


class DatasetWriter:
    def write(
        self, rows: List[Dict[str, Any]], target: Dict[str, Any]
    ) -> DatasetEnvelope:
        output_format = target.get("format", "jsonl")
        path = target["path"]
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_format == "jsonl":
            with output_path.open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        elif output_format == "json":
            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(rows, handle, ensure_ascii=False, indent=2)
        elif output_format == "csv":
            fieldnames = sorted({key for row in rows for key in row.keys()})
            with output_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
        else:
            raise ValueError(f"unsupported dataset format: {output_format}")

        return DatasetEnvelope(
            rows=rows, output_format=output_format, path=str(output_path)
        )
