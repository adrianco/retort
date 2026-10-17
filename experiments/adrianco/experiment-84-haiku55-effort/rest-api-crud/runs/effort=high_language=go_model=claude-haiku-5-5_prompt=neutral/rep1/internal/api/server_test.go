package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	"bookservice/internal/book"
	"bookservice/internal/store"
)

type fixture struct {
	t       *testing.T
	handler http.Handler
}

func newFixture(t *testing.T) *fixture {
	t.Helper()
	st, err := store.Open(filepath.Join(t.TempDir(), "api.db"))
	if err != nil {
		t.Fatalf("store.Open() error = %v", err)
	}
	t.Cleanup(func() { st.Close() })
	return &fixture{t: t, handler: NewHandler(st)}
}

// do sends a request with an optional raw body and returns the recorded response.
func (f *fixture) do(method, path, body string) *httptest.ResponseRecorder {
	f.t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	f.handler.ServeHTTP(w, r)
	return w
}

// create posts a book and returns the stored representation.
func (f *fixture) create(body string) book.Book {
	f.t.Helper()
	w := f.do(http.MethodPost, "/books", body)
	if w.Code != http.StatusCreated {
		f.t.Fatalf("create status = %d, body = %s", w.Code, w.Body)
	}
	return decode[book.Book](f.t, w)
}

func itoa(n int64) string {
	return strconv.FormatInt(n, 10)
}

func decode[T any](t *testing.T, w *httptest.ResponseRecorder) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(w.Body.Bytes(), &v); err != nil {
		t.Fatalf("decode response %q: %v", w.Body.String(), err)
	}
	return v
}

func assertStatus(t *testing.T, w *httptest.ResponseRecorder, want int) {
	t.Helper()
	if w.Code != want {
		t.Fatalf("status = %d, want %d; body = %s", w.Code, want, w.Body)
	}
}

func assertJSONError(t *testing.T, w *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	if ct := w.Header().Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q, want application/json", ct)
	}
	var body map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &body); err != nil {
		t.Fatalf("error body is not JSON: %q", w.Body.String())
	}
	if _, ok := body["error"]; !ok {
		t.Fatalf("error body has no \"error\" key: %v", body)
	}
	return body
}

func TestBookLifecycle(t *testing.T) {
	f := newFixture(t)

	// Create
	created := f.create(`{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"978-0-306-40615-7"}`)
	if created.ID == 0 {
		t.Fatal("created book has no id")
	}
	if created.ISBN != "9780306406157" {
		t.Errorf("ISBN = %q, want normalized 9780306406157", created.ISBN)
	}

	// Get
	w := f.do(http.MethodGet, "/books/"+itoa(created.ID), "")
	assertStatus(t, w, http.StatusOK)
	if got := decode[book.Book](t, w); got != created {
		t.Errorf("GET = %+v, want %+v", got, created)
	}

	// Update (full replacement)
	w = f.do(http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	assertStatus(t, w, http.StatusOK)
	updated := decode[book.Book](t, w)
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "" {
		t.Errorf("PUT returned %+v", updated)
	}

	// Delete
	w = f.do(http.MethodDelete, "/books/"+itoa(created.ID), "")
	assertStatus(t, w, http.StatusNoContent)
	if w.Body.Len() != 0 {
		t.Errorf("DELETE body = %q, want empty", w.Body.String())
	}

	// Gone
	w = f.do(http.MethodGet, "/books/"+itoa(created.ID), "")
	assertStatus(t, w, http.StatusNotFound)
	assertJSONError(t, w)
}

func TestCreateReturnsLocationAndCreated(t *testing.T) {
	f := newFixture(t)
	w := f.do(http.MethodPost, "/books", `{"title":"Emma","author":"Jane Austen"}`)
	assertStatus(t, w, http.StatusCreated)

	created := decode[book.Book](t, w)
	if loc, want := w.Header().Get("Location"), "/books/"+itoa(created.ID); loc != want {
		t.Errorf("Location = %q, want %q", loc, want)
	}
}

func TestCreateIgnoresClientSuppliedID(t *testing.T) {
	f := newFixture(t)
	created := f.create(`{"id":999,"title":"Emma","author":"Jane Austen"}`)
	if created.ID == 999 {
		t.Fatal("server accepted client-supplied id")
	}
}

func TestCreateValidation(t *testing.T) {
	tests := []struct {
		name       string
		body       string
		wantFields []string
	}{
		{"missing title", `{"author":"Jane Austen"}`, []string{"title"}},
		{"missing author", `{"title":"Emma"}`, []string{"author"}},
		{"blank title and author", `{"title":" ","author":" "}`, []string{"title", "author"}},
		{"bad year", `{"title":"Emma","author":"Jane Austen","year":12}`, []string{"year"}},
		{"bad isbn", `{"title":"Emma","author":"Jane Austen","isbn":"123"}`, []string{"isbn"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			w := f.do(http.MethodPost, "/books", tt.body)
			assertStatus(t, w, http.StatusBadRequest)

			body := assertJSONError(t, w)
			details, _ := body["details"].(map[string]any)
			for _, field := range tt.wantFields {
				if _, ok := details[field]; !ok {
					t.Errorf("details %v missing field %q", details, field)
				}
			}

			// A rejected create must not persist anything.
			list := decode[[]book.Book](t, f.do(http.MethodGet, "/books", ""))
			if len(list) != 0 {
				t.Errorf("rejected book was stored: %+v", list)
			}
		})
	}
}

func TestMalformedBodies(t *testing.T) {
	tests := []struct {
		name string
		body string
		code int
	}{
		{"not json", `{"title":`, http.StatusBadRequest},
		{"empty body", ``, http.StatusBadRequest},
		{"json array", `[{"title":"x"}]`, http.StatusBadRequest},
		{"wrong type for year", `{"title":"x","author":"y","year":"1965"}`, http.StatusBadRequest},
		{"trailing second document", `{"title":"x","author":"y"} {"title":"z"}`, http.StatusBadRequest},
		{"trailing garbage", `{"title":"x","author":"y"} junk`, http.StatusBadRequest},
		{"body too large", `{"title":"` + strings.Repeat("a", maxBodyBytes) + `","author":"y"}`, http.StatusRequestEntityTooLarge},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			w := f.do(http.MethodPost, "/books", tt.body)
			assertStatus(t, w, tt.code)
			assertJSONError(t, w)
		})
	}
}

func TestListBooksAndAuthorFilter(t *testing.T) {
	f := newFixture(t)

	// Empty collection must serialize as [], not null.
	w := f.do(http.MethodGet, "/books", "")
	assertStatus(t, w, http.StatusOK)
	if got := strings.TrimSpace(w.Body.String()); got != "[]" {
		t.Errorf("empty list body = %q, want []", got)
	}

	f.create(`{"title":"Dune","author":"Frank Herbert"}`)
	f.create(`{"title":"Emma","author":"Jane Austen"}`)
	f.create(`{"title":"Children of Dune","author":"Frank Herbert"}`)

	all := decode[[]book.Book](t, f.do(http.MethodGet, "/books", ""))
	if len(all) != 3 {
		t.Fatalf("list returned %d books, want 3", len(all))
	}

	filtered := decode[[]book.Book](t, f.do(http.MethodGet, "/books?author=frank%20herbert", ""))
	if len(filtered) != 2 {
		t.Fatalf("author filter returned %d books, want 2: %+v", len(filtered), filtered)
	}
	for _, b := range filtered {
		if b.Author != "Frank Herbert" {
			t.Errorf("filter leaked book by %q", b.Author)
		}
	}

	// An empty author parameter is treated as no filter.
	blank := decode[[]book.Book](t, f.do(http.MethodGet, "/books?author=", ""))
	if len(blank) != 3 {
		t.Errorf("empty author filter returned %d books, want 3", len(blank))
	}

	none := f.do(http.MethodGet, "/books?author=Nobody", "")
	assertStatus(t, none, http.StatusOK)
	if got := strings.TrimSpace(none.Body.String()); got != "[]" {
		t.Errorf("no-match body = %q, want []", got)
	}
}

func TestInvalidIDs(t *testing.T) {
	f := newFixture(t)
	for _, id := range []string{"abc", "0", "-3", "1.5", "99999999999999999999999"} {
		for _, method := range []string{http.MethodGet, http.MethodDelete} {
			w := f.do(method, "/books/"+id, "")
			assertStatus(t, w, http.StatusBadRequest)
			assertJSONError(t, w)
		}
		w := f.do(http.MethodPut, "/books/"+id, `{"title":"x","author":"y"}`)
		assertStatus(t, w, http.StatusBadRequest)
	}
}

func TestNotFoundForUnknownBook(t *testing.T) {
	f := newFixture(t)
	assertStatus(t, f.do(http.MethodGet, "/books/7", ""), http.StatusNotFound)
	assertStatus(t, f.do(http.MethodPut, "/books/7", `{"title":"x","author":"y"}`), http.StatusNotFound)
	assertStatus(t, f.do(http.MethodDelete, "/books/7", ""), http.StatusNotFound)
}

func TestUpdateValidationDoesNotChangeBook(t *testing.T) {
	f := newFixture(t)
	created := f.create(`{"title":"Dune","author":"Frank Herbert"}`)

	w := f.do(http.MethodPut, "/books/"+itoa(created.ID), `{"title":"","author":"Frank Herbert"}`)
	assertStatus(t, w, http.StatusBadRequest)
	assertJSONError(t, w)

	got := decode[book.Book](t, f.do(http.MethodGet, "/books/"+itoa(created.ID), ""))
	if got.Title != "Dune" {
		t.Errorf("title after failed update = %q, want Dune", got.Title)
	}
}

func TestDeleteTwiceReturnsNotFound(t *testing.T) {
	f := newFixture(t)
	created := f.create(`{"title":"Dune","author":"Frank Herbert"}`)

	assertStatus(t, f.do(http.MethodDelete, "/books/"+itoa(created.ID), ""), http.StatusNoContent)
	assertStatus(t, f.do(http.MethodDelete, "/books/"+itoa(created.ID), ""), http.StatusNotFound)
}

func TestHealth(t *testing.T) {
	f := newFixture(t)
	w := f.do(http.MethodGet, "/health", "")
	assertStatus(t, w, http.StatusOK)

	body := decode[map[string]string](t, w)
	if body["status"] != "ok" {
		t.Errorf("health body = %v, want status ok", body)
	}
}

func TestMethodNotAllowedIsJSON(t *testing.T) {
	f := newFixture(t)

	w := f.do(http.MethodPatch, "/books", "")
	assertStatus(t, w, http.StatusMethodNotAllowed)
	if allow := w.Header().Get("Allow"); allow != "GET, POST" {
		t.Errorf("Allow = %q, want \"GET, POST\"", allow)
	}
	assertJSONError(t, w)

	w = f.do(http.MethodPost, "/books/1", "")
	assertStatus(t, w, http.StatusMethodNotAllowed)
	if allow := w.Header().Get("Allow"); allow != "GET, PUT, DELETE" {
		t.Errorf("Allow = %q, want \"GET, PUT, DELETE\"", allow)
	}
}

func TestUnknownRouteIsJSON404(t *testing.T) {
	f := newFixture(t)
	w := f.do(http.MethodGet, "/nope", "")
	assertStatus(t, w, http.StatusNotFound)
	assertJSONError(t, w)
}

func TestPutAcceptsGetRepresentation(t *testing.T) {
	// A client can GET a book, edit it, and PUT the same JSON back. The id in
	// the body must be ignored in favour of the id in the path.
	f := newFixture(t)
	created := f.create(`{"title":"Dune","author":"Frank Herbert"}`)

	raw, err := json.Marshal(created)
	if err != nil {
		t.Fatal(err)
	}
	w := f.do(http.MethodPut, "/books/"+itoa(created.ID), string(raw))
	assertStatus(t, w, http.StatusOK)
	if got := decode[book.Book](t, w); got.ID != created.ID {
		t.Errorf("PUT returned id %d, want %d", got.ID, created.ID)
	}
}
