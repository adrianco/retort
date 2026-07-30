package api

import (
	"context"
	"fmt"
	"log/slog"
	"net/http"
	"slices"
	"strconv"
	"strings"
	"time"

	"bookapi/internal/books"
)

// listResponse wraps the collection rather than returning a bare JSON array,
// which leaves room to add pagination metadata without breaking clients.
type listResponse struct {
	Books []books.Book `json:"books"`
	Count int          `json:"count"`
}

// healthResponse is the body of GET /health.
type healthResponse struct {
	Status   string `json:"status"`
	Database string `json:"database"`
}

// handleHealth reports liveness. It touches the database, so a 200 means the
// service can actually serve requests rather than merely being up.
func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()

	if err := s.store.Ping(ctx); err != nil {
		s.logger.ErrorContext(ctx, "health check failed", slog.Any("error", err))
		s.respond(w, r, http.StatusServiceUnavailable, healthResponse{
			Status:   "degraded",
			Database: "unreachable",
		})
		return
	}
	s.respond(w, r, http.StatusOK, healthResponse{Status: "ok", Database: "ok"})
}

// handleCreateBook implements POST /books.
func (s *Server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	var input books.Input
	if err := decodeJSONBody(w, r, &input); err != nil {
		s.respondError(w, r, err)
		return
	}
	if err := input.Validate(s.now()); err != nil {
		s.respondError(w, r, err)
		return
	}

	book, err := s.store.Create(r.Context(), input)
	if err != nil {
		s.respondError(w, r, err)
		return
	}

	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	s.respond(w, r, http.StatusCreated, book)
}

// handleListBooks implements GET /books, optionally filtered by ?author=.
func (s *Server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	if err := rejectUnknownQueryParams(r, "author"); err != nil {
		s.respondError(w, r, err)
		return
	}

	list, err := s.store.List(r.Context(), r.URL.Query().Get("author"))
	if err != nil {
		s.respondError(w, r, err)
		return
	}
	s.respond(w, r, http.StatusOK, listResponse{Books: list, Count: len(list)})
}

// handleGetBook implements GET /books/{id}.
func (s *Server) handleGetBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		s.respondError(w, r, err)
		return
	}

	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.respondError(w, r, err)
		return
	}
	s.respond(w, r, http.StatusOK, book)
}

// handleUpdateBook implements PUT /books/{id}. PUT replaces the whole record,
// so an omitted year or isbn is cleared rather than left alone.
func (s *Server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		s.respondError(w, r, err)
		return
	}

	var input books.Input
	if err := decodeJSONBody(w, r, &input); err != nil {
		s.respondError(w, r, err)
		return
	}
	if err := input.Validate(s.now()); err != nil {
		s.respondError(w, r, err)
		return
	}

	book, err := s.store.Update(r.Context(), id, input)
	if err != nil {
		s.respondError(w, r, err)
		return
	}
	s.respond(w, r, http.StatusOK, book)
}

// handleDeleteBook implements DELETE /books/{id}.
func (s *Server) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := pathID(r)
	if err != nil {
		s.respondError(w, r, err)
		return
	}

	if err := s.store.Delete(r.Context(), id); err != nil {
		s.respondError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// pathID extracts the {id} wildcard. A non-numeric ID is a malformed request
// (400) rather than a missing book (404): no book could ever have that ID.
func pathID(r *http.Request) (int64, error) {
	raw := r.PathValue("id")
	id, err := strconv.ParseInt(raw, 10, 64)
	if err != nil || id < 1 {
		return 0, errorf(http.StatusBadRequest, "book id must be a positive integer, got %q", raw)
	}
	return id, nil
}

// rejectUnknownQueryParams mirrors the strictness of the JSON decoder: a
// misspelled ?auther= should not quietly return the whole collection.
func rejectUnknownQueryParams(r *http.Request, allowed ...string) error {
	for name := range r.URL.Query() {
		if !slices.Contains(allowed, name) {
			return errorf(http.StatusBadRequest, "unknown query parameter %q; supported: %s",
				name, strings.Join(allowed, ", "))
		}
	}
	return nil
}
