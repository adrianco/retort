package api_test

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"bookapi/internal/api"
	"bookapi/internal/book"
)

// requests exercises every store-backed endpoint.
var requests = []struct{ name, method, target, body string }{
	{"create", http.MethodPost, "/books", `{"title":"T","author":"A"}`},
	{"list", http.MethodGet, "/books", ""},
	{"get", http.MethodGet, "/books/1", ""},
	{"update", http.MethodPut, "/books/1", `{"title":"T","author":"A"}`},
	{"delete", http.MethodDelete, "/books/1", ""},
}

func TestStoreFailuresAreReportedAsAGeneric500(t *testing.T) {
	secret := errors.New("disk I/O error at /var/db/secret.db")

	for _, tt := range requests {
		t.Run(tt.name, func(t *testing.T) {
			var logs bytes.Buffer
			h := api.New(failingStore{err: secret}, slog.New(slog.NewTextHandler(&logs, nil)))

			rec := do(t, h, tt.method, tt.target, tt.body)
			expect(t, rec, http.StatusInternalServerError)
			if got := decode[errorJSON](t, rec).Error; got != "internal server error" {
				t.Errorf("error = %q, want a generic message", got)
			}
			if strings.Contains(rec.Body.String(), "secret.db") {
				t.Errorf("response leaks internal details: %s", rec.Body)
			}
			if !strings.Contains(logs.String(), "secret.db") {
				t.Errorf("the underlying error was not logged for operators: %s", logs.String())
			}
		})
	}
}

// A client that hangs up mid-request is not a server fault: it must not be
// logged as an error or counted as a 5xx.
func TestClientDisconnectIsNotAServerError(t *testing.T) {
	for _, tt := range requests {
		t.Run(tt.name, func(t *testing.T) {
			var logs bytes.Buffer
			h := api.New(failingStore{err: fmt.Errorf("store call: %w", context.Canceled)}, slog.New(slog.NewTextHandler(&logs, nil)))

			rec := do(t, h, tt.method, tt.target, tt.body)
			if rec.Code != 499 {
				t.Errorf("status = %d, want 499 (client closed request)", rec.Code)
			}
			if strings.Contains(logs.String(), "level=ERROR") {
				t.Errorf("a client disconnect was logged as an error:\n%s", logs.String())
			}
			if !strings.Contains(logs.String(), "status=499") {
				t.Errorf("the access log does not record the abandoned request:\n%s", logs.String())
			}
		})
	}
}

// The same, end to end: a request whose context is already cancelled reaches the
// real SQLite store, which refuses it with context.Canceled.
func TestCancelledRequestAgainstTheRealStore(t *testing.T) {
	h := newHandler(t)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	for _, tt := range requests {
		req := httptest.NewRequest(tt.method, tt.target, strings.NewReader(tt.body)).WithContext(ctx)
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		if rec.Code != 499 {
			t.Errorf("%s %s with a cancelled context = %d %s, want 499", tt.method, tt.target, rec.Code, rec.Body)
		}
	}
}

func TestUnknownBookFromTheStoreIsA404(t *testing.T) {
	// Wrapping must not hide the sentinel from the API layer.
	h := api.New(failingStore{err: fmt.Errorf("lookup: %w", book.ErrNotFound)}, discard)

	for _, tt := range requests {
		if tt.name == "create" || tt.name == "list" {
			continue
		}
		t.Run(tt.name, func(t *testing.T) {
			rec := do(t, h, tt.method, tt.target, tt.body)
			expect(t, rec, http.StatusNotFound)
			if got := decode[errorJSON](t, rec).Error; got != "book not found" {
				t.Errorf("error = %q, want %q", got, "book not found")
			}
		})
	}
}

func TestPanicInAHandlerBecomesAJSON500(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(panickingStore{}, slog.New(slog.NewTextHandler(&logs, nil)))

	rec := do(t, h, http.MethodGet, "/books/1", "")
	expect(t, rec, http.StatusInternalServerError)
	if got := decode[errorJSON](t, rec).Error; got != "internal server error" {
		t.Errorf("error = %q, want a generic message", got)
	}
	if strings.Contains(rec.Body.String(), "kaboom") {
		t.Errorf("response leaks the panic value: %s", rec.Body)
	}
	if out := logs.String(); !strings.Contains(out, "kaboom") || !strings.Contains(out, "panic while serving request") {
		t.Errorf("the panic was not logged: %s", out)
	}

	// The service keeps working after a panic.
	expect(t, do(t, h, http.MethodGet, "/health", ""), http.StatusOK)
}

func TestEachRequestIsLogged(t *testing.T) {
	var logs bytes.Buffer
	h := api.New(failingStore{}, slog.New(slog.NewTextHandler(&logs, nil)))

	do(t, h, http.MethodGet, "/health", "")
	do(t, h, http.MethodGet, "/nope", "")

	out := logs.String()
	for _, want := range []string{
		"method=GET path=/health status=200",
		"method=GET path=/nope status=404",
	} {
		if !strings.Contains(out, want) {
			t.Errorf("log does not contain %q:\n%s", want, out)
		}
	}
}
