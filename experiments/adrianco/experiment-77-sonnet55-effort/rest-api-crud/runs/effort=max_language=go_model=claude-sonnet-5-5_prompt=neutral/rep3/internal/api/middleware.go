package api

import (
	"net/http"
	"runtime/debug"
	"time"
)

// statusRecorder remembers the status code written through it so that the
// request can be logged and so that a panic is only answered with a 500 when
// nothing has been sent yet.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(code int) {
	if !r.wroteHeader {
		r.status = code
		r.wroteHeader = true
	}
	r.ResponseWriter.WriteHeader(code)
}

func (r *statusRecorder) Write(p []byte) (int, error) {
	r.wroteHeader = true // an implicit 200 is sent with the first write
	return r.ResponseWriter.Write(p)
}

// Unwrap lets http.ResponseController reach the underlying writer.
func (r *statusRecorder) Unwrap() http.ResponseWriter { return r.ResponseWriter }

// logAndRecover logs one line per request and turns a panic in a handler into
// a logged JSON 500 instead of a dropped connection.
func (s *server) logAndRecover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		defer func() {
			if p := recover(); p != nil {
				if p == http.ErrAbortHandler {
					panic(p) // deliberate abort: let net/http handle it
				}
				s.log.Error("panic while serving request",
					"method", r.Method, "path", r.URL.Path, "panic", p, "stack", string(debug.Stack()))
				if !rec.wroteHeader {
					s.writeError(rec, http.StatusInternalServerError, "internal server error")
				}
			}
			s.log.Info("request",
				"method", r.Method, "path", r.URL.Path, "status", rec.status, "duration", time.Since(start))
		}()

		next.ServeHTTP(rec, r)
	})
}
