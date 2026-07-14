// Context
// -------
// Locating the bundled datasets. The MCP binary and the test suite may be
// launched from different working directories, so FindDataDir walks upward from
// a starting directory until it finds a "data/kaggle" folder.
package soccer

import (
	"os"
	"path/filepath"
)

// FindDataDir searches start and its ancestors for a "data/kaggle" directory and
// returns its path. If start is empty, the current working directory is used.
func FindDataDir(start string) (string, bool) {
	if start == "" {
		if wd, err := os.Getwd(); err == nil {
			start = wd
		}
	}
	dir := start
	for {
		candidate := filepath.Join(dir, "data", "kaggle")
		if info, err := os.Stat(candidate); err == nil && info.IsDir() {
			return candidate, true
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", false
		}
		dir = parent
	}
}
