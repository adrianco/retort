package api_test

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"testing/iotest"

	"bookapi/internal/api"
)

func TestHealth(t *testing.T) {
	h := newHandler(t)

	rec := do(t, h, http.MethodGet, "/health", "")
	expect(t, rec, http.StatusOK)
	if got := decode[map[string]string](t, rec); got["status"] != "ok" {
		t.Errorf("body = %v, want status ok", got)
	}

	// GET routes also answer HEAD, which health checkers commonly use.
	expect(t, do(t, h, http.MethodHead, "/health", ""), http.StatusOK)
}

func TestHealthReportsAnUnreachableDatabase(t *testing.T) {
	h := api.New(failingStore{err: errors.New("disk I/O error at /var/db/secret.db")}, discard)

	rec := do(t, h, http.MethodGet, "/health", "")
	expect(t, rec, http.StatusServiceUnavailable)
	if got := decode[map[string]string](t, rec); got["status"] != "unavailable" {
		t.Errorf("body = %v, want status unavailable", got)
	}
	if strings.Contains(rec.Body.String(), "secret.db") {
		t.Errorf("health response leaks internal details: %s", rec.Body)
	}
}

func TestUnknownPathsReturnJSON404(t *testing.T) {
	h := newHandler(t)

	for _, path := range []string{"/", "/nope", "/books/1/extra", "/health/deep", "/books/", "/api/books"} {
		rec := do(t, h, http.MethodGet, path, "")
		expect(t, rec, http.StatusNotFound)
		if got := decode[errorJSON](t, rec).Error; got != "endpoint not found" {
			t.Errorf("GET %s error = %q, want %q", path, got, "endpoint not found")
		}
	}
}

func TestWrongMethodReturnsJSON405WithAllowHeader(t *testing.T) {
	h := newHandler(t)

	tests := []struct {
		method, path, allow string
	}{
		{http.MethodPatch, "/books/1", "GET, HEAD, PUT, DELETE"},
		{http.MethodPost, "/books/1", "GET, HEAD, PUT, DELETE"},
		{http.MethodDelete, "/books", "GET, HEAD, POST"},
		{http.MethodPut, "/books", "GET, HEAD, POST"},
		{http.MethodOptions, "/books", "GET, HEAD, POST"},
		{http.MethodPost, "/health", "GET, HEAD"},
		{http.MethodDelete, "/health", "GET, HEAD"},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.path, func(t *testing.T) {
			rec := do(t, h, tt.method, tt.path, "")
			expect(t, rec, http.StatusMethodNotAllowed)
			if got := rec.Header().Get("Allow"); got != tt.allow {
				t.Errorf("Allow = %q, want %q", got, tt.allow)
			}
			if got := decode[errorJSON](t, rec).Error; !strings.Contains(got, tt.method) {
				t.Errorf("error = %q, want it to mention the method %s", got, tt.method)
			}
		})
	}
}

func TestNewFallsBackToTheDefaultLogger(t *testing.T) {
	h := api.New(failingStore{}, nil)
	expect(t, do(t, h, http.MethodGet, "/health", ""), http.StatusOK)
}

func TestUnreadableRequestBodyIsABadRequest(t *testing.T) {
	h := newHandler(t)

	req := httptest.NewRequest(http.MethodPost, "/books", iotest.ErrReader(errors.New("connection reset")))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)

	expect(t, rec, http.StatusBadRequest)
	if got := decode[errorJSON](t, rec).Error; got != "request body could not be read" {
		t.Errorf("error = %q", got)
	}
	if strings.Contains(rec.Body.String(), "connection reset") {
		t.Errorf("response leaks the underlying read error: %s", rec.Body)
	}
}
