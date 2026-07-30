package api

import (
	"log/slog"
	"net/http"
	"runtime/debug"
	"time"
)

// recoverPanic keeps one broken request from taking the process down. If
// nothing has been written yet the client still gets a well-formed 500.
func (s *Server) recoverPanic(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		recorder, ok := w.(*statusRecorder)
		defer func() {
			panicValue := recover()
			if panicValue == nil {
				return
			}
			s.logger.ErrorContext(r.Context(), "panic serving request",
				slog.String("method", r.Method),
				slog.String("path", r.URL.Path),
				slog.Any("panic", panicValue),
				slog.String("stack", string(debug.Stack())))

			if ok && recorder.wrote {
				// Response already in flight: severing the connection is the
				// only honest signal that the body is incomplete.
				panic(http.ErrAbortHandler)
			}
			s.respond(w, r, http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
		}()
		next.ServeHTTP(w, r)
	})
}

// logRequests emits one structured line per request once it has completed.
func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		recorder := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		next.ServeHTTP(recorder, r)

		s.logger.InfoContext(r.Context(), "request",
			slog.String("method", r.Method),
			slog.String("path", r.URL.Path),
			slog.String("query", r.URL.RawQuery),
			slog.Int("status", recorder.status),
			slog.Duration("duration", time.Since(start)))
	})
}

// statusRecorder remembers the status code on its way to the client so the
// access log can report it.
type statusRecorder struct {
	http.ResponseWriter
	status int
	wrote  bool
}

func (rec *statusRecorder) WriteHeader(status int) {
	if !rec.wrote {
		rec.status = status
		rec.wrote = true
		rec.ResponseWriter.WriteHeader(status)
	}
}

func (rec *statusRecorder) Write(b []byte) (int, error) {
	rec.wrote = true
	return rec.ResponseWriter.Write(b)
}

// Unwrap lets http.ResponseController reach the underlying writer for
// flushing, hijacking and deadlines.
func (rec *statusRecorder) Unwrap() http.ResponseWriter { return rec.ResponseWriter }
