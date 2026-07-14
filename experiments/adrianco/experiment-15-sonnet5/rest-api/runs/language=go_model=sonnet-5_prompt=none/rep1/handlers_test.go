package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
)

func newTestAPI(t *testing.T) *API {
	t.Helper()
	store, err := NewStore(":memory:")
	if err != nil {
		t.Fatalf("failed to open store: %v", err)
	}
	t.Cleanup(func() { store.Close() })
	return NewAPI(store)
}

func doRequest(t *testing.T, h http.Handler, method, path string, body any) *httptest.ResponseRecorder {
	t.Helper()
	var reader *bytes.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			t.Fatalf("failed to marshal body: %v", err)
		}
		reader = bytes.NewReader(b)
	} else {
		reader = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, path, reader)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, req)
	return rec
}

func TestHealth(t *testing.T) {
	api := newTestAPI(t)
	rec := doRequest(t, api.Routes(), http.MethodGet, "/health", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestCreateAndGetBook(t *testing.T) {
	api := newTestAPI(t)
	h := api.Routes()

	createRec := doRequest(t, h, http.MethodPost, "/books", Book{
		Title:  "The Hobbit",
		Author: "J.R.R. Tolkien",
		Year:   1937,
		ISBN:   "978-0-261-10221-7",
	})
	if createRec.Code != http.StatusCreated {
		t.Fatalf("expected 201, got %d: %s", createRec.Code, createRec.Body.String())
	}
	var created Book
	if err := json.Unmarshal(createRec.Body.Bytes(), &created); err != nil {
		t.Fatalf("failed to unmarshal response: %v", err)
	}
	if created.ID == 0 {
		t.Fatalf("expected non-zero id")
	}

	getRec := doRequest(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if getRec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", getRec.Code)
	}
	var fetched Book
	if err := json.Unmarshal(getRec.Body.Bytes(), &fetched); err != nil {
		t.Fatalf("failed to unmarshal response: %v", err)
	}
	if fetched.Title != "The Hobbit" || fetched.Author != "J.R.R. Tolkien" {
		t.Fatalf("unexpected book: %+v", fetched)
	}
}

func TestCreateBookValidation(t *testing.T) {
	api := newTestAPI(t)
	h := api.Routes()

	rec := doRequest(t, h, http.MethodPost, "/books", Book{Author: "No Title"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing title, got %d", rec.Code)
	}

	rec = doRequest(t, h, http.MethodPost, "/books", Book{Title: "No Author"})
	if rec.Code != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing author, got %d", rec.Code)
	}
}

func TestListBooksWithAuthorFilter(t *testing.T) {
	api := newTestAPI(t)
	h := api.Routes()

	doRequest(t, h, http.MethodPost, "/books", Book{Title: "Book A", Author: "Author X", Year: 2000})
	doRequest(t, h, http.MethodPost, "/books", Book{Title: "Book B", Author: "Author Y", Year: 2001})
	doRequest(t, h, http.MethodPost, "/books", Book{Title: "Book C", Author: "Author X", Year: 2002})

	rec := doRequest(t, h, http.MethodGet, "/books?author=Author+X", nil)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	var books []Book
	if err := json.Unmarshal(rec.Body.Bytes(), &books); err != nil {
		t.Fatalf("failed to unmarshal response: %v", err)
	}
	if len(books) != 2 {
		t.Fatalf("expected 2 books for Author X, got %d", len(books))
	}
	for _, b := range books {
		if b.Author != "Author X" {
			t.Fatalf("unexpected author in filtered results: %s", b.Author)
		}
	}
}

func TestUpdateAndDeleteBook(t *testing.T) {
	api := newTestAPI(t)
	h := api.Routes()

	createRec := doRequest(t, h, http.MethodPost, "/books", Book{
		Title: "Original Title", Author: "Original Author", Year: 1999,
	})
	var created Book
	json.Unmarshal(createRec.Body.Bytes(), &created)

	updateRec := doRequest(t, h, http.MethodPut, "/books/"+itoa(created.ID), Book{
		Title: "Updated Title", Author: "Updated Author", Year: 2020, ISBN: "123",
	})
	if updateRec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d: %s", updateRec.Code, updateRec.Body.String())
	}
	var updated Book
	json.Unmarshal(updateRec.Body.Bytes(), &updated)
	if updated.Title != "Updated Title" || updated.Year != 2020 {
		t.Fatalf("unexpected updated book: %+v", updated)
	}

	deleteRec := doRequest(t, h, http.MethodDelete, "/books/"+itoa(created.ID), nil)
	if deleteRec.Code != http.StatusNoContent {
		t.Fatalf("expected 204, got %d", deleteRec.Code)
	}

	getRec := doRequest(t, h, http.MethodGet, "/books/"+itoa(created.ID), nil)
	if getRec.Code != http.StatusNotFound {
		t.Fatalf("expected 404 after delete, got %d", getRec.Code)
	}
}

func TestGetNonexistentBook(t *testing.T) {
	api := newTestAPI(t)
	h := api.Routes()

	rec := doRequest(t, h, http.MethodGet, "/books/9999", nil)
	if rec.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", rec.Code)
	}
}

func itoa(id int64) string {
	return strconv.FormatInt(id, 10)
}
