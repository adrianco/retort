"""Go coverage counts code a test runs as a SUBPROCESS (the ATDD protocol-driver pattern).

exp-83's first Go cell: a passing acceptance suite that `go build`s the server and
drives it over stdio scored test_coverage 0.0% and was failed as "tests did not run".
"""
import shutil
import textwrap

import pytest

from retort.scoring.scorers.test_coverage import TestCoverageScorer, _merge_go_profiles


def test_merge_takes_union_of_covered_blocks():
    unit = "mode: set\nm/a.go:1.1,2.2 3 0\nm/a.go:3.1,4.2 1 1\nm/b.go:1.1,2.2 6 0\n"
    integ = "mode: count\nm/a.go:1.1,2.2 3 5\n"
    assert _merge_go_profiles(unit, integ) == pytest.approx(100 * 4 / 10)
    assert _merge_go_profiles(unit) == pytest.approx(10.0)
    assert _merge_go_profiles("mode: set\n") is None


@pytest.mark.skipif(shutil.which("go") is None, reason="go toolchain not installed")
def test_subprocess_driven_acceptance_suite_is_credited(tmp_path):
    (tmp_path / "go.mod").write_text("module demo\n\ngo 1.21\n")
    (tmp_path / "cmd" / "demo").mkdir(parents=True)
    (tmp_path / "cmd" / "demo" / "main.go").write_text(textwrap.dedent("""\
        package main

        import "fmt"

        func main() {
            fmt.Println(double(21))
        }

        func double(n int) int { return n * 2 }
        """))
    (tmp_path / "acceptance").mkdir()
    (tmp_path / "acceptance" / "driver_test.go").write_text(textwrap.dedent("""\
        package acceptance

        import (
            "os/exec"
            "path/filepath"
            "strings"
            "testing"
        )

        func TestDoubles(t *testing.T) {
            bin := filepath.Join(t.TempDir(), "demo")
            if out, err := exec.Command("go", "build", "-o", bin, "../cmd/demo").CombinedOutput(); err != nil {
                t.Fatalf("build: %v %s", err, out)
            }
            out, err := exec.Command(bin).Output()
            if err != nil || strings.TrimSpace(string(out)) != "42" {
                t.Fatalf("got %q %v", out, err)
            }
        }
        """))
    pct = TestCoverageScorer()._go_coverage(tmp_path)
    assert pct is not None and pct > 50.0  # was 0.0 before the integration pass
