package api

import (
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// These white-box tests cover behaviour that cannot be reached through the
// public handler, which never panics after writing or encodes an unencodable value.

var discard = slog.New(slog.DiscardHandler)

func TestWriteJSONFallsBackToGeneric500WhenEncodingFails(t *testing.T) {
	rec := httptest.NewRecorder()

	writeJSON(rec, http.StatusOK, make(chan int)) // channels cannot be encoded as JSON

	if rec.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", rec.Code)
	}
	if got := rec.Header().Get("Content-Type"); got != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", got)
	}
	if got, want := strings.TrimSpace(rec.Body.String()), `{"error":"internal server error"}`; got != want {
		t.Errorf("body = %s, want %s", got, want)
	}
}

func TestStatusRecorder(t *testing.T) {
	t.Run("a write without WriteHeader is a 200", func(t *testing.T) {
		rec := &statusRecorder{ResponseWriter: httptest.NewRecorder(), status: http.StatusOK}
		io.WriteString(rec, "hello")
		if rec.status != http.StatusOK || !rec.wroteHeader {
			t.Errorf("status = %d, wroteHeader = %v; want 200 and true", rec.status, rec.wroteHeader)
		}
	})

	t.Run("the first WriteHeader wins, as in net/http", func(t *testing.T) {
		underlying := httptest.NewRecorder()
		rec := &statusRecorder{ResponseWriter: underlying, status: http.StatusOK}
		rec.WriteHeader(http.StatusCreated)
		rec.WriteHeader(http.StatusInternalServerError)
		if rec.status != http.StatusCreated {
			t.Errorf("recorded status = %d, want 201", rec.status)
		}
		if underlying.Code != http.StatusCreated {
			t.Errorf("underlying status = %d, want 201", underlying.Code)
		}
	})

	t.Run("http.ResponseController can reach the underlying writer", func(t *testing.T) {
		underlying := httptest.NewRecorder()
		rec := &statusRecorder{ResponseWriter: underlying, status: http.StatusOK}
		if err := http.NewResponseController(rec).Flush(); err != nil {
			t.Fatalf("Flush through the wrapper: %v", err)
		}
		if !underlying.Flushed {
			t.Error("Flush did not reach the underlying ResponseWriter")
		}
	})
}

func TestObserveDoesNotAppendAnErrorToAStartedResponse(t *testing.T) {
	handler := observe(discard, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusAccepted)
		io.WriteString(w, "partial")
		panic("failure after the response started")
	}))

	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))

	if rec.Code != http.StatusAccepted {
		t.Errorf("status = %d, want the original 202 (a 500 can no longer be sent)", rec.Code)
	}
	if got := rec.Body.String(); got != "partial" {
		t.Errorf("body = %q, want only what was written before the panic", got)
	}
}

func TestObservePropagatesErrAbortHandler(t *testing.T) {
	handler := observe(discard, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic(http.ErrAbortHandler)
	}))

	defer func() {
		if got := recover(); got != http.ErrAbortHandler {
			t.Errorf("recovered %v, want http.ErrAbortHandler to propagate to net/http", got)
		}
	}()
	rec := httptest.NewRecorder()
	handler.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	t.Error("ServeHTTP returned normally; the abort panic was swallowed")
}
