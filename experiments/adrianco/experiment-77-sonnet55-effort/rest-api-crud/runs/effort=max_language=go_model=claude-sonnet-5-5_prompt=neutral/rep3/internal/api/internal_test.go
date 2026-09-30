package api

import (
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"reflect"
	"strings"
	"testing"
)

func newTestServer() *server {
	return &server{log: slog.New(slog.NewTextHandler(io.Discard, nil))}
}

func TestWriteJSONFallsBackToA500WhenEncodingFails(t *testing.T) {
	rec := httptest.NewRecorder()
	newTestServer().writeJSON(rec, http.StatusCreated, make(chan int)) // channels cannot be encoded

	if rec.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", rec.Code)
	}
	if rec.Body.String() != internalErrorBody {
		t.Errorf("body = %q, want %q", rec.Body, internalErrorBody)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

func TestWriteJSONSetsSecurityAndTypeHeaders(t *testing.T) {
	rec := httptest.NewRecorder()
	newTestServer().writeJSON(rec, http.StatusOK, map[string]string{"title": "Tom & Jerry <3"})

	if got := rec.Header().Get("X-Content-Type-Options"); got != "nosniff" {
		t.Errorf("X-Content-Type-Options = %q, want nosniff", got)
	}
	if !strings.Contains(rec.Body.String(), "Tom & Jerry <3") {
		t.Errorf("body = %q, want the text unescaped", rec.Body)
	}
}

// A handler that has already started its response cannot be turned into a 500
// afterwards; the recovery must not append an error body to a partial reply.
func TestRecoveryLeavesAStartedResponseAlone(t *testing.T) {
	h := newTestServer().logAndRecover(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusAccepted)
		w.Write([]byte("partial"))
		panic("too late")
	}))

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))

	if rec.Code != http.StatusAccepted || rec.Body.String() != "partial" {
		t.Errorf("response = %d %q, want the original 202 %q left intact", rec.Code, rec.Body, "partial")
	}
}

func TestRecoveryLetsHandlerAbortsThrough(t *testing.T) {
	h := newTestServer().logAndRecover(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		panic(http.ErrAbortHandler)
	}))

	defer func() {
		if p := recover(); p != http.ErrAbortHandler {
			t.Errorf("recovered %v, want http.ErrAbortHandler to propagate", p)
		}
	}()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))
	t.Error("ServeHTTP returned normally, want the abort to propagate")
}

func TestStatusRecorderTracksImplicitAndExplicitStatus(t *testing.T) {
	implicit := &statusRecorder{ResponseWriter: httptest.NewRecorder(), status: http.StatusOK}
	implicit.Write([]byte("x"))
	if implicit.status != http.StatusOK || !implicit.wroteHeader {
		t.Errorf("after Write: status=%d wroteHeader=%v, want 200/true", implicit.status, implicit.wroteHeader)
	}

	explicit := &statusRecorder{ResponseWriter: httptest.NewRecorder(), status: http.StatusOK}
	explicit.WriteHeader(http.StatusTeapot)
	explicit.WriteHeader(http.StatusOK) // net/http ignores repeats, and so must the recorder
	if explicit.status != http.StatusTeapot {
		t.Errorf("status = %d, want the first status (418) to stick", explicit.status)
	}
}

// Wrapping the writer must not hide optional capabilities such as Flush from
// handlers that use http.ResponseController.
func TestLoggingWrapperKeepsTheUnderlyingWriterReachable(t *testing.T) {
	var flushErr error
	h := newTestServer().logAndRecover(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		flushErr = http.NewResponseController(w).Flush()
	}))

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/", nil))

	if flushErr != nil || !rec.Flushed {
		t.Errorf("Flush through the wrapper: err=%v flushed=%v, want it to reach the recorder", flushErr, rec.Flushed)
	}
}

func TestJSONTypeNames(t *testing.T) {
	tests := map[reflect.Type]string{
		reflect.TypeOf(""):       "a string",
		reflect.TypeOf(0):        "an integer",
		reflect.TypeOf(int64(0)): "an integer",
		reflect.TypeOf(true):     "of a different type",
	}
	for typ, want := range tests {
		if got := jsonType(typ); got != want {
			t.Errorf("jsonType(%v) = %q, want %q", typ, got, want)
		}
	}
}
