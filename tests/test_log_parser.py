"""Tests for log parsers — .sta, .msg, .dat files."""

from __future__ import annotations

import ast
from pathlib import Path

from abaqus_mcp_server.log_parser import (
    DatFileContent,
    MessageEntry,
    StaInfo,
    parse_dat_file,
    parse_msg_file,
    parse_sta_file,
)
from abaqus_mcp_server.odb_script_templates import (
    make_field_output_script,
    make_history_output_script,
    make_odb_summary_script,
)

FIXTURES = Path(__file__).parent / "fixtures" / "sample_files"


# ── .sta parsing ─────────────────────────────────────────────────────────────


class TestParseStaFile:
    def test_completed_status(self):
        content = (FIXTURES / "sample.sta").read_text()
        info = parse_sta_file(content)
        assert info.status == "completed"
        assert info.current_increment == 10
        assert info.current_step == 1
        assert info.step_time == 1.0
        assert info.total_time == 1.0

    def test_running_status(self):
        content = "    1    5   1      0     1 0.500  0.500"
        info = parse_sta_file(content)
        assert info.status == "running"
        assert info.current_increment == 5

    def test_failed_status(self):
        content = "THE ANALYSIS HAS NOT BEEN COMPLETED\n    1   1   1"
        info = parse_sta_file(content)
        assert info.status == "failed"

    def test_aborted_status(self):
        content = "THE ANALYSIS HAS BEEN TERMINATED"
        info = parse_sta_file(content)
        assert info.status == "aborted"

    def test_empty_file(self):
        info = parse_sta_file("")
        assert info.status == "unknown"

    def test_whitespace_only(self):
        info = parse_sta_file("   \n  \n  ")
        assert info.status == "unknown"


# ── .msg parsing ─────────────────────────────────────────────────────────────


class TestParseMsgFile:
    def test_extracts_errors_and_warnings(self):
        content = (FIXTURES / "sample.msg").read_text()
        entries = parse_msg_file(content)

        errors = [e for e in entries if e.severity == "ERROR"]
        warnings = [e for e in entries if e.severity == "WARNING"]

        assert len(errors) >= 1
        assert any("TOO MANY ATTEMPTS" in e.message for e in errors)
        assert len(warnings) >= 1
        assert any("STRAIN INCREMENT" in e.message for e in warnings)

    def test_empty_file(self):
        entries = parse_msg_file("")
        assert entries == []

    def test_message_has_line_number(self):
        entries = parse_msg_file("***WARNING: test warning\n***ERROR: test error")
        assert entries[0].line_number == 1
        assert entries[1].line_number == 2


# ── .dat parsing ─────────────────────────────────────────────────────────────


class TestParseDatFile:
    def test_extracts_errors(self):
        content = (FIXTURES / "sample.dat").read_text()
        result = parse_dat_file(content)
        assert len(result.errors) >= 1
        assert any("DISTORTING" in e for e in result.errors)

    def test_extracts_warnings(self):
        content = (FIXTURES / "sample.dat").read_text()
        result = parse_dat_file(content)
        assert len(result.warnings) >= 1
        assert any("NEGATIVE EIGENVALUES" in w for w in result.warnings)

    def test_no_errors_in_clean_file(self):
        content = "PROBLEM SIZE\n NUMBER OF ELEMENTS: 1000\n"
        result = parse_dat_file(content)
        assert result.errors == []
        assert "No errors" in result.summary


# ── ODB script templates ─────────────────────────────────────────────────────


class TestOdbScriptTemplates:
    def test_summary_script_is_valid_python(self):
        script = make_odb_summary_script("C:/test/model.odb")
        ast.parse(script)

    def test_summary_script_contains_expected_elements(self):
        script = make_odb_summary_script("/path/to/test.odb")
        assert "openOdb" in script
        assert "odbAccess" in script
        assert "ODB_JSON_START" in script
        assert "ODB_JSON_END" in script

    def test_field_output_script_is_valid_python(self):
        script = make_field_output_script(
            "test.odb", "Step-1", -1, "S", component="Mises"
        )
        ast.parse(script)

    def test_field_output_script_includes_component(self):
        script = make_field_output_script(
            "test.odb", "Step-1", -1, "S", component="Mises"
        )
        assert "Mises" in script

    def test_history_output_script_is_valid_python(self):
        script = make_history_output_script("test.odb", "Step-1", "ALLIE")
        ast.parse(script)

    def test_history_output_script_includes_region(self):
        script = make_history_output_script("test.odb", "Step-1", "ALLIE")
        assert "ALLIE" in script
