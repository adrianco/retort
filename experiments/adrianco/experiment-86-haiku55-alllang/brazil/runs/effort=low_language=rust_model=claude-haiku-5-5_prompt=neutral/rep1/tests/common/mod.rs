//! Shared fixture: the real Kaggle dataset, loaded once per test binary.

use std::path::PathBuf;
use std::sync::OnceLock;

use brazilian_soccer_mcp::data::Dataset;

pub fn dataset() -> &'static Dataset {
    static DATASET: OnceLock<Dataset> = OnceLock::new();
    DATASET.get_or_init(|| {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Dataset::load(&dir).expect("data/kaggle must load")
    })
}
