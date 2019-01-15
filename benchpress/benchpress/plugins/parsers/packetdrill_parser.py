#!/usr/bin/env python3

from benchpress.lib.parser import Parser


class TestStatus(object):
    PASSED = 1
    FAILED = 2


class PacketdrillParser(Parser):
    """
    Packetdrill test output is very simple (for now). One row for each
    test:
           test_name return_value
    So the parsing is simple:
        "test_name 0" => "test_name PASS"
        "test_name none-zero" => "test_name FAIL"
    """

    def __init__(self):
        super().__init__()

    def parse(self, stdout, stderr, returncode):
        metrics = {}
        for line in stdout:
            items = line.split()
            if len(items) != 2:
                continue

            test_name = items[0]
            test_metrics = {}
            if items[1] == "0":
                test_metrics["status"] = TestStatus.PASSED
            else:
                test_metrics["status"] = TestStatus.FAILED
            metrics[test_name] = test_metrics
        return metrics
