package main

import (
	"encoding/json"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
)

func setup(t *testing.T, path string) api {
	t.Helper()
	db, err := openDB(path)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return api{db}
}

func call(t *testing.T, a api, method, path, body string, status int) *httptest.ResponseRecorder {
	t.Helper()
	w := httptest.NewRecorder()
	a.ServeHTTP(w, httptest.NewRequest(method, path, strings.NewReader(body)))
	if w.Code != status {
		t.Fatalf("%s %s returned %d, want %d: %s", method, path, w.Code, status, w.Body.String())
	}
	if status != 204 && (!json.Valid(w.Body.Bytes()) || w.Header().Get("Content-Type") != "application/json") {
		t.Fatal("expected JSON response", w.Body.String())
	}
	return w
}

func TestLifecycle(t *testing.T) {
	a := setup(t, ":memory:")
	w := call(t, a, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"001"}`, 201)
	path := w.Header().Get("Location")
	var b Book
	json.Unmarshal(call(t, a, "GET", path, "", 200).Body.Bytes(), &b)
	if b.ID != 1 || b.Title != "Dune" || b.Author != "Frank Herbert" || b.Year == nil || *b.Year != 1965 || b.ISBN != "001" {
		t.Fatalf("unexpected book %+v", b)
	}
	call(t, a, "PUT", path, `{"title":"Foundation","author":"Isaac Asimov"}`, 200)
	var updated Book
	json.Unmarshal(call(t, a, "GET", path, "", 200).Body.Bytes(), &updated)
	if updated.Title != "Foundation" || updated.Year != nil || updated.ISBN != "" {
		t.Fatal(updated)
	}
	call(t, a, "DELETE", path, "", 204)
	call(t, a, "GET", path, "", 404)
	call(t, a, "DELETE", path, "", 404)
	call(t, a, "PUT", path, `{"title":"A","author":"B"}`, 404)
}

func TestFilteringAndPersistence(t *testing.T) {
	path := filepath.Join(t.TempDir(), "books.db")
	a := setup(t, path)
	call(t, a, "POST", "/books", `{"title":"First","author":"A B"}`, 201)
	call(t, a, "POST", "/books", `{"title":"Second","author":"C"}`, 201)
	a.db.Close()
	a = setup(t, path)
	for query, count := range map[string]int{"": 2, "?author=A+B": 1, "?author=D": 0} {
		var books []Book
		json.Unmarshal(call(t, a, "GET", "/books"+query, "", 200).Body.Bytes(), &books)
		if books == nil || len(books) != count || (count == 1 && books[0].Title != "First") {
			t.Fatalf("%s returned %+v", query, books)
		}
	}
}

func TestValidationAndHealth(t *testing.T) {
	a := setup(t, ":memory:")
	for _, body := range []string{`{"author":"A"}`, `{"title":"A","author":" "}`, `{`, `{"title":"A","author":"B"}{}`} {
		call(t, a, "POST", "/books", body, 400)
	}
	call(t, a, "GET", "/health", "", 200)
	call(t, a, "PATCH", "/books", "", 405)
}
