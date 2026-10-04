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
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	a.ServeHTTP(w, r)
	if w.Code != status {
		t.Fatalf("%s %s: got %d, want %d: %s", method, path, w.Code, status, w.Body.String())
	}
	if status != 204 && w.Header().Get("Content-Type") != "application/json" {
		t.Fatal("missing JSON content type")
	}
	return w
}

func TestBookLifecycle(t *testing.T) {
	a := testAPI(t)
	w := request(t, a, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`, 201)
	if w.Header().Get("Location") != "/books/1" {
		t.Fatal("incorrect Location")
	}
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.ID != 1 || b.Title != "Dune" || b.Author != "Frank Herbert" || b.Year != 1965 || b.ISBN != "9780441172719" {
		t.Fatalf("unexpected book: %+v", b)
	}
	got := request(t, a, "GET", "/books/1", "", 200)
	if got.Body.String() != w.Body.String() {
		t.Fatal("stored book differs")
	}
	updated := request(t, a, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"updated"}`, 200)
	got = request(t, a, "GET", "/books/1", "", 200)
	if got.Body.String() != updated.Body.String() {
		t.Fatal("update not persisted")
	}
	deleted := request(t, a, "DELETE", "/books/1", "", 204)
	if deleted.Body.Len() != 0 {
		t.Fatal("204 response must be empty")
	}
	request(t, a, "GET", "/books/1", "", 404)
	request(t, a, "DELETE", "/books/1", "", 404)
	request(t, a, "PUT", "/books/1", `{"title":"Missing","author":"Nobody"}`, 404)
}

func TestListAndAuthorFilter(t *testing.T) {
	a := testAPI(t)
	if w := request(t, a, "GET", "/books", "", 200); strings.TrimSpace(w.Body.String()) != "[]" {
		t.Fatal("empty list must be []")
	}
	for _, body := range []string{`{"title":"First","author":"A"}`, `{"title":"Second","author":"B"}`, `{"title":"Third","author":"A"}`} {
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
			t.Fatalf("%s: got %d books", tc.path, len(books))
		}
		for i := 1; i < len(books); i++ {
			if books[i].ID <= books[i-1].ID {
				t.Fatal("incorrect ordering")
			}
		}
	}
}

func TestValidation(t *testing.T) {
	a := testAPI(t)
	request(t, a, "POST", "/books", `{"title":"Original","author":"Author"}`, 201)
	for _, body := range []string{"", `null`, `[]`, `{`, `{}`, `{"title":"T"}`, `{"author":"A"}`, `{"title":"  ","author":"A"}`, `{"title":"T","author":"\t"}`, `{"title":"T","author":"A","year":"bad"}`, `{"title":"T","author":"A","extra":1}`, `{"title":"T","author":"A"} {}`} {
		for _, method := range []string{"POST", "PUT"} {
			path := "/books"
			if method == "PUT" {
				path += "/1"
			}
			request(t, a, method, path, body, 400)
		}
	}
	request(t, a, "POST", "/books", `{"title":"`+strings.Repeat("a", 1<<20)+`","author":"A"}`, 413)
	w := request(t, a, "GET", "/books/1", "", 200)
	if !strings.Contains(w.Body.String(), "Original") {
		t.Fatal("invalid update changed book")
	}
	w = request(t, a, "POST", "/books", `{"title":"  Trimmed  ","author":" Author "}`, 201)
	var b Book
	if err := json.Unmarshal(w.Body.Bytes(), &b); err != nil {
		t.Fatal(err)
	}
	if b.Title != "Trimmed" || b.Author != "Author" {
		t.Fatal("whitespace not trimmed")
	}
}

func TestRoutesAndHealth(t *testing.T) {
	a := testAPI(t)
	request(t, a, "GET", "/health", "", 200)
	for _, path := range []string{"/books/nope", "/books/0", "/books/-1"} {
		request(t, a, "GET", path, "", 400)
	}
	request(t, a, "GET", "/books/999", "", 404)
	request(t, a, "GET", "/unknown", "", 404)
	request(t, a, "GET", "/books/1/extra", "", 404)
	for _, path := range []string{"/books", "/books/1", "/health"} {
		w := request(t, a, http.MethodPatch, path, "", 405)
		if w.Header().Get("Allow") == "" {
			t.Fatal("missing Allow header")
		}
	}
	a.db.Close()
	request(t, a, "GET", "/health", "", 503)
}

func TestPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persistent.db")
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	a := &API{db}
	request(t, a, "POST", "/books", `{"title":"Persistent","author":"Author"}`, 201)
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
		t.Fatal("book lost after reopening")
	}
}
