// Shared test fixtures. The real Kaggle CSV files in data/kaggle are loaded
// once and reused across the BDD scenarios.
package main

import (
	"sync"
	"testing"
)

var (
	sharedDB   *DB
	sharedOnce sync.Once
	sharedErr  error
)

// testDB loads the bundled datasets once and returns the shared in-memory DB.
func testDB(t *testing.T) *DB {
	t.Helper()
	sharedOnce.Do(func() {
		sharedDB, sharedErr = BuildDB("data/kaggle")
	})
	if sharedErr != nil {
		t.Fatalf("failed to load datasets from data/kaggle: %v", sharedErr)
	}
	return sharedDB
}
