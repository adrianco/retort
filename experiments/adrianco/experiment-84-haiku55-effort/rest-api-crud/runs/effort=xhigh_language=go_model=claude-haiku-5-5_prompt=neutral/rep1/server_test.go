package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

// newTestHandler returns the API backed by a fresh database file, and the store behind it.
func newTestHandler(t *testing.T) (http.Handler, *Store) {
	t.Helper()
	store := openTestStore(t, filepath.Join(t.TempDir(), "books.db"))
	return NewHandler(store), store
}

// send runs one request against h and returns the recorded response.
func send(h http.Handler, method, target, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, target, strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

// decode unmarshals a response body into v and fails the test if the body is not JSON.
func decode(t *testing.T, rec *httptest.ResponseRecorder, v any) {
	t.Helper()
	if err := json.Unmarshal(rec.Body.Bytes(), v); err != nil {
		t.Fatalf("body is not JSON: %v\n%s", err, rec.Body.String())
	}
}

func expectStatus(t *testing.T, rec *httptest.ResponseRecorder, want int) {
	t.Helper()
	if rec.Code != want {
		t.Fatalf("status = %d, want %d; body: %s", rec.Code, want, rec.Body.String())
	}
}

func expectJSONContentType(t *testing.T, rec *httptest.ResponseRecorder) {
	t.Helper()
	if ct := rec.Header().Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`

func TestCreateAndGetBook(t *testing.T) {
	h, _ := newTestHandler(t)

	created := send(h, http.MethodPost, "/books", dune)
	expectStatus(t, created, http.StatusCreated)
	expectJSONContentType(t, created)
	if loc := created.Header().Get("Location"); loc != "/books/1" {
		t.Errorf("Location = %q, want /books/1", loc)
	}

	var book Book
	decode(t, created, &book)
	want := Book{ID: 1, BookInput: BookInput{Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}}
	if book != want {
		t.Errorf("created = %+v, want %+v", book, want)
	}

	got := send(h, http.MethodGet, "/books/1", "")
	expectStatus(t, got, http.StatusOK)
	var fetched Book
	decode(t, got, &fetched)
	if fetched != want {
		t.Errorf("fetched = %+v, want %+v", fetched, want)
	}
}

func TestCreateBookOnlyNeedsTitleAndAuthor(t *testing.T) {
	h, _ := newTestHandler(t)

	rec := send(h, http.MethodPost, "/books", `{"title":"Untitled Notes","author":"Anon"}`)
	expectStatus(t, rec, http.StatusCreated)
	var book Book
	decode(t, rec, &book)
	if book.Year != 0 || book.ISBN != "" {
		t.Errorf("optional fields = year %d isbn %q, want zero values", book.Year, book.ISBN)
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name   string
		body   string
		fields []string // expected keys in the "fields" error map
	}{
		{"missing title and author", `{"year":1965}`, []string{"title", "author"}},
		{"blank title", `{"title":"  ","author":"Anon"}`, []string{"title"}},
		{"missing author", `{"title":"Dune"}`, []string{"author"}},
		{"bad isbn", `{"title":"Dune","author":"Frank Herbert","isbn":"123"}`, []string{"isbn"}},
		{"negative year", `{"title":"Dune","author":"Frank Herbert","year":-5}`, []string{"year"}},
		{"several problems", `{"year":-5,"isbn":"nope"}`, []string{"title", "author", "year", "isbn"}},
		{"malformed json", `{"title":`, nil},
		{"wrong type", `{"title":"Dune","author":"Frank Herbert","year":"1965"}`, nil},
		{"unknown field", `{"title":"Dune","author":"Frank Herbert","rating":5}`, nil},
		{"trailing data", dune + ` {}`, nil},
		{"empty body", ``, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			h, _ := newTestHandler(t)
			rec := send(h, http.MethodPost, "/books", tt.body)
			expectStatus(t, rec, http.StatusBadRequest)
			expectJSONContentType(t, rec)

			var body struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			decode(t, rec, &body)
			if body.Error == "" {
				t.Error("error message is empty")
			}
			if len(tt.fields) == 0 {
				if body.Fields != nil {
					t.Errorf("fields = %v, want none", body.Fields)
				}
			} else {
				for _, f := range tt.fields {
					if _, ok := body.Fields[f]; !ok {
						t.Errorf("fields = %v, missing %q", body.Fields, f)
					}
				}
				if len(body.Fields) != len(tt.fields) {
					t.Errorf("fields = %v, want exactly %v", body.Fields, tt.fields)
				}
			}

			list := send(h, http.MethodGet, "/books", "")
			var books []Book
			decode(t, list, &books)
			if len(books) != 0 {
				t.Errorf("rejected request stored %d book(s)", len(books))
			}
		})
	}
}

func TestCreateBookBodyTooLarge(t *testing.T) {
	h, _ := newTestHandler(t)
	body := `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"A"}`
	expectStatus(t, send(h, http.MethodPost, "/books", body), http.StatusRequestEntityTooLarge)
}

func TestGetBookErrors(t *testing.T) {
	h, _ := newTestHandler(t)

	rec := send(h, http.MethodGet, "/books/999", "")
	expectStatus(t, rec, http.StatusNotFound)
	expectJSONContentType(t, rec)

	for _, id := range []string{"abc", "0", "-3", "1.5"} {
		expectStatus(t, send(h, http.MethodGet, "/books/"+id, ""), http.StatusBadRequest)
	}
}

func TestListBooks(t *testing.T) {
	h, _ := newTestHandler(t)

	empty := send(h, http.MethodGet, "/books", "")
	expectStatus(t, empty, http.StatusOK)
	if got := strings.TrimSpace(empty.Body.String()); got != "[]" {
		t.Errorf("empty list body = %s, want []", got)
	}

	for _, body := range []string{
		`{"title":"A Wizard of Earthsea","author":"Ursula K. Le Guin"}`,
		`{"title":"Dune","author":"Frank Herbert"}`,
		`{"title":"The Dispossessed","author":"Ursula K. Le Guin"}`,
	} {
		expectStatus(t, send(h, http.MethodPost, "/books", body), http.StatusCreated)
	}

	var all []Book
	decode(t, send(h, http.MethodGet, "/books", ""), &all)
	if titles := titlesOf(all); !reflect.DeepEqual(titles, []string{"A Wizard of Earthsea", "Dune", "The Dispossessed"}) {
		t.Errorf("all titles = %v, want insertion order", titles)
	}

	var byAuthor []Book
	rec := send(h, http.MethodGet, "/books?author=ursula+k.+le+guin", "")
	expectStatus(t, rec, http.StatusOK)
	decode(t, rec, &byAuthor)
	if titles := titlesOf(byAuthor); !reflect.DeepEqual(titles, []string{"A Wizard of Earthsea", "The Dispossessed"}) {
		t.Errorf("filtered titles = %v", titles)
	}

	var none []Book
	decode(t, send(h, http.MethodGet, "/books?author=Nobody", ""), &none)
	if none == nil || len(none) != 0 {
		t.Errorf("no-match filter = %v, want []", none)
	}

	var blankFilter []Book
	decode(t, send(h, http.MethodGet, "/books?author=+", ""), &blankFilter)
	if len(blankFilter) != 3 {
		t.Errorf("blank author filter returned %d books, want all 3", len(blankFilter))
	}
}

func TestUpdateBook(t *testing.T) {
	h, _ := newTestHandler(t)
	expectStatus(t, send(h, http.MethodPost, "/books", dune), http.StatusCreated)

	update := `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`
	rec := send(h, http.MethodPut, "/books/1", update)
	expectStatus(t, rec, http.StatusOK)

	var book Book
	decode(t, rec, &book)
	want := Book{ID: 1, BookInput: BookInput{Title: "Dune Messiah", Author: "Frank Herbert", Year: 1969}}
	if book != want {
		t.Errorf("updated = %+v, want %+v (PUT replaces the whole book, so isbn is cleared)", book, want)
	}

	var fetched Book
	decode(t, send(h, http.MethodGet, "/books/1", ""), &fetched)
	if fetched != want {
		t.Errorf("stored = %+v, want %+v", fetched, want)
	}
}

func TestUpdateBookErrors(t *testing.T) {
	h, _ := newTestHandler(t)
	expectStatus(t, send(h, http.MethodPost, "/books", dune), http.StatusCreated)

	expectStatus(t, send(h, http.MethodPut, "/books/999", dune), http.StatusNotFound)
	expectStatus(t, send(h, http.MethodPut, "/books/abc", dune), http.StatusBadRequest)

	invalid := send(h, http.MethodPut, "/books/1", `{"title":"","author":"Frank Herbert"}`)
	expectStatus(t, invalid, http.StatusBadRequest)

	var book Book
	decode(t, send(h, http.MethodGet, "/books/1", ""), &book)
	if book.Title != "Dune" {
		t.Errorf("failed update changed title to %q", book.Title)
	}
}

func TestDeleteBook(t *testing.T) {
	h, _ := newTestHandler(t)
	expectStatus(t, send(h, http.MethodPost, "/books", dune), http.StatusCreated)

	rec := send(h, http.MethodDelete, "/books/1", "")
	expectStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("204 response has body %q", rec.Body.String())
	}

	expectStatus(t, send(h, http.MethodGet, "/books/1", ""), http.StatusNotFound)
	expectStatus(t, send(h, http.MethodDelete, "/books/1", ""), http.StatusNotFound)
}

func TestHealth(t *testing.T) {
	h, store := newTestHandler(t)

	rec := send(h, http.MethodGet, "/health", "")
	expectStatus(t, rec, http.StatusOK)
	expectJSONContentType(t, rec)
	var body map[string]string
	decode(t, rec, &body)
	if body["status"] != "ok" {
		t.Errorf("health body = %v, want status ok", body)
	}

	store.Close()
	expectStatus(t, send(h, http.MethodGet, "/health", ""), http.StatusServiceUnavailable)
}

func TestUnmatchedRoutesReturnJSON(t *testing.T) {
	h, _ := newTestHandler(t)

	tests := []struct {
		method, target string
		status         int
		allow          string
	}{
		{http.MethodGet, "/nope", http.StatusNotFound, ""},
		{http.MethodGet, "/books/", http.StatusNotFound, ""},
		{http.MethodGet, "/books/1/extra", http.StatusNotFound, ""},
		{http.MethodPatch, "/books", http.StatusMethodNotAllowed, "GET, POST"},
		{http.MethodPatch, "/books/1", http.StatusMethodNotAllowed, "GET, PUT, DELETE"},
		{http.MethodPost, "/health", http.StatusMethodNotAllowed, "GET"},
	}
	for _, tt := range tests {
		t.Run(tt.method+" "+tt.target, func(t *testing.T) {
			rec := send(h, tt.method, tt.target, "")
			expectStatus(t, rec, tt.status)
			expectJSONContentType(t, rec)
			if got := rec.Header().Get("Allow"); got != tt.allow {
				t.Errorf("Allow = %q, want %q", got, tt.allow)
			}
			var body map[string]string
			decode(t, rec, &body)
			if body["error"] == "" {
				t.Error("error message is empty")
			}
		})
	}
}

// TestBookLifecycle walks one book through every endpoint in order.
func TestBookLifecycle(t *testing.T) {
	h, _ := newTestHandler(t)

	var created Book
	decode(t, send(h, http.MethodPost, "/books", dune), &created)
	id := fmt.Sprintf("/books/%d", created.ID)

	expectStatus(t, send(h, http.MethodGet, id, ""), http.StatusOK)
	expectStatus(t, send(h, http.MethodPut, id, `{"title":"Dune","author":"Frank Herbert","year":1965}`), http.StatusOK)
	expectStatus(t, send(h, http.MethodDelete, id, ""), http.StatusNoContent)
	expectStatus(t, send(h, http.MethodGet, id, ""), http.StatusNotFound)
}

func titlesOf(books []Book) []string {
	titles := make([]string, len(books))
	for i, b := range books {
		titles[i] = b.Title
	}
	return titles
}
