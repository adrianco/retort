package acceptance

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"testing"

	"brsoccer/acceptance/driver"

	// The specs reach the server only as a separate process. Importing it
	// here ties the test cache to the server's code, so a change to the
	// server always re-runs the specs.
	_ "brsoccer/internal/app"
)

// TestMain builds the release candidate — the soccer knowledge server —
// once, so that every spec talks to the real thing through its public
// interface.
func TestMain(m *testing.M) {
	dir, err := os.MkdirTemp("", "brsoccer-acceptance")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	binary := os.Getenv("SOCCER_SERVER_BINARY")
	if binary == "" {
		binary = filepath.Join(dir, "brazilian-soccer-mcp")
		build := exec.Command("go", "build", "-o", binary, "brsoccer")
		build.Stdout, build.Stderr = os.Stderr, os.Stderr
		if err := build.Run(); err != nil {
			fmt.Fprintln(os.Stderr, "could not build the soccer knowledge server:", err)
			os.RemoveAll(dir)
			os.Exit(1)
		}
	}
	driver.ServerBinary = binary
	code := m.Run()
	os.RemoveAll(dir)
	os.Exit(code)
}
