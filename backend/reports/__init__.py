"""
Reports subpackage for Project VISOR.
Generates structured JSON and Markdown forensic incident reports.
"""

from backend.reports.generator import (
    IncidentReportGenerator,
    get_report_generator,
)

__all__ = [
    "IncidentReportGenerator",
    "get_report_generator",
]
