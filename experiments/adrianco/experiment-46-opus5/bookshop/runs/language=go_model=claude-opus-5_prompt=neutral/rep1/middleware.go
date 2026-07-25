package main

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"runtime/debug"
	"strconv"
	"strings"
	"time"
)

type middleware func(http.Handler) http.Handler

// jsonifyMuxErrors replaces the plain-text 404/405 responses that http.ServeMux
// produces with the same JSON error shape the handlers use, so every response
// from the API is JSON.
func jsonifyMuxErrors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		next.ServeHTTP(&muxErrorWriter{ResponseWriter: w, request: r}, r)
	})
}

type muxErrorWriter struct {
	http.ResponseWriter
	request     *http.Request
	wroteHeader bool
	// replaced is set once we have substituted a JSON body, after which the
	// original plain-text body is discarded.
	replaced bool
}

func (w *muxErrorWriter) WriteHeader(status int) {
	if w.wroteHeader {
		return
	}
	w.wroteHeader = true

	// Handlers always set a JSON content type, so anything else at these
	// statuses came from the mux itself.
	isJSON := strings.HasPrefix(w.Header().Get("Content-Type"), "application/json")
	if isJSON || (status != http.StatusNotFound && status != http.StatusMethodNotAllowed) {
		w.ResponseWriter.WriteHeader(status)
		return
	}

	body := errorBody{Error: "resource not found", Details: []string{
		"no route matches " + w.request.Method + " " + w.request.URL.Path,
	}}
	if status == http.StatusMethodNotAllowed {
		body = errorBody{Error: "method not allowed", Details: []string{
			w.request.Method + " is not supported on " + w.request.URL.Path +
				"; allowed: " + w.Header().Get("Allow"),
		}}
	}

	encoded, err := json.Marshal(body)
	if err != nil {
		w.ResponseWriter.WriteHeader(status)
		return
	}
	encoded = append(encoded, '\n')

	w.replaced = true
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Content-Length", strconv.Itoa(len(encoded)))
	w.ResponseWriter.WriteHeader(status)
	w.ResponseWriter.Write(encoded)
}

func (w *muxErrorWriter) Write(b []byte) (int, error) {
	if !w.wroteHeader {
		w.WriteHeader(http.StatusOK)
	}
	if w.replaced {
		// Swallow the mux's plain-text body; ours is already written.
		return len(b), nil
	}
	return w.ResponseWriter.Write(b)
}

// logRequests emits one structured line per request.
func logRequests(logger *slog.Logger) middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
			next.ServeHTTP(rec, r)
			logger.Info("request",
				"method", r.Method,
				"path", r.URL.Path,
				"query", r.URL.RawQuery,
				"status", rec.status,
				"bytes", rec.bytes,
				"duration", time.Since(start).String(),
			)
		})
	}
}

// recoverPanics keeps one bad request from taking down the process.
func recoverPanics(logger *slog.Logger) middleware {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if v := recover(); v != nil {
					if v == http.ErrAbortHandler {
						panic(v) // Deliberate abort; let net/http handle it.
					}
					logger.Error("panic recovered",
						"method", r.Method, "path", r.URL.Path,
						"panic", v, "stack", string(debug.Stack()))
					writeError(w, http.StatusInternalServerError, "internal server error")
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}

type statusRecorder struct {
	http.ResponseWriter
	status      int
	bytes       int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(status int) {
	if r.wroteHeader {
		return
	}
	r.wroteHeader = true
	r.status = status
	r.ResponseWriter.WriteHeader(status)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	if !r.wroteHeader {
		r.WriteHeader(http.StatusOK)
	}
	n, err := r.ResponseWriter.Write(b)
	r.bytes += n
	return n, err
}
