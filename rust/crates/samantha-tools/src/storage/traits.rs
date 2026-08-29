//! MemoryBackend trait for all storage backends.

use samantha_core::{SamanthaError, RetrievalResult};
use serde_json::Value;

pub trait MemoryBackend: Send + Sync {
    fn backend_id(&self) -> &str;
    fn store(
        &self,
        content: &str,
        source: &str,
        metadata: Option<&Value>,
    ) -> Result<String, SamanthaError>;
    fn retrieve(
        &self,
        query: &str,
        top_k: usize,
    ) -> Result<Vec<RetrievalResult>, SamanthaError>;
    fn delete(&self, doc_id: &str) -> Result<bool, SamanthaError>;
    fn clear(&self) -> Result<(), SamanthaError>;
    fn count(&self) -> Result<usize, SamanthaError>;
}
