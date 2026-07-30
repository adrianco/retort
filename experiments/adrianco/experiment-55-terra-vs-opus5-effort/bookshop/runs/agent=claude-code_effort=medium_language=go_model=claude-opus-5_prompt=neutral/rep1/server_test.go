package main

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"
)

// newTestServer returns a Server backed by a fresh in-memory database.
func newTestServer(t *testing.T) *Server {
	t.Helper()
	store, err := OpenStore(":memory:")
	if err != nil {
		t.Fatalf("OpenStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store, slog.New(slog.NewTextHandler(io.Discard, nil)))
}

// do performs a request against the server and returns the recorder.
func do(t *testing.T, s *Server, method, target, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, target, nil)
	} else {
		r = httptest.NewRequest(method, target, strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	return w
}

func decodeBook(t *testing.T, w *httptest.ResponseRecorder) Book {
	t.Helper()
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatalf("decode book from %q: %v", w.Body.String(), err)
	}
	return b
}

// seed creates a book and returns it, failing the test if creation fails.
func seed(t *testing.T, s *Server, title, author string, year int, isbn string) Book {
	t.Helper()
	payload, err := json.Marshal(map[string]any{
		"title": title, "author": author, "year": year, "isbn": isbn,
	})
	if err != nil {
		t.Fatalf("marshal seed: %v", err)
	}
	w := do(t, s, http.MethodPost, "/books", string(payload))
	if w.Code != http.StatusCreated {
		t.Fatalf("seed %q: got status %d, body %s", title, w.Code, w.Body.String())
	}
	return decodeBook(t, w)
}

func TestHealth(t *testing.T) {
	s := newTestServer(t)

	w := do(t, s, http.MethodGet, "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("got status %d, want 200", w.Code)
	}
	if got := w.Header().Get("Content-Type"); !strings.HasPrefix(got, "application/json") {
		t.Errorf("Content-Type = %q, want JSON", got)
	}

	var body map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if body["status"] != "ok" {
		t.Errorf(`status = %q, want "ok"`, body["status"])
	}
}

func TestCreateBook(t *testing.T) {
	s := newTestServer(t)

	w := do(t, s, http.MethodPost, "/books",
		`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441013593"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("got status %d, want 201, body %s", w.Code, w.Body.String())
	}

	got := decodeBook(t, w)
	if got.ID == 0 {
		t.Error("expected a generated ID")
	}
	want := Book{ID: got.ID, Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441013593"}
	if got != want {
		t.Errorf("got %+v, want %+v", got, want)
	}
	if loc := w.Header().Get("Location"); loc != "/books/"+itoa(got.ID) {
		t.Errorf("Location = %q, want %q", loc, "/books/"+itoa(got.ID))
	}
}

func TestCreateBookValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantFields []string
	}{
		{"missing title", `{"author":"Ursula K. Le Guin"}`, []string{"title"}},
		{"missing author", `{"title":"The Dispossessed"}`, []string{"author"}},
		{"blank title and author", `{"title":"   ","author":""}`, []string{"title", "author"}},
		{"empty object", `{}`, []string{"title", "author"}},
		{"year out of range", `{"title":"T","author":"A","year":99999}`, []string{"year"}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			s := newTestServer(t)

			w := do(t, s, http.MethodPost, "/books", tc.body)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("got status %d, want 400, body %s", w.Code, w.Body.String())
			}

			var body struct {
				Error  string            `json:"error"`
				Fields map[string]string `json:"fields"`
			}
			if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
				t.Fatalf("decode: %v", err)
			}
			for _, f := range tc.wantFields {
				if _, ok := body.Fields[f]; !ok {
					t.Errorf("expected field %q in error %+v", f, body.Fields)
				}
			}
			if len(body.Fields) != len(tc.wantFields) {
				t.Errorf("got fields %+v, want exactly %v", body.Fields, tc.wantFields)
			}

			// Nothing should have been persisted.
			list := do(t, s, http.MethodGet, "/books", "")
			if list.Body.String() != "[]" {
				t.Errorf("store not empty: %s", list.Body.String())
			}
		})
	}
}

func TestCreateBookMalformedJSON(t *testing.T) {
	s := newTestServer(t)

	for _, body := range []string{`{"title":`, `not json`, `{"title":"T","author":"A","bogus":1}`} {
		w := do(t, s, http.MethodPost, "/books", body)
		if w.Code != http.StatusBadRequest {
			t.Errorf("body %q: got status %d, want 400", body, w.Code)
		}
	}

	// An entirely empty body is rejected too.
	w := httptest.NewRecorder()
	s.ServeHTTP(w, httptest.NewRequest(http.MethodPost, "/books", strings.NewReader("")))
	if w.Code != http.StatusBadRequest {
		t.Errorf("empty body: got status %d, want 400", w.Code)
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	s := newTestServer(t)
	seed(t, s, "Dune", "Frank Herbert", 1965, "1")
	seed(t, s, "Dune Messiah", "Frank Herbert", 1969, "2")
	seed(t, s, "Neuromancer", "William Gibson", 1984, "3")

	all := do(t, s, http.MethodGet, "/books", "")
	if all.Code != http.StatusOK {
		t.Fatalf("got status %d, want 200", all.Code)
	}
	var books []Book
	if err := json.Unmarshal(all.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(books) != 3 {
		t.Fatalf("got %d books, want 3", len(books))
	}

	filtered := do(t, s, http.MethodGet, "/books?author=Frank+Herbert", "")
	if err := json.Unmarshal(filtered.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("got %d books for author filter, want 2: %+v", len(books), books)
	}
	for _, b := range books {
		if b.Author != "Frank Herbert" {
			t.Errorf("unexpected author %q in filtered result", b.Author)
		}
	}

	// The filter is case-insensitive.
	ci := do(t, s, http.MethodGet, "/books?author=frank+herbert", "")
	if err := json.Unmarshal(ci.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(books) != 2 {
		t.Errorf("case-insensitive filter got %d books, want 2", len(books))
	}

	// An unknown author yields an empty array, not null.
	none := do(t, s, http.MethodGet, "/books?author=Nobody", "")
	if none.Body.String() != "[]" {
		t.Errorf("got %q, want []", none.Body.String())
	}
}

func TestGetBook(t *testing.T) {
	s := newTestServer(t)
	created := seed(t, s, "Neuromancer", "William Gibson", 1984, "9780441569595")

	w := do(t, s, http.MethodGet, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusOK {
		t.Fatalf("got status %d, want 200", w.Code)
	}
	if got := decodeBook(t, w); got != created {
		t.Errorf("got %+v, want %+v", got, created)
	}
}

func TestGetBookNotFoundAndBadID(t *testing.T) {
	s := newTestServer(t)

	if w := do(t, s, http.MethodGet, "/books/4242", ""); w.Code != http.StatusNotFound {
		t.Errorf("unknown id: got status %d, want 404", w.Code)
	}
	if w := do(t, s, http.MethodGet, "/books/abc", ""); w.Code != http.StatusBadRequest {
		t.Errorf("non-numeric id: got status %d, want 400", w.Code)
	}
	if w := do(t, s, http.MethodGet, "/books/0", ""); w.Code != http.StatusBadRequest {
		t.Errorf("zero id: got status %d, want 400", w.Code)
	}
}

func TestUpdateBook(t *testing.T) {
	s := newTestServer(t)
	created := seed(t, s, "Neuromancer", "W. Gibson", 1984, "old-isbn")

	w := do(t, s, http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"Neuromancer","author":"William Gibson","year":1984,"isbn":"9780441569595"}`)
	if w.Code != http.StatusOK {
		t.Fatalf("got status %d, want 200, body %s", w.Code, w.Body.String())
	}

	want := Book{ID: created.ID, Title: "Neuromancer", Author: "William Gibson", Year: 1984, ISBN: "9780441569595"}
	if got := decodeBook(t, w); got != want {
		t.Errorf("response: got %+v, want %+v", got, want)
	}

	// The change is persisted.
	reread := do(t, s, http.MethodGet, "/books/"+itoa(created.ID), "")
	if got := decodeBook(t, reread); got != want {
		t.Errorf("after re-read: got %+v, want %+v", got, want)
	}
}

func TestUpdateBookErrors(t *testing.T) {
	s := newTestServer(t)
	created := seed(t, s, "Dune", "Frank Herbert", 1965, "isbn")

	valid := `{"title":"Dune","author":"Frank Herbert"}`
	if w := do(t, s, http.MethodPut, "/books/9999", valid); w.Code != http.StatusNotFound {
		t.Errorf("unknown id: got status %d, want 404", w.Code)
	}

	invalid := `{"title":"","author":"Frank Herbert"}`
	if w := do(t, s, http.MethodPut, "/books/"+itoa(created.ID), invalid); w.Code != http.StatusBadRequest {
		t.Errorf("invalid payload: got status %d, want 400", w.Code)
	}

	// The failed update left the record untouched.
	reread := do(t, s, http.MethodGet, "/books/"+itoa(created.ID), "")
	if got := decodeBook(t, reread); got != created {
		t.Errorf("record mutated: got %+v, want %+v", got, created)
	}
}

func TestDeleteBook(t *testing.T) {
	s := newTestServer(t)
	created := seed(t, s, "Dune", "Frank Herbert", 1965, "isbn")

	w := do(t, s, http.MethodDelete, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("got status %d, want 204", w.Code)
	}
	if w.Body.Len() != 0 {
		t.Errorf("expected empty body, got %q", w.Body.String())
	}

	if g := do(t, s, http.MethodGet, "/books/"+itoa(created.ID), ""); g.Code != http.StatusNotFound {
		t.Errorf("after delete: got status %d, want 404", g.Code)
	}
	// Deleting twice is a 404, not a silent success.
	if again := do(t, s, http.MethodDelete, "/books/"+itoa(created.ID), ""); again.Code != http.StatusNotFound {
		t.Errorf("second delete: got status %d, want 404", again.Code)
	}
}

func TestMethodNotAllowed(t *testing.T) {
	s := newTestServer(t)

	if w := do(t, s, http.MethodPatch, "/books", `{}`); w.Code != http.StatusMethodNotAllowed {
		t.Errorf("PATCH /books: got status %d, want 405", w.Code)
	}
	if w := do(t, s, http.MethodPost, "/books/1", `{}`); w.Code != http.StatusMethodNotAllowed {
		t.Errorf("POST /books/1: got status %d, want 405", w.Code)
	}
}

func TestFullLifecycle(t *testing.T) {
	s := newTestServer(t)

	created := seed(t, s, "The Left Hand of Darkness", "Ursula K. Le Guin", 1969, "9780441478125")

	if w := do(t, s, http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"The Left Hand of Darkness","author":"Ursula K. Le Guin","year":1969,"isbn":"updated"}`,
	); w.Code != http.StatusOK {
		t.Fatalf("update: got status %d", w.Code)
	}

	list := do(t, s, http.MethodGet, "/books?author=Ursula+K.+Le+Guin", "")
	var books []Book
	if err := json.Unmarshal(list.Body.Bytes(), &books); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if len(books) != 1 || books[0].ISBN != "updated" {
		t.Fatalf("got %+v, want one book with isbn %q", books, "updated")
	}

	if w := do(t, s, http.MethodDelete, "/books/"+itoa(created.ID), ""); w.Code != http.StatusNoContent {
		t.Fatalf("delete: got status %d", w.Code)
	}
	if w := do(t, s, http.MethodGet, "/books", ""); w.Body.String() != "[]" {
		t.Errorf("got %q, want []", w.Body.String())
	}
}

// itoa keeps the URL building in the tests readable.
func itoa(id int64) string {
	return strconv.FormatInt(id, 10)
}
