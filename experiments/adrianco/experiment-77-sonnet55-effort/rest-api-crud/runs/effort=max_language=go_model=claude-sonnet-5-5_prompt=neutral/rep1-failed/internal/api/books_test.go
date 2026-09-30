package api_test

import (
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"slices"
	"strings"
	"testing"

	"bookapi/internal/api"
	"bookapi/internal/book"
)

func newHandler(t *testing.T) http.Handler {
	t.Helper()
	return api.New(openStore(t), discardLogger())
}

const dune = `{"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}`

// TestBookLifecycle walks one book through every endpoint in turn.
func TestBookLifecycle(t *testing.T) {
	h := newHandler(t)

	// Create.
	rec := send(t, h, http.MethodPost, "/books", dune)
	wantStatus(t, rec, http.StatusCreated)
	wantJSON(t, rec)
	created := decode[book.Book](t, rec)
	want := book.Book{ID: created.ID, Input: book.Input{
		Title: "Dune", Author: "Frank Herbert", Year: 1965, ISBN: "9780441172719",
	}}
	if created != want || created.ID <= 0 {
		t.Fatalf("created = %+v, want %+v with a positive id", created, want)
	}
	if loc := rec.Header().Get("Location"); loc != bookPath(created) {
		t.Errorf("Location = %q, want %q", loc, bookPath(created))
	}

	// Read it back, singly and in the list.
	rec = send(t, h, http.MethodGet, bookPath(created), "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[book.Book](t, rec); got != created {
		t.Errorf("GET = %+v, want %+v", got, created)
	}
	rec = send(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if got := decode[[]book.Book](t, rec); len(got) != 1 || got[0] != created {
		t.Errorf("list = %+v, want just %+v", got, created)
	}

	// Update.
	rec = send(t, h, http.MethodPut, bookPath(created),
		`{"title":"Dune Messiah","author":"Frank Herbert","year":1969,"isbn":"9780593098233"}`)
	wantStatus(t, rec, http.StatusOK)
	wantJSON(t, rec)
	updated := decode[book.Book](t, rec)
	if updated.ID != created.ID || updated.Title != "Dune Messiah" || updated.Year != 1969 || updated.ISBN != "9780593098233" {
		t.Errorf("updated = %+v", updated)
	}
	rec = send(t, h, http.MethodGet, bookPath(created), "")
	if got := decode[book.Book](t, rec); got != updated {
		t.Errorf("GET after PUT = %+v, want %+v", got, updated)
	}

	// Delete.
	rec = send(t, h, http.MethodDelete, bookPath(created), "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("DELETE body = %q, want empty", rec.Body)
	}
	wantError(t, send(t, h, http.MethodGet, bookPath(created), ""), http.StatusNotFound, "book not found")
	rec = send(t, h, http.MethodGet, "/books", "")
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("list after delete = %s, want []", got)
	}
}

func TestCreateBookJSONShape(t *testing.T) {
	h := newHandler(t)
	rec := send(t, h, http.MethodPost, "/books", dune)
	want := `{"id":1,"title":"Dune","author":"Frank Herbert","year":1965,"isbn":"9780441172719"}` + "\n"
	if got := rec.Body.String(); got != want {
		t.Errorf("body = %q, want %q", got, want)
	}
}

func TestCreateBookWithOnlyRequiredFields(t *testing.T) {
	h := newHandler(t)
	got := createBook(t, h, `{"title":"Dune","author":"Frank Herbert"}`)
	if got.Year != 0 || got.ISBN != "" {
		t.Errorf("optional fields = year %d, isbn %q; want the zero values", got.Year, got.ISBN)
	}
}

func TestCreateBookTrimsWhitespace(t *testing.T) {
	h := newHandler(t)
	got := createBook(t, h, `{"title":"  Dune \n","author":"\tFrank Herbert  ","isbn":" 978 "}`)
	if got.Title != "Dune" || got.Author != "Frank Herbert" || got.ISBN != "978" {
		t.Errorf("created = %+v, want surrounding whitespace removed", got)
	}
}

func TestCreateBookIgnoresClientIDAndUnknownFields(t *testing.T) {
	h := newHandler(t)
	got := createBook(t, h, `{"id":99,"title":"Dune","author":"Frank Herbert","rating":5}`)
	if got.ID == 99 {
		t.Error("the client-supplied id was used; ids must be assigned by the server")
	}
	wantError(t, send(t, h, http.MethodGet, "/books/99", ""), http.StatusNotFound, "book not found")
}

func TestCreateBookAcceptsAnyContentType(t *testing.T) {
	h := newHandler(t)
	// curl -d sends application/x-www-form-urlencoded unless told otherwise.
	for _, contentType := range []string{"application/x-www-form-urlencoded", "text/plain", ""} {
		t.Run(contentType, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodPost, "/books", strings.NewReader(dune))
			if contentType != "" {
				req.Header.Set("Content-Type", contentType)
			}
			rec := httptest.NewRecorder()
			h.ServeHTTP(rec, req)
			wantStatus(t, rec, http.StatusCreated)
		})
	}
}

func TestResponsesKeepTextReadable(t *testing.T) {
	h := newHandler(t)
	rec := send(t, h, http.MethodPost, "/books", `{"title":"Q&A <Handbook>","author":"Gabriel García Márquez"}`)
	wantStatus(t, rec, http.StatusCreated)
	body := rec.Body.String()
	for _, want := range []string{`"Q&A <Handbook>"`, `"Gabriel García Márquez"`} {
		if !strings.Contains(body, want) {
			t.Errorf("body %s does not contain %s verbatim", body, want)
		}
	}
}

func TestCreateBookValidation(t *testing.T) {
	h := newHandler(t)
	tests := []struct {
		name   string
		body   string
		fields []string // fields named in the error details, in order
	}{
		{"missing title", `{"author":"A"}`, []string{"title"}},
		{"missing author", `{"title":"T"}`, []string{"author"}},
		{"empty title", `{"title":"","author":"A"}`, []string{"title"}},
		{"blank title", `{"title":"   ","author":"A"}`, []string{"title"}},
		{"blank author", `{"title":"T","author":"\t"}`, []string{"author"}},
		{"null title", `{"title":null,"author":"A"}`, []string{"title"}},
		{"zero-width space only", bookJSON(zeroWidthSpace, "A"), []string{"title"}},
		{"zero-width characters only", bookJSON("A", wordJoiner+byteOrderMark+zeroWidthJoiner), []string{"author"}},
		{"lone surrogate only", `{"title":"\ud800","author":"A"}`, []string{"title"}},
		{"invalid UTF-8 only", "{\"title\":\"\xff\xfe\",\"author\":\"A\"}", []string{"title"}},
		{"empty object", `{}`, []string{"title", "author"}},
		{"null body", `null`, []string{"title", "author"}},
		{"negative year", `{"title":"T","author":"A","year":-1}`, []string{"year"}},
		{"year beyond 9999", `{"title":"T","author":"A","year":10000}`, []string{"year"}},
		{"overlong title", fmt.Sprintf(`{"title":%q,"author":"A"}`, strings.Repeat("x", 256)), []string{"title"}},
		{"overlong isbn", fmt.Sprintf(`{"title":"T","author":"A","isbn":%q}`, strings.Repeat("9", 33)), []string{"isbn"}},
		{"control character", `{"title":"a\u0000b","author":"A"}`, []string{"title"}},
		{"several problems at once", `{"title":"","author":"","year":-5}`, []string{"title", "author", "year"}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := wantError(t, send(t, h, http.MethodPost, "/books", tt.body), http.StatusBadRequest, tt.fields[0])
			var fields []string
			for _, d := range got.Details {
				fields = append(fields, d.Field)
				if d.Message == "" {
					t.Errorf("detail for %q has no message", d.Field)
				}
			}
			if !slices.Equal(fields, tt.fields) {
				t.Errorf("details name fields %v, want %v", fields, tt.fields)
			}
			for _, f := range tt.fields {
				if !strings.Contains(got.Error, f) {
					t.Errorf("error %q does not mention %q", got.Error, f)
				}
			}
		})
	}

	rec := send(t, h, http.MethodGet, "/books", "")
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("rejected requests were stored anyway: %s", got)
	}
}

func TestCreateBookRejectsMalformedBodies(t *testing.T) {
	h := newHandler(t)
	tests := []struct {
		name string
		body string
		want string
	}{
		{"empty body", ``, "must not be empty"},
		{"not JSON", `hello`, "not valid JSON"},
		{"truncated JSON", `{"title":"T",`, "unexpected end of input"},
		{"array", `[1,2,3]`, "must be a JSON object"},
		{"string", `"a book"`, "must be a JSON object"},
		{"year as a string", `{"title":"T","author":"A","year":"1999"}`, `field "year" must be an integer, got string`},
		{"fractional year", `{"title":"T","author":"A","year":1999.5}`, `field "year" must be an integer`},
		{"year too big for an integer", `{"title":"T","author":"A","year":1e400}`, `field "year"`},
		{"title as a number", `{"title":42,"author":"A"}`, `field "title" must be a string, got number`},
		{"author as an object", `{"title":"T","author":{}}`, `field "author" must be a string, got object`},
		{"second JSON value", `{"title":"T","author":"A"} {"title":"U"}`, "single JSON object"},
		{"trailing garbage", `{"title":"T","author":"A"} xyz`, "not valid JSON"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := wantError(t, send(t, h, http.MethodPost, "/books", tt.body), http.StatusBadRequest, tt.want)
			if len(got.Details) != 0 {
				t.Errorf("details = %+v, want none for a body that is not even a book", got.Details)
			}
		})
	}
}

// brokenBody fails the way a connection does when the client drops mid-upload.
type brokenBody struct{}

func (brokenBody) Read([]byte) (int, error) { return 0, errors.New("connection reset by peer") }

func TestCreateBookHandlesUnreadableBody(t *testing.T) {
	h := newHandler(t)
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(http.MethodPost, "/books", brokenBody{}))
	wantError(t, rec, http.StatusBadRequest, "could not be read")
	if strings.Contains(rec.Body.String(), "connection reset") {
		t.Errorf("response leaks the read error: %s", rec.Body)
	}
}

func TestRequestBodyLimitIsOneMiB(t *testing.T) {
	h := newHandler(t)
	const limit = 1 << 20
	bodyOfSize := func(n int) string {
		const prefix, suffix = `{"title":"`, `","author":"A"}`
		return prefix + strings.Repeat("x", n-len(prefix)-len(suffix)) + suffix
	}

	// A body of exactly the limit is read in full, so it is judged on its
	// content (the title is far too long) rather than on its size...
	wantError(t, send(t, h, http.MethodPost, "/books", bodyOfSize(limit)),
		http.StatusBadRequest, "title must be at most")
	// ...while one byte more is refused outright.
	wantError(t, send(t, h, http.MethodPost, "/books", bodyOfSize(limit+1)),
		http.StatusRequestEntityTooLarge, "must not exceed 1048576 bytes")
}

func TestGetBookNotFound(t *testing.T) {
	h := newHandler(t)
	createBook(t, h, dune)
	wantError(t, send(t, h, http.MethodGet, "/books/999", ""), http.StatusNotFound, "book not found")
}

func TestMalformedIDsAreRejected(t *testing.T) {
	h := newHandler(t)
	createBook(t, h, dune) // id 1 exists, so "+1" or "01" aliasing to it would be visible
	ids := []string{
		"abc", "0", "-1", "1.5", "1e3", "0x1", "%20",
		"+1", "01", "001", // would alias book 1 if parsed leniently
		"9223372036854775808", "18446744073709551615", "99999999999999999999", // beyond int64
	}
	requests := []struct{ method, body string }{
		{http.MethodGet, ""},
		{http.MethodPut, dune},
		{http.MethodDelete, ""},
	}
	for _, id := range ids {
		for _, r := range requests {
			t.Run(r.method+" "+id, func(t *testing.T) {
				wantError(t, send(t, h, r.method, "/books/"+id, r.body), http.StatusBadRequest, "positive integer")
			})
		}
	}
	// Nothing above may have touched the stored book.
	if rec := send(t, h, http.MethodGet, "/books/1", ""); rec.Code != http.StatusOK {
		t.Errorf("book 1 is gone or unreadable after the malformed requests: %d", rec.Code)
	}
}

func TestListBooksWhenEmpty(t *testing.T) {
	h := newHandler(t)
	rec := send(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	wantJSON(t, rec)
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("body = %s, want [] (not null)", got)
	}
}

func TestListBooksInCreationOrder(t *testing.T) {
	h := newHandler(t)
	want := []string{"Third", "First", "Second"}
	for _, title := range want {
		createBook(t, h, fmt.Sprintf(`{"title":%q,"author":"A"}`, title))
	}
	rec := send(t, h, http.MethodGet, "/books", "")
	wantStatus(t, rec, http.StatusOK)
	if got := titles(decode[[]book.Book](t, rec)); !slices.Equal(got, want) {
		t.Errorf("titles = %v, want %v", got, want)
	}
}

func TestListBooksFiltersByAuthor(t *testing.T) {
	h := newHandler(t)
	for _, b := range []struct{ title, author string }{
		{"Nineteen Eighty-Four", "George Orwell"},
		{"Brave New World", "Aldous Huxley"},
		{"Animal Farm", "George Orwell"},
	} {
		createBook(t, h, fmt.Sprintf(`{"title":%q,"author":%q}`, b.title, b.author))
	}

	orwell := []string{"Nineteen Eighty-Four", "Animal Farm"}
	all := []string{"Nineteen Eighty-Four", "Brave New World", "Animal Farm"}
	tests := []struct {
		target string
		want   []string
	}{
		{"/books?author=George+Orwell", orwell},
		{"/books?author=George%20Orwell", orwell},
		{"/books?author=george+orwell", orwell},
		{"/books?author=%20GEORGE%20ORWELL%20", orwell},
		{"/books?author=Aldous+Huxley", []string{"Brave New World"}},
		{"/books?author=Orwell", []string{}},
		{"/books?author=Nobody", []string{}},
		{"/books?author=", all},
		{"/books?author=%20", all},
		{"/books", all},
		{"/books?unrelated=1", all},
	}
	for _, tt := range tests {
		t.Run(tt.target, func(t *testing.T) {
			rec := send(t, h, http.MethodGet, tt.target, "")
			wantStatus(t, rec, http.StatusOK)
			if got := titles(decode[[]book.Book](t, rec)); !slices.Equal(got, tt.want) {
				t.Errorf("titles = %v, want %v", got, tt.want)
			}
			if len(tt.want) == 0 {
				if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
					t.Errorf("body = %s, want [] (not null)", got)
				}
			}
		})
	}
}

func TestListBooksRejectsMalformedQueryString(t *testing.T) {
	h := newHandler(t)
	createBook(t, h, dune)
	// A malformed pair must not be dropped silently: that would ignore the
	// filter and answer 200 with every book.
	for _, target := range []string{"/books?author=100%", "/books?author=%zz", "/books?author=a;b"} {
		t.Run(target, func(t *testing.T) {
			wantError(t, send(t, h, http.MethodGet, target, ""), http.StatusBadRequest, "malformed query string")
		})
	}
}

func TestUpdateBook(t *testing.T) {
	h := newHandler(t)
	target := createBook(t, h, dune)
	other := createBook(t, h, `{"title":"Bystander","author":"Someone Else","year":2000}`)

	rec := send(t, h, http.MethodPut, bookPath(target),
		`{"title":"Children of Dune","author":"Frank Herbert","year":1976,"isbn":"9780593098240"}`)
	wantStatus(t, rec, http.StatusOK)
	want := book.Book{ID: target.ID, Input: book.Input{
		Title: "Children of Dune", Author: "Frank Herbert", Year: 1976, ISBN: "9780593098240",
	}}
	if got := decode[book.Book](t, rec); got != want {
		t.Errorf("PUT response = %+v, want %+v", got, want)
	}

	rec = send(t, h, http.MethodGet, bookPath(target), "")
	if got := decode[book.Book](t, rec); got != want {
		t.Errorf("GET after PUT = %+v, want %+v", got, want)
	}
	rec = send(t, h, http.MethodGet, bookPath(other), "")
	if got := decode[book.Book](t, rec); got != other {
		t.Errorf("PUT changed another book: %+v, want %+v", got, other)
	}
}

func TestUpdateBookReplacesTheWholeBook(t *testing.T) {
	h := newHandler(t)
	target := createBook(t, h, dune)

	rec := send(t, h, http.MethodPut, bookPath(target), `{"title":"Dune","author":"Frank Herbert"}`)
	wantStatus(t, rec, http.StatusOK)
	got := decode[book.Book](t, rec)
	if got.Year != 0 || got.ISBN != "" {
		t.Errorf("PUT kept optional fields it was not sent: %+v; PUT replaces the whole book", got)
	}
}

func TestUpdateBookIgnoresIDInBody(t *testing.T) {
	h := newHandler(t)
	first := createBook(t, h, `{"title":"First","author":"A"}`)
	second := createBook(t, h, `{"title":"Second","author":"A"}`)

	rec := send(t, h, http.MethodPut, bookPath(first), fmt.Sprintf(`{"id":%d,"title":"Renamed","author":"A"}`, second.ID))
	wantStatus(t, rec, http.StatusOK)
	if got := decode[book.Book](t, rec); got.ID != first.ID || got.Title != "Renamed" {
		t.Errorf("PUT = %+v, want book %d renamed", got, first.ID)
	}
	rec = send(t, h, http.MethodGet, bookPath(second), "")
	if got := decode[book.Book](t, rec); got != second {
		t.Errorf("the id in the body redirected the update to another book: %+v", got)
	}
}

func TestUpdateBookNotFound(t *testing.T) {
	h := newHandler(t)
	wantError(t, send(t, h, http.MethodPut, "/books/999", dune), http.StatusNotFound, "book not found")
	rec := send(t, h, http.MethodGet, "/books", "")
	if got := strings.TrimSpace(rec.Body.String()); got != "[]" {
		t.Errorf("PUT to a missing id created a book: %s", got)
	}
}

func TestUpdateBookRejectsInvalidInput(t *testing.T) {
	h := newHandler(t)
	target := createBook(t, h, dune)

	for name, body := range map[string]string{
		"missing title":  `{"author":"Frank Herbert"}`,
		"blank author":   `{"title":"Dune","author":" "}`,
		"malformed JSON": `{"title":`,
		"empty body":     ``,
	} {
		t.Run(name, func(t *testing.T) {
			wantError(t, send(t, h, http.MethodPut, bookPath(target), body), http.StatusBadRequest, "")
		})
	}
	rec := send(t, h, http.MethodGet, bookPath(target), "")
	if got := decode[book.Book](t, rec); got != target {
		t.Errorf("a rejected update changed the book: %+v, want %+v", got, target)
	}
}

func TestUpdateValidationTakesPrecedenceOverLookup(t *testing.T) {
	h := newHandler(t)
	wantError(t, send(t, h, http.MethodPut, "/books/999", `{"author":"A"}`), http.StatusBadRequest, "title")
}

func TestDeleteBook(t *testing.T) {
	h := newHandler(t)
	keep := createBook(t, h, `{"title":"Keep","author":"A"}`)
	drop := createBook(t, h, `{"title":"Drop","author":"A"}`)

	rec := send(t, h, http.MethodDelete, bookPath(drop), "")
	wantStatus(t, rec, http.StatusNoContent)
	if rec.Body.Len() != 0 {
		t.Errorf("body = %q, want empty", rec.Body)
	}

	wantError(t, send(t, h, http.MethodGet, bookPath(drop), ""), http.StatusNotFound, "book not found")
	wantError(t, send(t, h, http.MethodDelete, bookPath(drop), ""), http.StatusNotFound, "book not found")
	rec = send(t, h, http.MethodGet, "/books", "")
	if got := decode[[]book.Book](t, rec); len(got) != 1 || got[0] != keep {
		t.Errorf("list after delete = %+v, want only %+v", got, keep)
	}
}

func TestDeleteBookNotFound(t *testing.T) {
	h := newHandler(t)
	wantError(t, send(t, h, http.MethodDelete, "/books/999", ""), http.StatusNotFound, "book not found")
}
