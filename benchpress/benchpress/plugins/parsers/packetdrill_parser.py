#!/usr/bin/env python3

from typing import List

from benchpress.lib.parser import Parser, TestCaseResult, TestStatus


class PacketdrillParser(Parser):
    """
    Packetdrill test output is very simple (for now). One row for each
    test:
           test_name return_value
    So the parsing is simple:
        "test_name 0" => "test_name PASS"
        "test_name non-zero" => "test_name FAIL"
    """

    def parse(
        self, stdout: List[str], stderr: List[str], returncode: int
    ) -> List[TestCaseResult]:
        test_cases: List[TestCaseResult] = []
        for line in stdout:
            items = line.split()
            if len(items) != 2:
                continue

            test_name = items[0]
            case = TestCaseResult(name=test_name, status=TestStatus.FAILED)
            if items[1] == "0":
                case.status = TestStatus.PASSED

            test_cases.append(case)

        return test_cases
