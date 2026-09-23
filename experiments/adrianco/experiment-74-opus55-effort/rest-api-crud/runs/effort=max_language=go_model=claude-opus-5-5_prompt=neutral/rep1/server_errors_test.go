package main

import (
	"fmt"
	"log/slog"
	"maps"
	"net/http"
	"net/http/httptest"
	"slices"
	"strings"
	"testing"
	"time"
)

func TestCreateBookRejectsInvalidInput(t *testing.T) {
	api := newTestAPI(t)
	tests := []struct {
		name       string
		body       string
		wantStatus int
		wantFields []string // the fields reported as invalid, sorted
	}{
		{"missing title", `{"author": "George Orwell"}`, http.StatusBadRequest, []string{"title"}},
		{"missing author", `{"title": "Animal Farm"}`, http.StatusBadRequest, []string{"author"}},
		{"null title", `{"title": null, "author": "George Orwell"}`, http.StatusBadRequest, []string{"title"}},
		{"blank title and author", `{"title": " ", "author": "\t"}`, http.StatusBadRequest, []string{"author", "title"}},
		{"empty object", `{}`, http.StatusBadRequest, []string{"author", "title"}},
		{"null", `null`, http.StatusBadRequest, []string{"author", "title"}},
		{"title too long", `{"title": "` + strings.Repeat("a", maxTitleLen+1) + `", "author": "A"}`, http.StatusBadRequest, []string{"title"}},
		{"title not a string", `{"title": 1984, "author": "George Orwell"}`, http.StatusBadRequest, []string{"title"}},
		{"year zero", `{"title": "Animal Farm", "author": "George Orwell", "year": 0}`, http.StatusBadRequest, []string{"year"}},
		{"year in the future", fmt.Sprintf(`{"title": "Animal Farm", "author": "George Orwell", "year": %d}`, time.Now().Year()+2), http.StatusBadRequest, []string{"year"}},
		{"year as a string", `{"title": "Animal Farm", "author": "George Orwell", "year": "1945"}`, http.StatusBadRequest, []string{"year"}},
		{"fractional year", `{"title": "Animal Farm", "author": "George Orwell", "year": 1945.5}`, http.StatusBadRequest, []string{"year"}},
		{"malformed isbn", `{"title": "Animal Farm", "author": "George Orwell", "isbn": "12-34"}`, http.StatusBadRequest, []string{"isbn"}},
		{"isbn as a number", `{"title": "Animal Farm", "author": "George Orwell", "isbn": 9780451526342}`, http.StatusBadRequest, []string{"isbn"}},
		{"empty body", ``, http.StatusBadRequest, nil},
		{"malformed JSON", `{"title": "Animal Farm",`, http.StatusBadRequest, nil},
		{"array", `[{"title": "Animal Farm", "author": "George Orwell"}]`, http.StatusBadRequest, nil},
		{"two objects", `{"title": "A", "author": "B"} {"title": "C", "author": "D"}`, http.StatusBadRequest, nil},
		{"body too large", `{"title": "` + strings.Repeat("a", maxBodyBytes) + `", "author": "A"}`, http.StatusRequestEntityTooLarge, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			res := api.do(t, http.MethodPost, "/books", tt.body)
			expectStatus(t, res, tt.wantStatus)
			got := decode[errorResponse](t, res)
			if got.Error == "" {
				t.Error("error message is empty")
			}
			if fields := slices.Sorted(maps.Keys(got.Fields)); !slices.Equal(fields, tt.wantFields) {
				t.Errorf("invalid fields = %v, want %v (response: %s)", fields, tt.wantFields, res.body)
			}
		})
	}

	res := api.do(t, http.MethodGet, "/books", nil)
	expectStatus(t, res, http.StatusOK)
	if books := decode[[]Book](t, res); len(books) != 0 {
		t.Errorf("invalid requests stored %d books, want none", len(books))
	}
}

func TestUpdateBookRejectsInvalidInput(t *testing.T) {
	api := newTestAPI(t)
	book := api.createBook(t, map[string]any{"title": "Animal Farm", "author": "George Orwell"})

	res := api.do(t, http.MethodPut, fmt.Sprintf("/books/%d", book.ID), map[string]any{"title": "", "author": "George Orwell"})
	expectStatus(t, res, http.StatusBadRequest)
	if got := decode[errorResponse](t, res); got.Fields["title"] != "is required" {
		t.Errorf("response = %s, want title reported as required", res.body)
	}
	expectBook(t, api.getBook(t, book.ID), book)

	res = api.do(t, http.MethodPut, "/books/999", map[string]any{"title": "Animal Farm", "author": "George Orwell"})
	expectStatus(t, res, http.StatusNotFound)
}

func TestInvalidBookID(t *testing.T) {
	api := newTestAPI(t)
	for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
		for _, method := range []string{http.MethodGet, http.MethodPut, http.MethodDelete} {
			t.Run(method+" "+id, func(t *testing.T) {
				var body any
				if method == http.MethodPut {
					body = map[string]any{"title": "Animal Farm", "author": "George Orwell"}
				}
				res := api.do(t, method, "/books/"+id, body)
				expectStatus(t, res, http.StatusBadRequest)
				if got := decode[errorResponse](t, res); got.Error != "book id must be a positive integer" {
					t.Errorf("error = %q", got.Error)
				}
			})
		}
	}
}

func TestMethodNotAllowed(t *testing.T) {
	api := newTestAPI(t)
	tests := []struct{ method, path, allow string }{
		{http.MethodPatch, "/books/1", "GET, HEAD, PUT, DELETE"},
		{http.MethodPost, "/books/1", "GET, HEAD, PUT, DELETE"},
		{http.MethodPut, "/books", "GET, HEAD, POST"},
		{http.MethodDelete, "/books", "GET, HEAD, POST"},
		{http.MethodPost, "/health", "GET, HEAD"},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.path, func(t *testing.T) {
			res := api.do(t, tt.method, tt.path, nil)
			expectStatus(t, res, http.StatusMethodNotAllowed)
			if got := res.header.Get("Allow"); got != tt.allow {
				t.Errorf("Allow = %q, want %q", got, tt.allow)
			}
			if got := decode[errorResponse](t, res); got.Error == "" {
				t.Error("error message is empty")
			}
		})
	}
}

func TestUnknownPath(t *testing.T) {
	api := newTestAPI(t)
	for _, path := range []string{"/", "/authors", "/books/", "/books/1/reviews"} {
		t.Run(path, func(t *testing.T) {
			res := api.do(t, http.MethodGet, path, nil)
			expectStatus(t, res, http.StatusNotFound)
			if got := decode[errorResponse](t, res); got.Error != "not found" {
				t.Errorf("error = %q, want %q", got.Error, "not found")
			}
		})
	}
}

func TestInternalErrorsAreLoggedButNotExposed(t *testing.T) {
	api := newTestAPI(t)
	api.store.Close() // from now on, every query fails

	res := api.do(t, http.MethodGet, "/books", nil)
	expectStatus(t, res, http.StatusInternalServerError)
	if got := decode[errorResponse](t, res); got.Error != "internal server error" {
		t.Errorf("error = %q, want %q", got.Error, "internal server error")
	}
	if logs := api.logs.String(); !strings.Contains(logs, "database is closed") {
		t.Errorf("the cause was not logged; log:\n%s", logs)
	}
}

func TestPanicsBecomeInternalErrors(t *testing.T) {
	logs := &syncBuffer{}
	s := NewServer(nil, slog.New(slog.NewTextHandler(logs, nil)))
	h := s.recoverPanics(http.HandlerFunc(func(http.ResponseWriter, *http.Request) {
		panic("something went badly wrong")
	}))

	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/books", nil))
	res := response{status: rec.Code, header: rec.Header(), body: rec.Body.Bytes()}
	expectStatus(t, res, http.StatusInternalServerError)
	if got := decode[errorResponse](t, res); got.Error != "internal server error" {
		t.Errorf("error = %q, want %q", got.Error, "internal server error")
	}
	if !strings.Contains(logs.String(), "something went badly wrong") {
		t.Errorf("the panic was not logged; log:\n%s", logs)
	}
}
