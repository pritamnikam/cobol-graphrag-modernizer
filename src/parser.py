import logging
import os
import re
from typing import Any, Dict, List

logger = logging.getLogger("CobolParserService")


class CobolParserService:
  """Parses legacy COBOL, JCL, and Copybook files safely with error handling."""

  @staticmethod
  def parse_workspace(base_path: str) -> Dict[str, List[Dict[str, Any]]]:
    parsed_data = {
        "jobs": [],
        "programs": [],
        "copybooks": [],
        "relations": [],
    }

    if not os.path.exists(base_path):
      logger.error(f"Target directory {base_path} does not exist.")
      return parsed_data

    for root, _, files in os.walk(base_path):
      for file in files:
        filepath = os.path.join(root, file)
        try:
          with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

          if file.endswith(".jcl"):
            job_name = file.split(".")[0]
            programs = re.findall(
                r"EXEC\s+PGM=([A-Z0-9]+)", content, re.IGNORECASE
            )
            datasets = re.findall(
                r"DD\s+DSN=([A-Z0-9.]+)", content, re.IGNORECASE
            )
            parsed_data["jobs"].append(
                {"name": job_name, "code": content, "datasets": datasets}
            )
            for p in programs:
              parsed_data["relations"].append({
                  "from": job_name,
                  "from_type": "Job",
                  "to": p,
                  "to_type": "Program",
                  "rel": "EXECUTES",
              })

          elif file.endswith(".cbl"):
            prog_name = file.split(".")[0]
            copies = re.findall(
                r"COPY\s+([A-Z0-9\-]+)\.", content, re.IGNORECASE
            )
            remarks = re.findall(
                r"\*\s*REMARKS\.\s*(.*)", content, re.IGNORECASE
            )
            business_logic = (
                " ".join(remarks)
                if remarks
                else "Core enterprise processing unit."
            )

            parsed_data["programs"].append({
                "name": prog_name,
                "code": content,
                "business_logic": business_logic,
            })
            for c in copies:
              parsed_data["relations"].append({
                  "from": prog_name,
                  "from_type": "Program",
                  "to": c,
                  "to_type": "Copybook",
                  "rel": "USES_COPYBOOK",
              })

          elif file.endswith(".cpy"):
            cpy_name = file.split(".")[0]
            parsed_data["copybooks"].append({"name": cpy_name, "code": content})

        except Exception as e:
          logger.error(f"Failed to parse file {filepath}: {str(e)}")

    logger.info(
        f"Parsed successfully: {len(parsed_data['jobs'])} Jobs,"
        f" {len(parsed_data['programs'])} Programs,"
        f" {len(parsed_data['copybooks'])} Copybooks."
    )
    return parsed_data