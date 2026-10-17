package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"maps"
	"net/http"
	"net/http/httptest"
	"net/url"
	"reflect"
	"slices"
	"strings"
	"testing"
)

// newTestAPI returns the HTTP handler backed by a fresh database, and the store behind it.
func newTestAPI(t *testing.T) (http.Handler, *Store) {
	t.Helper()
	store := newTestStore(t)
	logger := slog.New(slog.NewTextHandler(io.Discard, nil))
	return NewHandler(store, logger), store
}

// send runs one request through h and returns the recorded response. An empty
// body sends no body at all.
func send(t *testing.T, h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var reqBody io.Reader
	if body != "" {
		reqBody = strings.NewReader(body)
	}
	req := httptest.NewRequest(method, target, reqBody)
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func assertStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

// assertJSON checks the status code and that the response is declared as JSON.
func assertJSON(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	assertStatus(t, rec, want)
	if ct := rec.Header().Get("Content-Type"); ct != "application/json" {
		t.Fatalf("Content-Type = %q, want application/json", ct)
	}
}

func decodeBody(t *testing.T, rec *httptest.ResponseRecorder, v any) {
	t.Helper()
	if err := json.NewDecoder(rec.Body).Decode(v); err != nil {
		t.Fatalf("decode body %q: %v", rec.Body.String(), err)
	}
}

func titlesOf(books []Book) []string {
	var titles []string
	for _, b := range books {
		titles = append(titles, b.Title)
	}
	return titles
}

func TestBookLifecycle(t *testing.T) {
	h, _ := newTestAPI(t)

	rec := send(t, h, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-441-17271-9"}`)
	assertJSON(t, rec, http.StatusCreated)
	if loc := rec.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}
	// The ISBN comes back normalised, so the stored form is canonical.
	want := Book{ID: 1, Title: "Dune", Author: "Frank Herbert", Year: intPtr(1965), ISBN: strPtr("9780441172719")}
	var created Book
	decodeBody(t, rec, &created)
	if !reflect.DeepEqual(created, want) {
		t.Fatalf("created = %+v, want %+v", created, want)
	}

	rec = send(t, h, http.MethodGet, "/books/1", "")
	assertJSON(t, rec, http.StatusOK)
	var fetched Book
	decodeBody(t, rec, &fetched)
	if !reflect.DeepEqual(fetched, want) {
		t.Fatalf("fetched = %+v, want %+v", fetched, want)
	}

	// PUT replaces the record, so the year and ISBN that were not sent are cleared.
	rec = send(t, h, http.MethodPut, "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert"}`)
	assertJSON(t, rec, http.StatusOK)
	var updated Book
	decodeBody(t, rec, &updated)
	wantUpdated := Book{ID: 1, Title: "Dune Messiah", Author: "Frank Herbert"}
	if !reflect.DeepEqual(updated, wantUpdated) {
		t.Fatalf("updated = %+v, want %+v", updated, wantUpdated)
	}

	rec = send(t, h, http.MethodDelete, "/books/1", "")
	assertStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has a body: %q", rec.Body.String())
	}

	rec = send(t, h, http.MethodGet, "/books/1", "")
	assertJSON(t, rec, http.StatusNotFound)
	var e errorBody
	decodeBody(t, rec, &e)
	if e.Error == "" {
		t.Error("404 response has no error message")
	}
}

func TestCreateBookRejectsInvalidInput(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantFields []string // fields reported in a validation error
		wantError  string   // substring of the error message, for non-validation errors
	}{
		{name: "missing title and author", body: `{"year":1965}`, wantFields: []string{"author", "title"}},
		{name: "blank title", body: `{"title":"   ","author":"A"}`, wantFields: []string{"title"}},
		{name: "missing author", body: `{"title":"T"}`, wantFields: []string{"author"}},
		{name: "year out of range", body: `{"title":"T","author":"A","year":3000}`, wantFields: []string{"year"}},
		{name: "invalid ISBN", body: `{"title":"T","author":"A","isbn":"123"}`, wantFields: []string{"isbn"}},
		{name: "year sent as a string", body: `{"title":"T","author":"A","year":"1965"}`, wantFields: []string{"year"}},
		{name: "title sent as a number", body: `{"title":42,"author":"A"}`, wantFields: []string{"title"}},
		{name: "unknown field", body: `{"title":"T","author":"A","isbm":"9780441172719"}`, wantError: "unknown field"},
		{name: "malformed JSON", body: `{"title":`, wantError: "invalid JSON"},
		{name: "empty body", body: ``, wantError: "empty"},
		{name: "array instead of object", body: `[]`, wantError: "JSON object"},
		{name: "two JSON values", body: `{"title":"T","author":"A"}{}`, wantError: "single JSON object"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h, store := newTestAPI(t)

			rec := send(t, h, http.MethodPost, "/books", tt.body)
			assertJSON(t, rec, http.StatusBadRequest)

			var e errorBody
			decodeBody(t, rec, &e)
			if !strings.Contains(e.Error, tt.wantError) {
				t.Errorf("error = %q, want it to contain %q", e.Error, tt.wantError)
			}
			if got := slices.Sorted(maps.Keys(e.Fields)); !slices.Equal(got, tt.wantFields) {
				t.Errorf("fields = %v, want %v", got, tt.wantFields)
			}

			books, err := store.List(t.Context(), "")
			if err != nil {
				t.Fatalf("List: %v", err)
			}
			if len(books) != 0 {
				t.Errorf("rejected request stored %d book(s)", len(books))
			}
		})
	}
}

func TestRequestBodyTooLarge(t *testing.T) {
	h, _ := newTestAPI(t)
	body := `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"A"}`

	rec := send(t, h, http.MethodPost, "/books", body)
	assertJSON(t, rec, http.StatusRequestEntityTooLarge)
}

func TestListBooks(t *testing.T) {
	h, _ := newTestAPI(t)
	for _, body := range []string{
		`{"title":"Dune","author":"Frank Herbert"}`,
		`{"title":"Dune Messiah","author":"Frank Herbert"}`,
		`{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin"}`,
	} {
		assertStatus(t, send(t, h, http.MethodPost, "/books", body), http.StatusCreated)
	}

	all := []string{"Dune", "Dune Messiah", "A Wizard of Earthsea"}
	tests := []struct {
		name   string
		target string
		want   []string
	}{
		{name: "all books in ID order", target: "/books", want: all},
		{name: "author filter matches a substring", target: "/books?author=herbert", want: []string{"Dune", "Dune Messiah"}},
		{name: "author filter ignores surrounding spaces", target: "/books?author=" + url.QueryEscape("  le guin "), want: []string{"A Wizard of Earthsea"}},
		{name: "empty author filter returns everything", target: "/books?author=", want: all},
		{name: "author filter with no match", target: "/books?author=nobody", want: nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			rec := send(t, h, http.MethodGet, tt.target, "")
			assertJSON(t, rec, http.StatusOK)

			var books []Book
			decodeBody(t, rec, &books)
			if got := titlesOf(books); !slices.Equal(got, tt.want) {
				t.Fatalf("titles = %v, want %v", got, tt.want)
			}
		})
	}

	// An empty collection must encode as [], not null.
	rec := send(t, h, http.MethodGet, "/books?author=nobody", "")
	if body := strings.TrimSpace(rec.Body.String()); body != "[]" {
		t.Errorf("empty result body = %q, want []", body)
	}
}

func TestUpdateBookRejectsInvalidBodyWithoutChangingBook(t *testing.T) {
	h, _ := newTestAPI(t)
	assertStatus(t, send(t, h, http.MethodPost, "/books", `{"title":"Dune","author":"Frank Herbert"}`), http.StatusCreated)

	rec := send(t, h, http.MethodPut, "/books/1", `{"title":"","author":"Frank Herbert"}`)
	assertJSON(t, rec, http.StatusBadRequest)

	rec = send(t, h, http.MethodGet, "/books/1", "")
	var book Book
	decodeBody(t, rec, &book)
	if book.Title != "Dune" {
		t.Fatalf("title after rejected update = %q, want Dune", book.Title)
	}
}

func TestMissingAndMalformedBookIDs(t *testing.T) {
	h, _ := newTestAPI(t)
	valid := `{"title":"T","author":"A"}`

	tests := []struct {
		method string
		target string
		body   string
		want   int
	}{
		{http.MethodGet, "/books/999", "", http.StatusNotFound},
		{http.MethodPut, "/books/999", valid, http.StatusNotFound},
		{http.MethodDelete, "/books/999", "", http.StatusNotFound},
		{http.MethodGet, "/books/abc", "", http.StatusBadRequest},
		{http.MethodGet, "/books/0", "", http.StatusBadRequest},
		{http.MethodGet, "/books/-3", "", http.StatusBadRequest},
		{http.MethodGet, "/books/1.5", "", http.StatusBadRequest},
		{http.MethodPut, "/books/abc", valid, http.StatusBadRequest},
		{http.MethodDelete, "/books/abc", "", http.StatusBadRequest},
	}
	for _, tt := range tests {
		rec := send(t, h, tt.method, tt.target, tt.body)
		assertJSON(t, rec, tt.want)
	}
}

func TestDeleteBookTwiceReturnsNotFound(t *testing.T) {
	h, _ := newTestAPI(t)
	assertStatus(t, send(t, h, http.MethodPost, "/books", `{"title":"T","author":"A"}`), http.StatusCreated)

	assertStatus(t, send(t, h, http.MethodDelete, "/books/1", ""), http.StatusNoContent)
	assertJSON(t, send(t, h, http.MethodDelete, "/books/1", ""), http.StatusNotFound)
}

func TestHealth(t *testing.T) {
	h, store := newTestAPI(t)

	rec := send(t, h, http.MethodGet, "/health", "")
	assertJSON(t, rec, http.StatusOK)
	var status map[string]string
	decodeBody(t, rec, &status)
	if status["status"] != "ok" {
		t.Fatalf("health status = %v, want ok", status)
	}

	assertStatus(t, send(t, h, http.MethodHead, "/health", ""), http.StatusOK)

	// With the database closed the service must report itself unavailable.
	if err := store.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}
	rec = send(t, h, http.MethodGet, "/health", "")
	assertJSON(t, rec, http.StatusServiceUnavailable)
}

func TestMethodNotAllowedListsAllowedMethods(t *testing.T) {
	h, _ := newTestAPI(t)
	tests := []struct {
		method string
		target string
		allow  string
	}{
		{http.MethodPut, "/books", "GET, HEAD, POST"},
		{http.MethodDelete, "/books", "GET, HEAD, POST"},
		{http.MethodPost, "/books/1", "DELETE, GET, HEAD, PUT"},
		{http.MethodPatch, "/books/1", "DELETE, GET, HEAD, PUT"},
		{http.MethodPost, "/health", "GET, HEAD"},
	}
	for _, tt := range tests {
		rec := send(t, h, tt.method, tt.target, "")
		assertJSON(t, rec, http.StatusMethodNotAllowed)
		if got := rec.Header().Get("Allow"); got != tt.allow {
			t.Errorf("%s %s: Allow = %q, want %q", tt.method, tt.target, got, tt.allow)
		}
	}
}

func TestUnknownRoutesReturnJSON404(t *testing.T) {
	h, _ := newTestAPI(t)
	for _, target := range []string{"/", "/nope", "/books/1/extra"} {
		assertJSON(t, send(t, h, http.MethodGet, target, ""), http.StatusNotFound)
	}
}
