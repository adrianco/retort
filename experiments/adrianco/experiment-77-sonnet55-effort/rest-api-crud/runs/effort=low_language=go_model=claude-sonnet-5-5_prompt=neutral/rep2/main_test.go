package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func setup(t *testing.T) http.Handler {
	t.Helper()
	s, err := NewStore(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	return (&API{s}).routes()
}

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	return w
}

func TestHealth(t *testing.T) {
	if w := do(setup(t), "GET", "/health", ""); w.Code != 200 {
		t.Fatalf("got %d", w.Code)
	}
}

func TestCRUD(t *testing.T) {
	h := setup(t)
	w := do(h, "POST", "/books", `{"title":"Dune","author":"Herbert","year":1965,"isbn":"123"}`)
	if w.Code != 201 {
		t.Fatalf("create: %d %s", w.Code, w.Body)
	}
	var b Book
	json.Unmarshal(w.Body.Bytes(), &b)
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("bad book %+v", b)
	}
	if w = do(h, "GET", "/books/1", ""); w.Code != 200 {
		t.Fatalf("get: %d", w.Code)
	}
	w = do(h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Herbert","year":1969}`)
	if w.Code != 200 || !strings.Contains(w.Body.String(), "Dune Messiah") {
		t.Fatalf("update: %d %s", w.Code, w.Body)
	}
	if w = do(h, "DELETE", "/books/1", ""); w.Code != 204 {
		t.Fatalf("delete: %d", w.Code)
	}
	if w = do(h, "GET", "/books/1", ""); w.Code != 404 {
		t.Fatalf("after delete: %d", w.Code)
	}
	if w = do(h, "PUT", "/books/1", `{"title":"x","author":"y"}`); w.Code != 404 {
		t.Fatalf("put missing: %d", w.Code)
	}
	if w = do(h, "DELETE", "/books/1", ""); w.Code != 404 {
		t.Fatalf("delete missing: %d", w.Code)
	}
}

func TestValidation(t *testing.T) {
	h := setup(t)
	for _, body := range []string{`{"author":"a"}`, `{"title":"t"}`, `{"title":"  ","author":"a"}`, `not json`} {
		if w := do(h, "POST", "/books", body); w.Code != 400 {
			t.Errorf("%q: got %d", body, w.Code)
		}
	}
	if w := do(h, "GET", "/books/abc", ""); w.Code != 400 {
		t.Errorf("bad id: %d", w.Code)
	}
}

func TestListAuthorFilter(t *testing.T) {
	h := setup(t)
	do(h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(h, "POST", "/books", `{"title":"B","author":"Y"}`)
	var all, some []Book
	json.Unmarshal(do(h, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(h, "GET", "/books?author=Y", "").Body.Bytes(), &some)
	if len(all) != 2 || len(some) != 1 || some[0].Title != "B" {
		t.Fatalf("all=%v some=%v", all, some)
	}
}
