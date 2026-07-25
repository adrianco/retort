pub mod db;
pub mod models;
pub mod routes;
pub mod server;

pub use crate::models::{Book, CreateBookRequest, UpdateBookRequest};
pub use crate::routes::{configure_routes, get_books, get_book, create_book, update_book, delete_book};
pub use crate::db::{AppState, init_db};
pub use crate::server::{AppError, HealthResponse, health, start_server};
