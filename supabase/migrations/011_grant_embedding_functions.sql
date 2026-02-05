-- ============================================
-- Migration: Grant Embedding Functions to Authenticated Users
-- Date: 2026-02-05
-- Description: Enable authenticated users to generate embeddings from iOS app
-- ============================================

-- ============================================
-- 1. GRANT EXECUTE PERMISSIONS FOR EMBEDDING FUNCTIONS
-- ============================================

-- Allow authenticated users to fetch pending embeddings
GRANT EXECUTE ON FUNCTION get_pending_embeddings(INT) TO authenticated;

-- Allow authenticated users to update embedding status
GRANT EXECUTE ON FUNCTION update_embedding_status(UUID, VECTOR(1536), TEXT) TO authenticated;

-- ============================================
-- 2. ADD COMMENTS
-- ============================================

COMMENT ON FUNCTION get_pending_embeddings(INT) IS
'Atomically fetches and locks pending embeddings for processing. Accessible by authenticated users for iOS app embedding generation.';

COMMENT ON FUNCTION update_embedding_status(UUID, VECTOR(1536), TEXT) IS
'Updates embedding and status for a claim. Accessible by authenticated users for iOS app embedding generation.';

-- ============================================
-- Migration Complete
-- ============================================
