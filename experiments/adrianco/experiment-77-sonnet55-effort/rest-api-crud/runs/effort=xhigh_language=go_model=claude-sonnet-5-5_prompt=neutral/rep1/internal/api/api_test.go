package api

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"bookapi/internal/books"
)

func newServer(t *testing.T) (*httptest.Server, *books.Store) {
	t.Helper()
	store, err := books.Open(books.MemoryPath)
	if err != nil {
		t.Fatalf("Open: %v", err)
	}
	srv := httptest.NewServer(New(store, nil))
	t.Cleanup(func() {
		srv.Close()
		store.Close()
	})
	return srv, store
}

// do sends a request and returns the status, headers and raw body.
func do(t *testing.T, method, url, body string) (int, http.Header, []byte) {
	t.Helper()
	var rd io.Reader
	if body != "" {
		rd = strings.NewReader(body)
	}
	req, err := http.NewRequest(method, url, rd)
	if err != nil {
		t.Fatal(err)
	}
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("%s %s: %v", method, url, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		t.Fatal(err)
	}
	return resp.StatusCode, resp.Header, raw
}

func decode[T any](t *testing.T, raw []byte) T {
	t.Helper()
	var v T
	if err := json.Unmarshal(raw, &v); err != nil {
		t.Fatalf("decode %q: %v", raw, err)
	}
	return v
}

func wantStatus(t *testing.T, got, want int, body []byte) {
	t.Helper()
	if got != want {
		t.Fatalf("status = %d, want %d (body: %s)", got, want, body)
	}
}

func createBook(t *testing.T, srv *httptest.Server, body string) books.Book {
	t.Helper()
	status, _, raw := do(t, "POST", srv.URL+"/books", body)
	wantStatus(t, status, http.StatusCreated, raw)
	return decode[books.Book](t, raw)
}

func TestHealth(t *testing.T) {
	srv, _ := newServer(t)
	status, hdr, raw := do(t, "GET", srv.URL+"/health", "")
	wantStatus(t, status, http.StatusOK, raw)
	if got := decode[map[string]string](t, raw)["status"]; got != "ok" {
		t.Errorf("status field = %q, want ok", got)
	}
	if ct := hdr.Get("Content-Type"); ct != "application/json" {
		t.Errorf("Content-Type = %q", ct)
	}
}

func TestHealthReportsUnavailableDatabase(t *testing.T) {
	srv, store := newServer(t)
	store.Close()
	status, _, raw := do(t, "GET", srv.URL+"/health", "")
	wantStatus(t, status, http.StatusServiceUnavailable, raw)
}

func TestCreateBook(t *testing.T) {
	srv, _ := newServer(t)
	status, hdr, raw := do(t, "POST", srv.URL+"/books",
		`{"title":"The Hobbit","author":"J.R.R. Tolkien","year":1937,"isbn":"9780547928227"}`)
	wantStatus(t, status, http.StatusCreated, raw)

	got := decode[books.Book](t, raw)
	want := books.Book{ID: got.ID, Title: "The Hobbit", Author: "J.R.R. Tolkien", Year: 1937, ISBN: "9780547928227"}
	if got != want || got.ID < 1 {
		t.Errorf("created = %+v, want %+v", got, want)
	}
	if loc := hdr.Get("Location"); loc != "/books/"+itoa(got.ID) {
		t.Errorf("Location = %q", loc)
	}

	// It is retrievable afterwards.
	status, _, raw = do(t, "GET", srv.URL+"/books/"+itoa(got.ID), "")
	wantStatus(t, status, http.StatusOK, raw)
	if fetched := decode[books.Book](t, raw); fetched != want {
		t.Errorf("fetched = %+v, want %+v", fetched, want)
	}
}

func TestCreateValidation(t *testing.T) {
	tests := []struct {
		name   string
		body   string
		status int
		field  string // expected key in "fields", if any
	}{
		{"missing title", `{"author":"A"}`, 400, "title"},
		{"empty title", `{"title":"","author":"A"}`, 400, "title"},
		{"whitespace title", `{"title":"  ","author":"A"}`, 400, "title"},
		{"missing author", `{"title":"T"}`, 400, "author"},
		{"null author", `{"title":"T","author":null}`, 400, "author"},
		{"negative year", `{"title":"T","author":"A","year":-5}`, 400, "year"},
		{"year wrong type", `{"title":"T","author":"A","year":"1999"}`, 400, ""},
		{"fractional year", `{"title":"T","author":"A","year":1999.5}`, 400, ""},
		{"malformed JSON", `{"title":`, 400, ""},
		{"not an object", `["title"]`, 400, ""},
		{"trailing document", `{"title":"T","author":"A"}{"title":"U","author":"B"}`, 400, ""},
		{"empty body", ``, 400, ""},
	}
	srv, store := newServer(t)
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			status, hdr, raw := do(t, "POST", srv.URL+"/books", tc.body)
			wantStatus(t, status, tc.status, raw)
			if ct := hdr.Get("Content-Type"); ct != "application/json" {
				t.Errorf("Content-Type = %q, want application/json", ct)
			}
			body := decode[errorBody](t, raw)
			if body.Error == "" {
				t.Error("error message missing")
			}
			if tc.field != "" && body.Fields[tc.field] == "" {
				t.Errorf("fields = %v, want an entry for %q", body.Fields, tc.field)
			}
		})
	}

	if all, _ := store.List(t.Context(), ""); len(all) != 0 {
		t.Errorf("invalid requests created %d books", len(all))
	}
}

func TestCreateReportsAllInvalidFields(t *testing.T) {
	srv, _ := newServer(t)
	status, _, raw := do(t, "POST", srv.URL+"/books", `{}`)
	wantStatus(t, status, http.StatusBadRequest, raw)
	fields := decode[errorBody](t, raw).Fields
	if fields["title"] == "" || fields["author"] == "" {
		t.Errorf("fields = %v, want both title and author", fields)
	}
}

func TestBodyTooLarge(t *testing.T) {
	srv, _ := newServer(t)
	body := `{"title":"` + strings.Repeat("x", maxBodyBytes) + `","author":"A"}`
	status, _, raw := do(t, "POST", srv.URL+"/books", body)
	wantStatus(t, status, http.StatusRequestEntityTooLarge, raw)
}

func TestListAndAuthorFilter(t *testing.T) {
	srv, _ := newServer(t)

	status, _, raw := do(t, "GET", srv.URL+"/books", "")
	wantStatus(t, status, http.StatusOK, raw)
	if strings.TrimSpace(string(raw)) != "[]" {
		t.Errorf("empty list body = %q, want []", raw)
	}

	createBook(t, srv, `{"title":"Emma","author":"Jane Austen","year":1815}`)
	createBook(t, srv, `{"title":"Dune","author":"Frank Herbert","year":1965}`)
	createBook(t, srv, `{"title":"Persuasion","author":"Jane Austen","year":1817}`)

	titles := func(query string) []string {
		t.Helper()
		status, _, raw := do(t, "GET", srv.URL+"/books"+query, "")
		wantStatus(t, status, http.StatusOK, raw)
		var out []string
		for _, b := range decode[[]books.Book](t, raw) {
			out = append(out, b.Title)
		}
		return out
	}
	eq := func(got []string, want ...string) {
		t.Helper()
		if strings.Join(got, "|") != strings.Join(want, "|") {
			t.Errorf("got %v, want %v", got, want)
		}
	}

	eq(titles(""), "Emma", "Dune", "Persuasion")
	eq(titles("?author=Jane+Austen"), "Emma", "Persuasion")
	eq(titles("?author=Jane%20Austen"), "Emma", "Persuasion")
	eq(titles("?author=jane+austen"), "Emma", "Persuasion")
	eq(titles("?author=Frank+Herbert"), "Dune")
	eq(titles("?author=Nobody"))
	eq(titles("?author="), "Emma", "Dune", "Persuasion")
}

func TestGetBook(t *testing.T) {
	srv, _ := newServer(t)
	b := createBook(t, srv, `{"title":"T","author":"A"}`)

	status, _, raw := do(t, "GET", srv.URL+"/books/"+itoa(b.ID), "")
	wantStatus(t, status, http.StatusOK, raw)

	status, _, raw = do(t, "GET", srv.URL+"/books/9999", "")
	wantStatus(t, status, http.StatusNotFound, raw)
	if decode[errorBody](t, raw).Error == "" {
		t.Error("404 body has no error message")
	}

	for _, id := range []string{"abc", "0", "-1", "1.5", "99999999999999999999"} {
		status, _, raw = do(t, "GET", srv.URL+"/books/"+id, "")
		wantStatus(t, status, http.StatusBadRequest, raw)
	}
}

func TestUpdateBook(t *testing.T) {
	srv, _ := newServer(t)
	b := createBook(t, srv, `{"title":"Old","author":"A","year":1990,"isbn":"1"}`)
	url := srv.URL + "/books/" + itoa(b.ID)

	status, _, raw := do(t, "PUT", url, `{"title":"New","author":"B","year":2001,"isbn":"2"}`)
	wantStatus(t, status, http.StatusOK, raw)
	want := books.Book{ID: b.ID, Title: "New", Author: "B", Year: 2001, ISBN: "2"}
	if got := decode[books.Book](t, raw); got != want {
		t.Errorf("PUT response = %+v, want %+v", got, want)
	}

	_, _, raw = do(t, "GET", url, "")
	if got := decode[books.Book](t, raw); got != want {
		t.Errorf("after PUT GET = %+v, want %+v", got, want)
	}

	// PUT replaces the record: omitted optional fields are cleared.
	status, _, raw = do(t, "PUT", url, `{"title":"Bare","author":"B"}`)
	wantStatus(t, status, http.StatusOK, raw)
	if got := decode[books.Book](t, raw); got.Year != 0 || got.ISBN != "" {
		t.Errorf("optional fields not cleared: %+v", got)
	}

	// Invalid update is rejected and leaves the record untouched.
	status, _, raw = do(t, "PUT", url, `{"title":"","author":"B"}`)
	wantStatus(t, status, http.StatusBadRequest, raw)
	_, _, raw = do(t, "GET", url, "")
	if got := decode[books.Book](t, raw); got.Title != "Bare" {
		t.Errorf("record changed by invalid update: %+v", got)
	}

	status, _, raw = do(t, "PUT", srv.URL+"/books/9999", `{"title":"T","author":"A"}`)
	wantStatus(t, status, http.StatusNotFound, raw)
	status, _, raw = do(t, "PUT", srv.URL+"/books/abc", `{"title":"T","author":"A"}`)
	wantStatus(t, status, http.StatusBadRequest, raw)
}

func TestDeleteBook(t *testing.T) {
	srv, _ := newServer(t)
	b := createBook(t, srv, `{"title":"T","author":"A"}`)
	url := srv.URL + "/books/" + itoa(b.ID)

	status, _, raw := do(t, "DELETE", url, "")
	wantStatus(t, status, http.StatusNoContent, raw)
	if len(raw) != 0 {
		t.Errorf("204 response has body %q", raw)
	}

	status, _, raw = do(t, "GET", url, "")
	wantStatus(t, status, http.StatusNotFound, raw)
	status, _, raw = do(t, "DELETE", url, "")
	wantStatus(t, status, http.StatusNotFound, raw)
	status, _, raw = do(t, "DELETE", srv.URL+"/books/abc", "")
	wantStatus(t, status, http.StatusBadRequest, raw)
}

func TestRoutingErrorsAreJSON(t *testing.T) {
	srv, _ := newServer(t)
	tests := []struct {
		method, path string
		status       int
		allow        string
	}{
		{"GET", "/nope", 404, ""},
		{"GET", "/", 404, ""},
		{"GET", "/books/1/extra", 404, ""},
		{"POST", "/health", 405, "GET"},
		{"DELETE", "/books", 405, "GET, POST"},
		{"PATCH", "/books/1", 405, "GET, PUT, DELETE"},
		{"POST", "/books/1", 405, "GET, PUT, DELETE"},
	}
	for _, tc := range tests {
		t.Run(tc.method+" "+tc.path, func(t *testing.T) {
			status, hdr, raw := do(t, tc.method, srv.URL+tc.path, "")
			wantStatus(t, status, tc.status, raw)
			if ct := hdr.Get("Content-Type"); ct != "application/json" {
				t.Errorf("Content-Type = %q, want application/json", ct)
			}
			if decode[errorBody](t, raw).Error == "" {
				t.Error("error message missing")
			}
			if got := hdr.Get("Allow"); got != tc.allow {
				t.Errorf("Allow = %q, want %q", got, tc.allow)
			}
		})
	}
}

func TestPanicIsRecovered(t *testing.T) {
	h := New(panicStore{}, nil)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest("GET", "/books", nil))
	wantStatus(t, rec.Code, http.StatusInternalServerError, rec.Body.Bytes())
	if decode[errorBody](t, rec.Body.Bytes()).Error == "" {
		t.Error("error message missing")
	}
}

// panicStore panics on List; other methods are never reached.
type panicStore struct{ Store }

func (panicStore) List(_ context.Context, _ string) ([]books.Book, error) { panic("boom") }

func itoa(id int64) string { return strconv.FormatInt(id, 10) }
