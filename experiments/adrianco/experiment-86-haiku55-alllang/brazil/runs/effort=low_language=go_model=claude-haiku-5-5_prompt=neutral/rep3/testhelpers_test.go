// Shared test fixtures: the real dataset is loaded once per test binary.

package main

import (
	"sync"
	"testing"
)

const testDataDir = "data/kaggle"

var (
	dsOnce sync.Once
	dsVal  *Dataset
	dsErr  error
)

// loadTestDataset returns the real Kaggle dataset, failing the test if it cannot be read.
func loadTestDataset(t *testing.T) *Dataset {
	t.Helper()
	dsOnce.Do(func() {
		dsVal, dsErr = LoadDataset(testDataDir)
	})
	if dsErr != nil {
		t.Fatalf("load dataset: %v", dsErr)
	}
	return dsVal
}
