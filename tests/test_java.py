# SPDX-License-Identifier: AGPL-3.0-or-later
"""Java/JUnit alpha: the Maven oracle behind the same contracts.

Skipped when mvn/java are absent (CI without a JDK). Locally these run a
real Maven+JUnit project generated on the fly: repair byte-exact with JUnit
as the judge, and refusal with the tree untouched and every rejected
candidate harvested against the assertion that killed it.
"""
import os
import shutil
import subprocess
import sys

import pytest

from fluidfix import MechanicalObserver
from fluidfix.javaoracle import JavaOracle, jguard_once

_JH = os.environ.get("JAVA_HOME") or (
    "/opt/homebrew/opt/openjdk"
    if os.path.exists("/opt/homebrew/opt/openjdk/bin/java") else None)

pytestmark = pytest.mark.skipif(
    shutil.which("mvn") is None or _JH is None,
    reason="maven/java not installed")

_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>demo</groupId><artifactId>billing</artifactId><version>1.0</version>
  <properties><maven.compiler.release>17</maven.compiler.release>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties>
  <dependencies><dependency><groupId>junit</groupId><artifactId>junit</artifactId>
    <version>4.13.2</version><scope>test</scope></dependency></dependencies>
</project>
"""

_MAIN = """package demo;

public class Billing {
    public static int discountPercent(int units) {
        if (units >= 10) {
            return 15;
        }
        return 0;
    }

    public static int total(int units, int price) {
        int gross = units * price;
        return gross - gross * discountPercent(units) / 100;
    }
}
"""

_TEST = """package demo;

import static org.junit.Assert.assertEquals;
import org.junit.Test;

public class BillingTest {
    @Test public void boundaryGetsDiscount() {
        assertEquals(15, Billing.discountPercent(10));
    }
    @Test public void belowBoundaryDoesNot() {
        assertEquals(0, Billing.discountPercent(9));
    }
    @Test public void totalAppliesDiscount() {
        assertEquals(850, Billing.total(10, 100));
    }
}
"""


def _project(tmp_path, main_src):
    (tmp_path / "src/main/java/demo").mkdir(parents=True)
    (tmp_path / "src/test/java/demo").mkdir(parents=True)
    (tmp_path / "pom.xml").write_text(_POM)
    (tmp_path / "src/main/java/demo/Billing.java").write_text(main_src)
    (tmp_path / "src/test/java/demo/BillingTest.java").write_text(_TEST)
    return JavaOracle(str(tmp_path), java_home=_JH, timeout=300)


def test_junit_repairs_boundary_flip_byte_exact(tmp_path):
    broken = _MAIN.replace("if (units >= 10)", "if (units > 10)")
    oracle = _project(tmp_path, broken)
    report = jguard_once(oracle, MechanicalObserver())
    assert report.status == "repaired"
    assert (tmp_path / "src/main/java/demo/Billing.java").read_text() == _MAIN


def test_junit_oov_refuses_untouched_with_harvest(tmp_path):
    broken = _MAIN.replace("/ 100;", "/ 1000;")
    oracle = _project(tmp_path, broken)
    report = jguard_once(oracle, MechanicalObserver())
    assert report.status == "refused"
    assert (tmp_path / "src/main/java/demo/Billing.java").read_text() == broken
    assert report.attempts
    assert any("expected" in e["why"] for e in report.attempts)
