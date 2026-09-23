package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func setup(t *testing.T) http.Handler {
	db, err := OpenDB(":memory:")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { db.Close() })
	return NewServer(db)
}

func do(h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, path, strings.NewReader(body))
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	if rec := do(setup(t), "GET", "/health", ""); rec.Code != 200 {
		t.Fatalf("got %d", rec.Code)
	}
}

func TestCRUD(t *testing.T) {
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
	if rec = do(h, "GET", "/books/1", ""); rec.Code != 200 {
		t.Fatalf("get: %d", rec.Code)
	}
	rec = do(h, "PUT", "/books/1", `{"title":"Dune Messiah","author":"Frank Herbert","year":1969}`)
	json.Unmarshal(rec.Body.Bytes(), &b)
	if rec.Code != 200 || b.Title != "Dune Messiah" {
		t.Fatalf("update: %d %s", rec.Code, rec.Body)
	}
	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != 204 {
		t.Fatalf("delete: %d", rec.Code)
	}
	if rec = do(h, "GET", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("get after delete: %d", rec.Code)
	}
	if rec = do(h, "DELETE", "/books/1", ""); rec.Code != 404 {
		t.Fatalf("delete missing: %d", rec.Code)
	}
	if rec = do(h, "GET", "/books/abc", ""); rec.Code != 400 {
		t.Fatalf("bad id: %d", rec.Code)
	}
}

func TestValidation(t *testing.T) {
	h := setup(t)
	for _, body := range []string{`{"author":"x"}`, `{"title":"x"}`, `{"title":"  ","author":"x"}`, `not json`} {
		if rec := do(h, "POST", "/books", body); rec.Code != 400 {
			t.Errorf("body %q: got %d", body, rec.Code)
		}
	}
	do(h, "POST", "/books", `{"title":"a","author":"b"}`)
	if rec := do(h, "PUT", "/books/1", `{"title":""}`); rec.Code != 400 {
		t.Errorf("put validation: %d", rec.Code)
	}
	if rec := do(h, "PUT", "/books/99", `{"title":"a","author":"b"}`); rec.Code != 404 {
		t.Errorf("put missing: %d", rec.Code)
	}
}

func TestListAuthorFilter(t *testing.T) {
	h := setup(t)
	do(h, "POST", "/books", `{"title":"A","author":"Le Guin"}`)
	do(h, "POST", "/books", `{"title":"B","author":"Asimov"}`)
	do(h, "POST", "/books", `{"title":"C","author":"Le Guin"}`)
	var all, filtered []Book
	json.Unmarshal(do(h, "GET", "/books", "").Body.Bytes(), &all)
	json.Unmarshal(do(h, "GET", "/books?author=le+guin", "").Body.Bytes(), &filtered)
	if len(all) != 3 || len(filtered) != 2 {
		t.Fatalf("all=%d filtered=%d", len(all), len(filtered))
	}
	var empty []Book
	rec := do(h, "GET", "/books?author=nobody", "")
	json.Unmarshal(rec.Body.Bytes(), &empty)
	if strings.TrimSpace(rec.Body.String()) != "[]" {
		t.Fatalf("expected [], got %s", rec.Body)
	}
}
