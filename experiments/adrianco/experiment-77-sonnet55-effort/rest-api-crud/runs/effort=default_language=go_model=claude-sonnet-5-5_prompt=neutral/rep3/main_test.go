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
	return newHandler(s)
}

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	rec := do(setup(t), "GET", "/health", "")
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "ok") {
		t.Fatalf("got %d %s", rec.Code, rec.Body)
	}
}

func TestCRUDLifecycle(t *testing.T) {
	h := setup(t)
	rec := do(h, "POST", "/books", `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"123"}`)
	if rec.Code != 201 {
		t.Fatalf("create: %d %s", rec.Code, rec.Body)
	}
	var b Book
	json.Unmarshal(rec.Body.Bytes(), &b)
	if b.ID == 0 || b.Title != "Dune" {
		t.Fatalf("bad book %+v", b)
	}

	if rec = do(h, "GET", "/books/1", ""); rec.Code != 200 || !strings.Contains(rec.Body.String(), "Frank Herbert") {
		t.Fatalf("get: %d %s", rec.Code, rec.Body)
	}
	rec = do(h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"456"}`)
	if rec.Code != 200 || !strings.Contains(rec.Body.String(), "Dune Messiah") {
		t.Fatalf("update: %d %s", rec.Code, rec.Body)
	}
	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != 204 {
		t.Fatalf("delete: %d", rec.Code)
	}
	if rec = do(h, "GET", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("get after delete: %d", rec.Code)
	}
}

func TestValidation(t *testing.T) {
	h := setup(t)
	for _, body := range []string{
		`{"author":"A"}`, `{"title":"T"}`, `{"title":"  ","author":"A"}`, `not json`, `{"title":"T","author":"A","year":-1}`,
	} {
		if rec := do(h, "POST", "/books", body); rec.Code != 400 {
			t.Errorf("body %q: got %d", body, rec.Code)
		}
	}
	if rec := do(h, "PUT", "/books/1", `{"title":"T"}`); rec.Code != 400 {
		t.Errorf("put invalid: %d", rec.Code)
	}
}

func TestListAndAuthorFilter(t *testing.T) {
	h := setup(t)
	do(h, "POST", "/books", `{"title":"A","author":"X"}`)
	do(h, "POST", "/books", `{"title":"B","author":"Y"}`)
	do(h, "POST", "/books", `{"title":"C","author":"X"}`)

	var all, filtered []Book
	json.Unmarshal(do(h, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(h, "GET", "/books?author=X", "").Body.Bytes(), &filtered)
	if len(all) != 3 || len(filtered) != 2 {
		t.Fatalf("all=%d filtered=%d", len(all), len(filtered))
	}
	rec := do(h, "GET", "/books?author=nobody", "")
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("expected empty array, got %s", rec.Body)
	}
}

func TestNotFoundAndBadID(t *testing.T) {
	h := setup(t)
	if rec := do(h, "GET", "/books/99", ""); rec.Code != 404 {
		t.Errorf("get: %d", rec.Code)
	}
	if rec := do(h, "PUT", "/books/99", `{"title":"T","author":"A"}`); rec.Code != 404 {
		t.Errorf("put: %d", rec.Code)
	}
	if rec := do(h, "DELETE", "/books/99", ""); rec.Code != 404 {
		t.Errorf("delete: %d", rec.Code)
	}
	if rec := do(h, "GET", "/books/abc", ""); rec.Code != 400 {
		t.Errorf("bad id: %d", rec.Code)
	}
}
