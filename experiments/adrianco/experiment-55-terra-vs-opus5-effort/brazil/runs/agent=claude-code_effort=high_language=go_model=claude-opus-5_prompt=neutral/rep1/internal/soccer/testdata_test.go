// testdata_test.go provides the shared, load-once fixture used by every test in
// this package. Loading all six CSVs takes a moment, so the graph is built once
// per test binary and shared read-only.
package soccer

import (
	"os"
	"path/filepath"
	"sync"
	"testing"
)

var (
	loadOnce    sync.Once
	sharedGraph *Graph
	loadErr     error
)

// DataDir walks up from the working directory to find data/kaggle.
func DataDir(t testing.TB) string {
	t.Helper()
	dir, err := os.Getwd()
	if err != nil {
		t.Fatalf("getwd: %v", err)
	}
	for i := 0; i < 6; i++ {
		cand := filepath.Join(dir, "data", "kaggle")
		if st, err := os.Stat(cand); err == nil && st.IsDir() {
			return cand
		}
		dir = filepath.Dir(dir)
	}
	t.Fatalf("could not locate data/kaggle from the working directory")
	return ""
}

// LoadTestGraph returns the shared knowledge graph, loading it on first use.
func LoadTestGraph(t testing.TB) *Graph {
	t.Helper()
	loadOnce.Do(func() {
		sharedGraph, loadErr = Load(os.DirFS(DataDir(t)))
	})
	if loadErr != nil {
		t.Fatalf("loading datasets: %v", loadErr)
	}
	return sharedGraph
}
