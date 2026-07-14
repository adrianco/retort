// support_test.go provides shared fixtures for the BDD-style test suite.
// The full dataset is loaded once and reused across every scenario.
package main

import (
	"sync"
	"testing"
)

const testDataDir = "data/kaggle"

var (
	storeOnce sync.Once
	testStore *DataStore
	storeErr  error
)

// loadedStore is the Given step shared by every scenario: "the data is loaded".
func loadedStore(t *testing.T) *DataStore {
	t.Helper()
	storeOnce.Do(func() {
		testStore, storeErr = LoadAll(testDataDir)
	})
	if storeErr != nil {
		t.Fatalf("Given the data is loaded: load failed: %v", storeErr)
	}
	if testStore == nil {
		t.Fatal("Given the data is loaded: store is nil")
	}
	return testStore
}
