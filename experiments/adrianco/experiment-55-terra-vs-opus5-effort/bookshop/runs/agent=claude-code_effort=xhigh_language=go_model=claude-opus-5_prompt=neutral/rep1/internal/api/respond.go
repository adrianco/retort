package api

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"

	"bookapi/internal/books"
)

// ErrorResponse is the body of every failed request.
//
// Details is populated for validation failures, mapping each rejected field to
// the reason it was rejected.
type ErrorResponse struct {
	Error   string            `json:"error"`
	Details map[string]string `json:"details,omitempty"`
}

// statusError is an error that already knows which HTTP status it deserves.
// Handlers return it for problems the client can fix.
type statusError struct {
	status  int
	message string
}

func (e *statusError) Error() string { return e.message }

func errorf(status int, format string, args ...any) *statusError {
	return &statusError{status: status, message: fmt.Sprintf(format, args...)}
}

// respond writes payload as a JSON body with the given status code.
//
// It marshals into memory first: if encoding fails there is still time to send
// a 500 instead of truncating an already-committed 200 response.
func (s *Server) respond(w http.ResponseWriter, r *http.Request, status int, payload any) {
	body, err := json.Marshal(payload)
	if err != nil {
		s.logger.ErrorContext(r.Context(), "encoding response failed",
			slog.String("path", r.URL.Path), slog.Any("error", err))
		status, body = http.StatusInternalServerError, []byte(`{"error":"internal server error"}`)
	}
	body = append(body, '\n')

	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	// For a HEAD request net/http discards the body but still reports its
	// length, so writing it unconditionally is what yields a correct
	// Content-Length. ServeMux routes HEAD to the GET handlers.
	w.Write(body) //nolint:errcheck // the client hung up; nothing left to do
}

// respondError maps err onto a status code and a JSON error body. Anything it
// does not recognise is a bug on our side: the client sees a bare 500 and the
// details go to the log.
func (s *Server) respondError(w http.ResponseWriter, r *http.Request, err error) {
	// The client vanished mid-request. Whatever we write goes nowhere, and a
	// stack of 500s in the log would be pure noise.
	if r.Context().Err() != nil && errors.Is(err, context.Canceled) {
		s.logger.DebugContext(r.Context(), "client disconnected", slog.String("path", r.URL.Path))
		return
	}

	var (
		validation *books.ValidationError
		status     *statusError
	)
	switch {
	case errors.As(err, &validation):
		s.respond(w, r, http.StatusUnprocessableEntity, ErrorResponse{
			Error:   "validation failed",
			Details: validation.Fields,
		})
	case errors.As(err, &status):
		s.respond(w, r, status.status, ErrorResponse{Error: status.message})
	case errors.Is(err, books.ErrNotFound):
		s.respond(w, r, http.StatusNotFound, ErrorResponse{Error: "book not found"})
	case errors.Is(err, books.ErrDuplicateISBN):
		s.respond(w, r, http.StatusConflict, ErrorResponse{Error: books.ErrDuplicateISBN.Error()})
	default:
		s.logger.ErrorContext(r.Context(), "request failed",
			slog.String("method", r.Method),
			slog.String("path", r.URL.Path),
			slog.Any("error", err))
		s.respond(w, r, http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
	}
}
