package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// maxBodyBytes caps request bodies; book records are small.
const maxBodyBytes = 1 << 20 // 1 MiB

// Server wires the HTTP routes to the store.
type Server struct {
	store   *Store
	logger  *slog.Logger
	now     func() time.Time
	handler http.Handler
}

// NewServer builds a Server with all routes and middleware registered.
func NewServer(store *Store, logger *slog.Logger) *Server {
	if logger == nil {
		logger = slog.New(slog.NewTextHandler(io.Discard, nil))
	}
	s := &Server{store: store, logger: logger, now: time.Now}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", s.handleHealth)
	mux.HandleFunc("POST /books", s.handleCreate)
	mux.HandleFunc("GET /books", s.handleList)
	mux.HandleFunc("GET /books/{id}", s.handleGet)
	mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	mux.HandleFunc("DELETE /books/{id}", s.handleDelete)

	// Logging sits outermost so panic-recovered 500s still get a log line.
	s.handler = logRequests(s.logger)(recoverPanics(s.logger)(jsonifyMuxErrors(mux)))
	return s
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) { s.handler.ServeHTTP(w, r) }

// --- handlers ---------------------------------------------------------------

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		s.logger.Error("health check failed", "error", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status": "unavailable",
			"error":  "database unreachable",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeAndValidate(w, r)
	if !ok {
		return
	}

	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	books, err := s.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeAndValidate(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := s.pathID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.writeStoreError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// --- helpers ----------------------------------------------------------------

// pathID parses the {id} path segment, writing a 400 and reporting false if it
// is not a positive integer.
func (s *Server) pathID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, "invalid book id",
			fmt.Sprintf("%q is not a positive integer", raw))
		return 0, false
	}
	return id, true
}

// decodeAndValidate reads the JSON body and validates it, writing a 400 and
// reporting false on any problem.
func (s *Server) decodeAndValidate(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	if ct := r.Header.Get("Content-Type"); ct != "" {
		if mediaType := strings.TrimSpace(strings.Split(ct, ";")[0]); !strings.EqualFold(mediaType, "application/json") {
			writeError(w, http.StatusUnsupportedMediaType,
				"unsupported content type", "expected application/json, got "+mediaType)
			return BookInput{}, false
		}
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxBodyBytes)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()

	var payload bookPayload
	if err := dec.Decode(&payload); err != nil {
		var maxErr *http.MaxBytesError
		if errors.As(err, &maxErr) {
			writeError(w, http.StatusRequestEntityTooLarge, "request body too large",
				fmt.Sprintf("body must be at most %d bytes", maxBodyBytes))
			return BookInput{}, false
		}
		writeError(w, http.StatusBadRequest, "malformed JSON body", decodeMessage(err))
		return BookInput{}, false
	}
	// Reject trailing content so `{...}{...}` is not silently accepted.
	if err := dec.Decode(new(json.RawMessage)); !errors.Is(err, io.EOF) {
		writeError(w, http.StatusBadRequest, "malformed JSON body",
			"body must contain exactly one JSON object")
		return BookInput{}, false
	}

	in, problems := payload.validate(s.now())
	if len(problems) > 0 {
		writeError(w, http.StatusBadRequest, "validation failed", problems...)
		return BookInput{}, false
	}
	return in, true
}

func decodeMessage(err error) string {
	var (
		syntaxErr *json.SyntaxError
		typeErr   *json.UnmarshalTypeError
	)
	switch {
	case errors.As(err, &syntaxErr):
		return fmt.Sprintf("invalid JSON at byte offset %d", syntaxErr.Offset)
	case errors.As(err, &typeErr):
		return fmt.Sprintf("field %q must be of type %s", typeErr.Field, typeErr.Type)
	case errors.Is(err, io.EOF):
		return "body is empty"
	case errors.Is(err, io.ErrUnexpectedEOF):
		// A truncated document, e.g. `{"title":`.
		return "invalid JSON: unexpected end of input"
	default:
		return err.Error()
	}
}

func (s *Server) writeStoreError(w http.ResponseWriter, r *http.Request, err error) {
	switch {
	case errors.Is(err, ErrNotFound):
		writeError(w, http.StatusNotFound, "book not found")
	case errors.Is(err, ErrDuplicateISBN):
		writeError(w, http.StatusConflict, "isbn already in use",
			"another book is already registered with that isbn")
	case errors.Is(err, context.Canceled), errors.Is(err, context.DeadlineExceeded):
		// Client hung up or timed out; nothing useful to send.
		s.logger.Debug("request cancelled", "method", r.Method, "path", r.URL.Path, "error", err)
	default:
		s.logger.Error("internal error", "method", r.Method, "path", r.URL.Path, "error", err)
		writeError(w, http.StatusInternalServerError, "internal server error")
	}
}

// errorBody is the shape of every error response.
type errorBody struct {
	Error   string   `json:"error"`
	Details []string `json:"details,omitempty"`
}

func writeError(w http.ResponseWriter, status int, message string, details ...string) {
	writeJSON(w, status, errorBody{Error: message, Details: details})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	body, err := json.Marshal(payload)
	if err != nil {
		// Only reachable if a handler passes an unmarshalable value.
		http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
		return
	}
	body = append(body, '\n')
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	w.Write(body)
}
