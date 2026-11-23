use axum::{
    extract::{
        rejection::{JsonRejection, QueryRejection},
        Path, Query, State,
    },
    http::{header, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Json, Router,
};
use rusqlite::{params, Connection, OptionalExtension, Row};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::sync::{Arc, Mutex};

#[derive(Clone)]
struct Db(Arc<Mutex<Connection>>);
struct Error(StatusCode, String);
type Result<T> = std::result::Result<T, Error>;

impl IntoResponse for Error {
    fn into_response(self) -> Response {
        (self.0, Json(json!({"error":self.1}))).into_response()
    }
}
impl Error {
    fn internal(e: impl std::fmt::Display) -> Self {
        eprintln!("Database error: {e}");
        Self(
            StatusCode::INTERNAL_SERVER_ERROR,
            "Database unavailable".into(),
        )
    }
    fn missing() -> Self {
        Self(StatusCode::NOT_FOUND, "Book not found".into())
    }
}
impl From<rusqlite::Error> for Error {
    fn from(e: rusqlite::Error) -> Self {
        Self::internal(e)
    }
}
impl Db {
    async fn run<T: Send + 'static>(
        &self,
        f: impl FnOnce(&Connection) -> Result<T> + Send + 'static,
    ) -> Result<T> {
        let db = self.clone();
        tokio::task::spawn_blocking(move || {
            let conn = db.0.lock().map_err(Error::internal)?;
            f(&conn)
        })
        .await
        .map_err(Error::internal)?
    }
}

#[derive(Serialize, Deserialize)]
struct Fields {
    title: String,
    author: String,
    year: Option<i32>,
    isbn: Option<String>,
}
#[derive(Serialize)]
struct Book {
    id: i64,
    #[serde(flatten)]
    fields: Fields,
}
fn row(r: &Row) -> rusqlite::Result<Book> {
    Ok(Book {
        id: r.get(0)?,
        fields: Fields {
            title: r.get(1)?,
            author: r.get(2)?,
            year: r.get(3)?,
            isbn: r.get(4)?,
        },
    })
}
type Body = std::result::Result<Json<Fields>, JsonRejection>;
fn validate(body: Body) -> Result<Fields> {
    let Json(mut f) = body.map_err(|e| Error(e.status(), e.body_text()))?;
    f.title = f.title.trim().into();
    f.author = f.author.trim().into();
    if f.title.is_empty() || f.author.is_empty() {
        return Err(Error(
            StatusCode::UNPROCESSABLE_ENTITY,
            "Title and author are required".into(),
        ));
    }
    Ok(f)
}
fn id(raw: String) -> Result<i64> {
    raw.parse().map_err(|_| {
        Error(
            StatusCode::BAD_REQUEST,
            "Expected an integer book ID".into(),
        )
    })
}
async fn create(State(db): State<Db>, body: Body) -> Result<impl IntoResponse> {
    let f = validate(body)?;
    let book = db
        .run(move |c| {
            c.execute(
                "INSERT INTO books(title,author,year,isbn) VALUES(?,?,?,?)",
                params![f.title, f.author, f.year, f.isbn],
            )?;
            Ok(Book {
                id: c.last_insert_rowid(),
                fields: f,
            })
        })
        .await?;
    Ok((
        StatusCode::CREATED,
        [(header::LOCATION, format!("/books/{}", book.id))],
        Json(book),
    ))
}
#[derive(Deserialize)]
struct Filter {
    author: Option<String>,
}
async fn list(
    State(db): State<Db>,
    filter: std::result::Result<Query<Filter>, QueryRejection>,
) -> Result<Json<Vec<Book>>> {
    let Query(filter) = filter.map_err(|e| Error(e.status(), e.body_text()))?;
    db.run(move |c| {
        let mut s = c.prepare(
            "SELECT id,title,author,year,isbn FROM books WHERE ?1 IS NULL OR author=?1 ORDER BY id",
        )?;
        let books = s
            .query_map([filter.author], row)?
            .collect::<rusqlite::Result<Vec<_>>>()?;
        Ok(Json(books))
    })
    .await
}
async fn fetch(State(db): State<Db>, Path(raw): Path<String>) -> Result<Json<Book>> {
    let id = id(raw)?;
    db.run(move |c| {
        c.query_row(
            "SELECT id,title,author,year,isbn FROM books WHERE id=?",
            [id],
            row,
        )
        .optional()?
        .map(Json)
        .ok_or_else(Error::missing)
    })
    .await
}
async fn update(State(db): State<Db>, Path(raw): Path<String>, body: Body) -> Result<Json<Book>> {
    let id = id(raw)?;
    let f = validate(body)?;
    db.run(move |c| {
        if c.execute(
            "UPDATE books SET title=?,author=?,year=?,isbn=? WHERE id=?",
            params![f.title, f.author, f.year, f.isbn, id],
        )? == 0
        {
            return Err(Error::missing());
        }
        Ok(Json(Book { id, fields: f }))
    })
    .await
}
async fn remove(State(db): State<Db>, Path(raw): Path<String>) -> Result<StatusCode> {
    let id = id(raw)?;
    db.run(move |c| {
        if c.execute("DELETE FROM books WHERE id=?", [id])? == 0 {
            return Err(Error::missing());
        }
        Ok(StatusCode::NO_CONTENT)
    })
    .await
}
fn app(c: Connection) -> rusqlite::Result<Router> {
    c.execute_batch("CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,author TEXT NOT NULL,year INTEGER,isbn TEXT)")?;
    Ok(Router::new()
        .route("/health", get(|| async { Json(json!({"status":"ok"})) }))
        .route("/books", get(list).post(create))
        .route("/books/{id}", get(fetch).put(update).delete(remove))
        .fallback(|| async { Error(StatusCode::NOT_FOUND, "Route not found".into()) })
        .method_not_allowed_fallback(|| async {
            Error(StatusCode::METHOD_NOT_ALLOWED, "Method not allowed".into())
        })
        .with_state(Db(Arc::new(Mutex::new(c)))))
}
#[tokio::main]
async fn main() -> std::result::Result<(), Box<dyn std::error::Error>> {
    let router = app(Connection::open(
        std::env::var("BOOKS_DB").unwrap_or_else(|_| "books.sqlite".into()),
    )?)?;
    let listener = tokio::net::TcpListener::bind(
        std::env::var("BOOKS_ADDR").unwrap_or_else(|_| "127.0.0.1:3000".into()),
    )
    .await?;
    println!("Listening on http://{}", listener.local_addr()?);
    axum::serve(listener, router).await?;
    Ok(())
}
#[cfg(test)]
mod tests;
