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
            steps = re.findall(
                r"^\s*//([A-Z0-9@$#]+)\s+EXEC\s+PGM=([A-Z0-9]+)",
                content,
                re.IGNORECASE | re.MULTILINE,
            )
            datasets = re.findall(
                r"DD\s+DSN=([A-Z0-9.]+)", content, re.IGNORECASE
            )
            parsed_data["jobs"].append(
                {"name": job_name, "code": content, "datasets": datasets}
            )
            for step_order, (step_name, program_name) in enumerate(steps, 1):
              parsed_data["relations"].append({
                  "from": job_name,
                  "from_type": "Job",
                  "to": program_name,
                  "to_type": "Program",
                  "rel": "EXECUTES",
                  "step_order": step_order,
                  "step_name": step_name,
              })

            dependencies = re.findall(
                r"^\s*//\*\s*DEPENDS-ON:\s*([A-Z0-9_]+)",
                content,
                re.IGNORECASE | re.MULTILINE,
            )
            for dependency in dependencies:
              parsed_data["relations"].append({
                  "from": job_name,
                  "from_type": "Job",
                  "to": dependency,
                  "to_type": "Job",
                  "rel": "DEPENDS_ON",
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

            called_programs = re.findall(
                r"\bCALL\s+['\"]([A-Z0-9-]+)['\"]",
                content,
                re.IGNORECASE,
            )
            for called_program in called_programs:
              parsed_data["relations"].append({
                  "from": prog_name,
                  "from_type": "Program",
                  "to": called_program,
                  "to_type": "Program",
                  "rel": "CALLS",
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