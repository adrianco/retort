package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func newTestServer(t *testing.T) http.Handler {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewServer(store)
}

func do(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	var r *http.Request
	if body == "" {
		r = httptest.NewRequest(method, path, nil)
	} else {
		r = httptest.NewRequest(method, path, strings.NewReader(body))
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestHealth(t *testing.T) {
	h := newTestServer(t)
	w := do(t, h, http.MethodGet, "/health", "")
	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	var got map[string]string
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode: %v", err)
	}
	if got["status"] != "ok" {
		t.Fatalf("status field = %q, want ok", got["status"])
	}
}

func TestCreateAndGet(t *testing.T) {
	h := newTestServer(t)

	w := do(t, h, http.MethodPost, "/books",
		`{"title":"Go in Action","author":"Kennedy","year":2015,"isbn":"978-1617291784"}`)
	if w.Code != http.StatusCreated {
		t.Fatalf("create status = %d, want 201 (body: %s)", w.Code, w.Body.String())
	}
	var created Book
	if err := json.Unmarshal(w.Body.Bytes(), &created); err != nil {
		t.Fatalf("decode created: %v", err)
	}
	if created.ID == 0 {
		t.Fatal("expected non-zero ID")
	}
	if created.Title != "Go in Action" || created.Author != "Kennedy" {
		t.Fatalf("unexpected created book: %+v", created)
	}

	w = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusOK {
		t.Fatalf("get status = %d, want 200", w.Code)
	}
	var got Book
	if err := json.Unmarshal(w.Body.Bytes(), &got); err != nil {
		t.Fatalf("decode got: %v", err)
	}
	if got != created {
		t.Fatalf("got %+v, want %+v", got, created)
	}
}

func TestCreateValidation(t *testing.T) {
	h := newTestServer(t)

	cases := map[string]string{
		"missing title":  `{"author":"Someone"}`,
		"missing author": `{"title":"Something"}`,
		"blank title":    `{"title":"   ","author":"Someone"}`,
	}
	for name, body := range cases {
		t.Run(name, func(t *testing.T) {
			w := do(t, h, http.MethodPost, "/books", body)
			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400 (body: %s)", w.Code, w.Body.String())
			}
		})
	}
}

func TestListWithAuthorFilter(t *testing.T) {
	h := newTestServer(t)

	create := func(title, author string) {
		body := `{"title":"` + title + `","author":"` + author + `"}`
		w := do(t, h, http.MethodPost, "/books", body)
		if w.Code != http.StatusCreated {
			t.Fatalf("seed create failed: %d %s", w.Code, w.Body.String())
		}
	}
	create("A", "Alice")
	create("B", "Bob")
	create("C", "Alice")

	w := do(t, h, http.MethodGet, "/books", "")
	var all []Book
	json.Unmarshal(w.Body.Bytes(), &all)
	if len(all) != 3 {
		t.Fatalf("list all = %d, want 3", len(all))
	}

	w = do(t, h, http.MethodGet, "/books?author=Alice", "")
	var filtered []Book
	json.Unmarshal(w.Body.Bytes(), &filtered)
	if len(filtered) != 2 {
		t.Fatalf("list by Alice = %d, want 2", len(filtered))
	}
	for _, b := range filtered {
		if b.Author != "Alice" {
			t.Fatalf("filtered book has author %q, want Alice", b.Author)
		}
	}
}

func TestUpdate(t *testing.T) {
	h := newTestServer(t)

	w := do(t, h, http.MethodPost, "/books", `{"title":"Old","author":"Auth"}`)
	var created Book
	json.Unmarshal(w.Body.Bytes(), &created)

	w = do(t, h, http.MethodPut, "/books/"+itoa(created.ID),
		`{"title":"New","author":"Auth","year":2020,"isbn":"123"}`)
	if w.Code != http.StatusOK {
		t.Fatalf("update status = %d, want 200 (body: %s)", w.Code, w.Body.String())
	}
	var updated Book
	json.Unmarshal(w.Body.Bytes(), &updated)
	if updated.Title != "New" || updated.Year != 2020 || updated.ID != created.ID {
		t.Fatalf("unexpected updated book: %+v", updated)
	}
}

func TestDelete(t *testing.T) {
	h := newTestServer(t)

	w := do(t, h, http.MethodPost, "/books", `{"title":"Doomed","author":"Auth"}`)
	var created Book
	json.Unmarshal(w.Body.Bytes(), &created)

	w = do(t, h, http.MethodDelete, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusNoContent {
		t.Fatalf("delete status = %d, want 204", w.Code)
	}

	w = do(t, h, http.MethodGet, "/books/"+itoa(created.ID), "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("get after delete status = %d, want 404", w.Code)
	}
}

func TestGetNotFound(t *testing.T) {
	h := newTestServer(t)
	w := do(t, h, http.MethodGet, "/books/9999", "")
	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want 404", w.Code)
	}
}

func TestCreateRejectsMalformedJSON(t *testing.T) {
	h := newTestServer(t)
	w := do(t, h, http.MethodPost, "/books", `{not json`)
	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400", w.Code)
	}
}

// itoa avoids importing strconv in multiple test helpers.
func itoa(i int64) string {
	return string(jsonNumber(i))
}

func jsonNumber(i int64) []byte {
	b, _ := json.Marshal(i)
	return bytes.TrimSpace(b)
}
