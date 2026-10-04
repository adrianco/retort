package drivers

import (
	"path/filepath"
	"sync"
	"testing"
)

var (
	providedOnce sync.Once
	providedConn *Connection
	providedErr  error
)

// ProvidedDataSystem returns the one shared, read-only instance of the
// system loaded with the provided Kaggle datasets.
func ProvidedDataSystem(t *testing.T) *Connection {
	t.Helper()
	providedOnce.Do(func() {
		providedConn, providedErr = StartConnection(filepath.Join(ModuleRoot(), "data", "kaggle"))
	})
	if providedErr != nil {
		t.Fatalf("the soccer knowledge system did not start with the provided data: %v", providedErr)
	}
	return providedConn
}

// StopProvidedDataSystem shuts the shared instance down at the end of a run.
func StopProvidedDataSystem() {
	if providedConn != nil {
		providedConn.Close()
	}
}
