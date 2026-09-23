package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"reflect"
	"strconv"
	"strings"
	"time"
)

// maxBodyBytes caps the size of request bodies.
const maxBodyBytes = 1 << 20 // 1 MiB

func (s *server) handleHealth(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Second)
	defer cancel()
	if err := s.store.Ping(ctx); err != nil {
		s.logger.Error("health check failed", "err", err)
		writeJSON(w, http.StatusServiceUnavailable, map[string]string{"status": "unavailable"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func (s *server) handleListBooks(w http.ResponseWriter, r *http.Request) {
	author := strings.TrimSpace(r.URL.Query().Get("author"))
	books, err := s.store.List(r.Context(), author)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, books)
}

func (s *server) handleCreateBook(w http.ResponseWriter, r *http.Request) {
	in, err := decodeBookInput(w, r)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	book, err := s.store.Create(r.Context(), in)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	w.Header().Set("Location", fmt.Sprintf("/books/%d", book.ID))
	writeJSON(w, http.StatusCreated, book)
}

func (s *server) handleGetBook(w http.ResponseWriter, r *http.Request) {
	id, err := bookID(r)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	book, err := s.store.Get(r.Context(), id)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

// handleUpdateBook replaces a book, as PUT semantics require: optional fields
// left out of the body are cleared.
func (s *server) handleUpdateBook(w http.ResponseWriter, r *http.Request) {
	id, err := bookID(r)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	in, err := decodeBookInput(w, r)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	book, err := s.store.Update(r.Context(), id, in)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, book)
}

func (s *server) handleDeleteBook(w http.ResponseWriter, r *http.Request) {
	id, err := bookID(r)
	if err != nil {
		s.writeError(w, r, err)
		return
	}
	if err := s.store.Delete(r.Context(), id); err != nil {
		s.writeError(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// requestError is a problem with the request itself, reported to the client
// verbatim with the given status code.
type requestError struct {
	status int
	msg    string
}

func (e *requestError) Error() string { return e.msg }

func badRequest(format string, args ...any) error {
	return &requestError{status: http.StatusBadRequest, msg: fmt.Sprintf(format, args...)}
}

// bookID parses the {id} path segment.
func bookID(r *http.Request) (int64, error) {
	id, err := strconv.ParseInt(r.PathValue("id"), 10, 64)
	if err != nil {
		return 0, badRequest("book id must be an integer")
	}
	return id, nil
}

// decodeBookInput reads a book from the request body, normalizes it and
// validates it.
func decodeBookInput(w http.ResponseWriter, r *http.Request) (BookInput, error) {
	var in BookInput
	if err := decodeJSON(w, r, &in); err != nil {
		return BookInput{}, err
	}
	in = in.Normalize()
	if err := in.Validate(); err != nil {
		return BookInput{}, err
	}
	return in, nil
}

// decodeJSON decodes a request body holding exactly one JSON value into dst,
// translating decoding failures into client-friendly errors. Unknown fields
// are ignored, so clients may send back a book exactly as they received it.
func decodeJSON(w http.ResponseWriter, r *http.Request, dst any) error {
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, maxBodyBytes))
	err := dec.Decode(dst)
	if err == nil {
		// Anything but whitespace after the first value is an error.
		if !errors.Is(dec.Decode(&struct{}{}), io.EOF) {
			return badRequest("request body must contain a single JSON object")
		}
		return nil
	}

	var syntaxErr *json.SyntaxError
	var typeErr *json.UnmarshalTypeError
	var sizeErr *http.MaxBytesError
	switch {
	case errors.Is(err, io.EOF):
		return badRequest("request body must not be empty")
	case errors.As(err, &sizeErr):
		return &requestError{
			status: http.StatusRequestEntityTooLarge,
			msg:    fmt.Sprintf("request body must not exceed %d bytes", sizeErr.Limit),
		}
	case errors.As(err, &syntaxErr), errors.Is(err, io.ErrUnexpectedEOF):
		return badRequest("request body is not valid JSON")
	case errors.As(err, &typeErr) && typeErr.Field != "":
		return badRequest("%s must be %s", typeErr.Field, jsonTypeName(typeErr.Type))
	case errors.As(err, &typeErr):
		return badRequest("request body must be a JSON object")
	default:
		return badRequest("invalid request body: %v", err)
	}
}

// jsonTypeName describes a Go type in JSON terms, for error messages.
func jsonTypeName(t reflect.Type) string {
	switch t.Kind() {
	case reflect.String:
		return "a string"
	case reflect.Int, reflect.Int8, reflect.Int16, reflect.Int32, reflect.Int64,
		reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return "an integer"
	case reflect.Float32, reflect.Float64:
		return "a number"
	case reflect.Bool:
		return "a boolean"
	default:
		return "of type " + t.String()
	}
}
