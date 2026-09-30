package api

import (
	"log/slog"
	"net/http"
	"runtime/debug"
	"time"
)

// statusRecorder remembers the status code of a response and whether the
// response has started, which the middleware needs after the handler returns.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(code int) {
	if !r.wroteHeader {
		r.status, r.wroteHeader = code, true
	}
	r.ResponseWriter.WriteHeader(code)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	if !r.wroteHeader {
		r.status, r.wroteHeader = http.StatusOK, true
	}
	return r.ResponseWriter.Write(b)
}

// Unwrap lets http.ResponseController reach the underlying writer.
func (r *statusRecorder) Unwrap() http.ResponseWriter { return r.ResponseWriter }

// observe logs every request and turns a panic in a handler into a 500
// response, so one bad request cannot take the connection (or the log) down
// silently.
func observe(logger *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		defer func() {
			if v := recover(); v != nil {
				if v == http.ErrAbortHandler {
					panic(v) // deliberate abort: net/http expects it to propagate
				}
				logger.Error("panic while handling request",
					"method", r.Method, "path", r.URL.Path, "panic", v, "stack", string(debug.Stack()))
				if !rec.wroteHeader {
					writeError(rec, http.StatusInternalServerError, "internal server error")
				}
			}
			logger.Info("request",
				"method", r.Method, "path", r.URL.Path, "status", rec.status, "duration", time.Since(start))
		}()

		next.ServeHTTP(rec, r)
	})
}
