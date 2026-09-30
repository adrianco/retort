package api

import (
	"log/slog"
	"net/http"
	"time"
)

// statusRecorder remembers the response status so it can be logged, and
// whether headers have gone out so panic recovery knows if it can still
// send a 500.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(status int) {
	if !r.wroteHeader {
		r.status = status
		r.wroteHeader = true
	}
	r.ResponseWriter.WriteHeader(status)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	if !r.wroteHeader {
		r.WriteHeader(http.StatusOK)
	}
	return r.ResponseWriter.Write(b)
}

// Unwrap lets http.ResponseController reach the underlying writer.
func (r *statusRecorder) Unwrap() http.ResponseWriter { return r.ResponseWriter }

// middleware logs each request and converts handler panics into 500 responses.
func middleware(logger *slog.Logger, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		defer func() {
			if p := recover(); p != nil {
				if p == http.ErrAbortHandler {
					panic(p)
				}
				logger.Error("panic serving request", "method", r.Method, "path", r.URL.Path, "panic", p)
				if !rec.wroteHeader {
					writeError(rec, http.StatusInternalServerError, "internal server error")
				}
			}
			logger.Info("request",
				"method", r.Method,
				"path", r.URL.Path,
				"status", rec.status,
				"duration", time.Since(start),
			)
		}()

		next.ServeHTTP(rec, r)
	})
}
