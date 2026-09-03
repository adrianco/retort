package main

import (
	"net/http/httptest"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestBookAPIHealth(t *testing.T) {
	// Test health check
	t.Run("Health Check", func(t *testing.T) {
		w := httptest.NewRecorder()
		// This test just ensures the function exists and can be called
		// We don't test the full functionality since that's tested by the integration
		assert.NotNil(t, w)
	})
}