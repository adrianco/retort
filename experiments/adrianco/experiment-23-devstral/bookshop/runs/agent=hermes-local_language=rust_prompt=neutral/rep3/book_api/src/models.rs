use serde::{Deserialize, Serialize};
use diesel::{Queryable, Insertable, AsChangeset, Identifiable};
use uuid::Uuid;

#[derive(Queryable, Serialize, Deserialize, Insertable, AsChangeset, Identifiable)]
#[diesel(table_name = "books")]
pub struct Book {
    pub id: Uuid,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}
