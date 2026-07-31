package soccer

import (
	"sync"
	"testing"
)

// The datasets are loaded once for the whole package: every test shares the
// same read-only Store, which keeps `go test` well under a second per test.
var (
	sharedOnce  sync.Once
	sharedStore *Store
	sharedErr   error
)

func testStore(t testing.TB) *Store {
	t.Helper()
	sharedOnce.Do(func() {
		sharedStore, sharedErr = Load(Options{})
	})
	if sharedErr != nil {
		t.Fatalf("loading datasets: %v", sharedErr)
	}
	return sharedStore
}
