// ============================================================================
// CONTEXT: BDD test support - shared fixture
//
// Purpose:  Loads the full Dataset from data/kaggle exactly once per test
//           binary (OnceLock) so every Given/When/Then scenario runs against
//           the real CSV files shipped in the repository.
// ============================================================================

use brazilian_soccer_mcp::data::Dataset;
use std::path::PathBuf;
use std::sync::OnceLock;

static DATASET: OnceLock<Dataset> = OnceLock::new();

/// GIVEN: the match and player data is loaded from data/kaggle.
pub fn given_loaded_dataset() -> &'static Dataset {
    DATASET.get_or_init(|| {
        let dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/kaggle");
        Dataset::load(&dir).expect("all six CSV files should load")
    })
}
