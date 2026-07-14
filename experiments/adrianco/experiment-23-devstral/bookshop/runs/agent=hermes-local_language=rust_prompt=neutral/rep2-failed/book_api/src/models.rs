use diesel::prelude::*;
use serde::{Deserialize, Serialize};
use uuid::Uuid;
use validator::Validate;

#[derive(Queryable, Serialize, Deserialize, Debug, Validate)]
pub struct Book {
    pub id: Uuid,
    pub title: String,
    pub author: String,
    pub year: Option<i32>,
    pub isbn: Option<String>,
}

#[derive(Insertable, Deserialize, Debug, Validate)]
#[table_name = "books"]
pub struct NewBook<'a> {
    pub id: Uuid,
    pub title: &'a str,
    pub author: &'a str,
    pub year: Option<i32>,
    pub isbn: Option<&'a str>,
}

impl<'a> NewBook<'a> {
    pub fn new(title: &'a str, author: &'a str, year: Option<i32>, isbn: Option<&'a str>) -> Self {
        NewBook {
            id: Uuid::new_v4(),
            title,
            author,
            year,
            isbn,
        }
    }
}

#[derive(AsChangeset, Deserialize, Debug, Validate)]
#[table_name = "books"]
pub struct UpdateBook<'a> {
    pub title: Option<&'a str>,
    pub author: Option<&'a str>,
    pub year: Option<i32>,
    pub isbn: Option<&'a str>,
}
