package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func testAPI(t *testing.T) *API {
	t.Helper()
	db, err := openDB(filepath.Join(t.TempDir(), "books.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return &API{db}
}
func request(t *testing.T, a *API, method, path, body string, status int) *httptest.ResponseRecorder {
	t.Helper()
	w := httptest.NewRecorder()
	a.ServeHTTP(w, httptest.NewRequest(method, path, strings.NewReader(body)))
	if w.Code != status {
		t.Fatalf("%s %s: got %d want %d: %s", method, path, w.Code, status, w.Body.String())
	}
	if status != 204 && (w.Header().Get("Content-Type") != "application/json" || !json.Valid(w.Body.Bytes())) {
		t.Fatalf("not JSON: %s", w.Body.String())
	}
	return w
}
func TestBookLifecycle(t *testing.T) {
	a := testAPI(t)
	w := request(t, a, "POST", "/books", `{"title":" Dune ","author":" Frank Herbert ","year":1965,"isbn":"9780441172719"}`, 201)
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID <= 0 || b.Title != "Dune" || b.Author != "Frank Herbert" || b.Year != 1965 || b.ISBN != "9780441172719" {
		t.Fatalf("unexpected book: %+v", b)
	}
	path := w.Header().Get("Location")
	got := request(t, a, "GET", path, "", 200)
	if got.Body.String() != w.Body.String() {
		t.Fatal("created and fetched books differ")
	}
	w = request(t, a, "PUT", path, `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"new"}`, 200)
	got = request(t, a, "GET", path, "", 200)
	if got.Body.String() != w.Body.String() || !strings.Contains(got.Body.String(), "Dune Messiah") {
		t.Fatal("update was not persisted")
	}
	w = request(t, a, "DELETE", path, "", 204)
	if w.Body.Len() != 0 {
		t.Fatal("204 must have no body")
	}
	request(t, a, "GET", path, "", 404)
	request(t, a, "DELETE", path, "", 404)
	request(t, a, "PUT", path, `{"title":"x","author":"y"}`, 404)
}
func TestListAndAuthorFilter(t *testing.T) {
	a := testAPI(t)
	if w := request(t, a, "GET", "/books", "", 200); strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatal("empty list must be []")
	}
	for _, body := range []string{`{"title":"One","author":"A"}`, `{"title":"Two","author":"B"}`, `{"title":"Three","author":"A"}`} {
		request(t, a, "POST", "/books", body, 201)
	}
	for _, tc := range []struct {
		path  string
		count int
	}{{"/books", 3}, {"/books?author=A", 2}, {"/books?author=a", 0}, {"/books?author=missing", 0}, {"/books?author=%27%20OR%201%3D1--", 0}} {
		w := request(t, a, "GET", tc.path, "", 200)
		var books []Book
		if err := json.Unmarshal(w.Body.Bytes(), &books); err != nil {
			t.Fatal(err)
		}
		if len(books) != tc.count {
			t.Fatalf("%s got %d books", tc.path, len(books))
		}
	}
}
func TestValidation(t *testing.T) {
	a := testAPI(t)
	request(t, a, "POST", "/books", `{"title":"original","author":"author"}`, 201)
	for _, body := range []string{"", `{`, `null`, `[]`, `{}`, `{"title":"x"}`, `{"author":"a"}`, `{"title":"  ","author":"a"}`, `{"title":"x","author":"\n"}`, `{"title":"x","author":"a","year":"bad"}`, `{"title":"x","author":"a","extra":1}`, `{"title":"x","author":"a"} {}`} {
		for _, method := range []string{"POST", "PUT"} {
			path := "/books"
			if method == "PUT" {
				path += "/1"
			}
			request(t, a, method, path, body, 400)
		}
	}
	request(t, a, "POST", "/books", `{"title":"`+strings.Repeat("x", 1<<20)+`","author":"a"}`, 413)
	w := request(t, a, "GET", "/books/1", "", 200)
	if !strings.Contains(w.Body.String(), "original") {
		t.Fatal("invalid update changed book")
	}
	for _, id := range []string{"abc", "0", "-1", "999999999999999999999999"} {
		request(t, a, "GET", "/books/"+id, "", 400)
	}
	request(t, a, "GET", "/books/999", "", 404)
}
func TestHealthAndRouting(t *testing.T) {
	a := testAPI(t)
	request(t, a, "GET", "/health", "", 200)
	request(t, a, "GET", "/missing", "", 404)
	request(t, a, "GET", "/books/1/extra", "", 404)
	for _, tc := range []struct{ path, allow string }{{"/health", "GET"}, {"/books", "GET, POST"}, {"/books/1", "GET, PUT, DELETE"}} {
		w := request(t, a, http.MethodPatch, tc.path, "", 405)
		if w.Header().Get("Allow") != tc.allow {
			t.Fatal("missing Allow header")
		}
	}
	a.db.Close()
	request(t, a, "GET", "/health", "", 503)
	request(t, a, "GET", "/books", "", 500)
}
func TestPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persistent.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	request(t, &API{db}, "POST", "/books", `{"title":"Persistent","author":"Author"}`, 201)
	if err := db.Close(); err != nil {
		t.Fatal(err)
	}
	db, err = openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	defer db.Close()
	w := request(t, &API{db}, "GET", "/books/1", "", 200)
	if !strings.Contains(w.Body.String(), "Persistent") {
		t.Fatal("book did not survive reopening database")
	}
}
