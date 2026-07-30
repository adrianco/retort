package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"
)

// maxBodyBytes caps request bodies; a book record is never large and this
// keeps a malformed or hostile client from exhausting memory.
const maxBodyBytes = 1 << 20 // 1 MiB

// Server wires the HTTP routes to the store.
type Server struct {
	store  *Store
	logger *log.Logger
	now    func() time.Time
	mux    *http.ServeMux
}

// NewServer builds a Server with all routes registered. Pass a nil logger to
// discard request logs.
func NewServer(store *Store, logger *log.Logger) *Server {
	if logger == nil {
		logger = log.New(io.Discard, "", 0)
	}
	s := &Server{store: store, logger: logger, now: time.Now, mux: http.NewServeMux()}
	s.routes()
	return s
}

func (s *Server) routes() {
	s.mux.HandleFunc("GET /health", s.handleHealth)
	s.mux.HandleFunc("POST /books", s.handleCreate)
	s.mux.HandleFunc("GET /books", s.handleList)
	s.mux.HandleFunc("GET /books/{id}", s.handleGet)
	s.mux.HandleFunc("PUT /books/{id}", s.handleUpdate)
	s.mux.HandleFunc("DELETE /books/{id}", s.handleDelete)

	// A known path reached with an unsupported method must answer 405, and an
	// unknown path 404 — both with a JSON body like every other response.
	// ServeMux resolves these after the method-specific patterns above, which
	// are more specific.
	s.mux.HandleFunc("/health", methodNotAllowed(http.MethodGet))
	s.mux.HandleFunc("/books", methodNotAllowed(http.MethodGet, http.MethodPost))
	s.mux.HandleFunc("/books/{id}", methodNotAllowed(http.MethodGet, http.MethodPut, http.MethodDelete))
	s.mux.HandleFunc("/", handleNotFound)
}

// ServeHTTP satisfies http.Handler, logging each request after it completes.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	start := s.now()
	rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
	s.mux.ServeHTTP(rec, r)
	s.logger.Printf("%s %s %s %d %s",
		r.RemoteAddr, r.Method, r.URL.RequestURI(), rec.status, s.now().Sub(start).Round(time.Microsecond))
}

// statusRecorder captures the response status for logging.
type statusRecorder struct {
	http.ResponseWriter
	status      int
	wroteHeader bool
}

func (r *statusRecorder) WriteHeader(status int) {
	if !r.wroteHeader {
		r.status, r.wroteHeader = status, true
	}
	r.ResponseWriter.WriteHeader(status)
}

func (r *statusRecorder) Write(b []byte) (int, error) {
	r.wroteHeader = true
	return r.ResponseWriter.Write(b)
}

// --- handlers ---

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Ping(r.Context()); err != nil {
		s.logger.Printf("health check failed: %v", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{
			"status":   "unavailable",
			"database": "unreachable",
		})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status":   "ok",
		"database": "ok",
	})
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.internalError(w, "create book", err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.internalError(w, "list books", err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.storeError(w, "get book", err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleUpdate(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	in, ok := s.decodeInput(w, r)
	if !ok {
		return
	}
	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.storeError(w, "update book", err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	id, ok := parseID(w, r)
	if !ok {
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.storeError(w, "delete book", err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func handleNotFound(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusNotFound, "no such endpoint: "+r.Method+" "+r.URL.Path, nil)
}

// methodNotAllowed builds a handler that advertises the methods a path does
// support, as RFC 9110 requires of a 405.
func methodNotAllowed(allowed ...string) http.HandlerFunc {
	allow := strings.Join(allowed, ", ")
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Allow", allow)
		writeError(w, http.StatusMethodNotAllowed, r.Method+" is not allowed on "+r.URL.Path+"; allowed: "+allow, nil)
	}
}

// --- helpers ---

// decodeInput reads, validates and normalizes a book payload, writing the
// appropriate 400 response and reporting false if anything is wrong.
func (s *Server) decodeInput(w http.ResponseWriter, r *http.Request) (BookInput, bool) {
	var in BookInput

	if ct := r.Header.Get("Content-Type"); ct != "" && !isJSONContentType(ct) {
		writeError(w, http.StatusUnsupportedMediaType, "Content-Type must be application/json", nil)
		return in, false
	}

	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	// Reject typos like {"titel": ...} instead of silently creating a book
	// with an empty title.
	dec.DisallowUnknownFields()
	if err := dec.Decode(&in); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON body: "+decodeErrMessage(err), nil)
		return in, false
	}
	// Exactly one JSON value is expected.
	if err := dec.Decode(new(json.RawMessage)); err != io.EOF {
		writeError(w, http.StatusBadRequest, "invalid JSON body: unexpected trailing data", nil)
		return in, false
	}

	in.Normalize()
	if err := in.Validate(s.now()); err != nil {
		var ve ValidationError
		if errors.As(err, &ve) {
			writeError(w, http.StatusBadRequest, "validation failed", ve)
			return in, false
		}
		writeError(w, http.StatusBadRequest, err.Error(), nil)
		return in, false
	}
	return in, true
}

// decodeErrMessage keeps decoding failures informative without leaking Go
// internals such as struct type names.
func decodeErrMessage(err error) string {
	var (
		syntaxErr *json.SyntaxError
		typeErr   *json.UnmarshalTypeError
		maxErr    *http.MaxBytesError
	)
	switch {
	case errors.As(err, &syntaxErr):
		return fmt.Sprintf("malformed JSON at byte %d", syntaxErr.Offset)
	case errors.As(err, &typeErr):
		return fmt.Sprintf("field %q must be of type %s", typeErr.Field, typeErr.Type)
	case errors.As(err, &maxErr):
		return fmt.Sprintf("body must not exceed %d bytes", maxBodyBytes)
	case errors.Is(err, io.EOF):
		return "body is empty"
	default:
		// Unknown-field errors arrive as a plain error string.
		return err.Error()
	}
}

func isJSONContentType(ct string) bool {
	media := strings.TrimSpace(strings.SplitN(ct, ";", 2)[0])
	return strings.EqualFold(media, "application/json")
}

// parseID extracts the {id} path value, writing a 400 for anything that is not
// a positive integer.
func parseID(w http.ResponseWriter, r *http.Request) (int64, bool) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		writeError(w, http.StatusBadRequest, fmt.Sprintf("invalid book id %q: must be a positive integer", raw), nil)
		return 0, false
	}
	return id, true
}

// storeError maps store failures to responses: a missing book is a 404,
// anything else is a 500.
func (s *Server) storeError(w http.ResponseWriter, op string, err error) {
	if errors.Is(err, ErrNotFound) {
		writeError(w, http.StatusNotFound, "book not found", nil)
		return
	}
	s.internalError(w, op, err)
}

// internalError logs the underlying cause and returns a generic message, so
// database details never reach the client.
func (s *Server) internalError(w http.ResponseWriter, op string, err error) {
	s.logger.Printf("%s: %v", op, err)
	writeError(w, http.StatusInternalServerError, "internal server error", nil)
}

// errorBody is the shape of every error response.
type errorBody struct {
	Error  string            `json:"error"`
	Fields map[string]string `json:"fields,omitempty"`
}

func writeError(w http.ResponseWriter, status int, msg string, fields map[string]string) {
	writeJSON(w, status, errorBody{Error: msg, Fields: fields})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	body, err := json.Marshal(payload)
	if err != nil {
		// Every payload here is a plain struct or map of strings, so this is
		// unreachable in practice; fail loudly rather than send a 200 with an
		// empty body.
		http.Error(w, `{"error":"internal server error"}`, http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	w.Write(append(body, '\n'))
}
