-- ============================================================================
-- SUPABASE MIGRATION: Core Application Schema
-- Purpose: App layer tables for user management, documents, RAG, and access control
-- Database: PostgreSQL with pgvector for embeddings
-- Extensions: uuid-ossp, pgvector, pg_trgm
-- ============================================================================

-- ============================================================================
-- ENABLE EXTENSIONS
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- TABLE: users
-- Description: Platform users with tenant isolation
-- Purpose: Manage user accounts, roles, and access to the platform
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Authentication and identity
    email VARCHAR(255) NOT NULL UNIQUE,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    
    -- User profile
    full_name VARCHAR(255),
    avatar_url VARCHAR(512),
    phone_number VARCHAR(20),
    
    -- Tenant relationship
    tenant_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    -- role values: 'super_admin', 'tenant_admin', 'property_manager', 'leasing_agent', 'maintenance', 'accountant', 'user'
    
    -- Account status
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    -- metadata can contain preferences, department, location, etc.
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT role_valid CHECK (role IN ('super_admin', 'tenant_admin', 'property_manager', 'leasing_agent', 'maintenance', 'accountant', 'user'))
);

COMMENT ON TABLE users IS 'Platform users with tenant relationships and role-based access control';
COMMENT ON COLUMN users.tenant_id IS 'Foreign key to Snowflake tenant - enables multi-tenant isolation';
COMMENT ON COLUMN users.role IS 'User role determining default permissions and platform features';
COMMENT ON COLUMN users.metadata IS 'JSON blob for storing user preferences, department, tags, etc.';

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
CREATE INDEX idx_users_is_active ON users(is_active);
CREATE INDEX idx_users_tenant_role ON users(tenant_id, role);

-- ============================================================================
-- TABLE: documents
-- Description: Real estate documents stored with metadata and URLs
-- Purpose: Track all documents uploaded for RAG indexing and retrieval
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    doc_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Relationship
    tenant_id VARCHAR(255) NOT NULL,
    property_id VARCHAR(255),
    -- property_id can be NULL for tenant-level documents
    
    -- Document metadata
    doc_type VARCHAR(50) NOT NULL,
    -- doc_type values: 'Lease', 'InspectionReport', 'MaintenanceLog', 'MarketingDoc', 'ComplianceDoc', 'FinancialStatement', 'PropertyAppraisal', 'Other'
    
    doc_title VARCHAR(512) NOT NULL,
    doc_description TEXT,
    
    -- Storage details
    doc_url VARCHAR(512) NOT NULL,
    -- URL to document in cloud storage (S3, GCS, etc.)
    
    doc_text TEXT,
    -- Full extracted text from document (for search and RAG)
    
    page_count INTEGER,
    file_size_bytes BIGINT,
    file_type VARCHAR(20),
    -- file_type: 'pdf', 'docx', 'txt', 'xlsx', 'jpg', etc.
    
    -- Document relationships
    uploaded_by UUID REFERENCES users(user_id),
    
    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'pending',
    -- pending, processing, completed, failed
    
    extraction_error TEXT,
    
    -- Metadata
    tags VARCHAR(255)[],
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE documents IS 'Real estate documents (leases, reports, etc.) with full text for RAG retrieval';
COMMENT ON COLUMN documents.doc_text IS 'Extracted full text used for embedding and semantic search';
COMMENT ON COLUMN documents.doc_type IS 'Document category for filtering and access control';
COMMENT ON COLUMN documents.tags IS 'Array of searchable tags for document discovery';

CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_property ON documents(property_id);
CREATE INDEX idx_documents_type ON documents(doc_type);
CREATE INDEX idx_documents_created ON documents(created_at DESC);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);
CREATE INDEX idx_documents_text_search ON documents USING GIN(to_tsvector('english', doc_text));

-- ============================================================================
-- TABLE: document_chunks
-- Description: Chunked documents with embeddings for vector search (RAG)
-- Purpose: Store semantic chunks and embeddings for semantic similarity search
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    doc_id UUID NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    
    -- Chunk content
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    -- chunk_index is the sequence number within the document
    
    -- Vector embedding (3072 dimensions for advanced LLMs)
    embedding VECTOR(3072),
    -- NULL until processed
    
    -- Chunk metadata
    chunk_metadata JSONB DEFAULT '{}',
    -- Can store: source_page, section_title, confidence_score, chunk_tokens, etc.
    
    embedding_model VARCHAR(100),
    -- Record which embedding model was used (e.g., 'text-embedding-3-large')
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE document_chunks IS 'Chunked document segments with vector embeddings for semantic RAG search';
COMMENT ON COLUMN document_chunks.embedding IS 'Vector embedding (3072 dims) for semantic similarity search using pgvector';
COMMENT ON COLUMN document_chunks.chunk_metadata IS 'JSON with source page, section, confidence, token count, etc.';

CREATE INDEX idx_document_chunks_doc ON document_chunks(doc_id);
CREATE INDEX idx_document_chunks_embedding ON document_chunks USING HNSW(embedding vector_cosine_ops);
-- HNSW index optimized for cosine similarity on embeddings

-- ============================================================================
-- TABLE: query_history
-- Description: Track user queries for analytics, debugging, and feedback
-- Purpose: Monitor platform usage, analyze patterns, improve suggestions
-- ============================================================================

CREATE TABLE IF NOT EXISTS query_history (
    query_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User and tenant
    user_id UUID NOT NULL REFERENCES users(user_id),
    tenant_id VARCHAR(255) NOT NULL,
    
    -- Query details
    query_text TEXT NOT NULL,
    query_type VARCHAR(50),
    -- query_type: 'document_search', 'text_to_sql', 'natural_language', 'sql_direct'
    
    -- Generated SQL (for text-to-sql queries)
    generated_sql TEXT,
    sql_error TEXT,
    -- SQL error message if execution failed
    
    -- Execution metrics
    execution_time_ms INTEGER,
    result_count INTEGER,
    
    -- User feedback
    feedback_rating INTEGER,
    -- 1-5 star rating from user
    
    feedback_comment TEXT,
    -- User comment on query quality
    
    -- Query status
    status VARCHAR(20) DEFAULT 'completed',
    -- pending, executing, completed, failed
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE query_history IS 'Query execution history for analytics, debugging, and feedback collection';
COMMENT ON COLUMN query_history.query_type IS 'Type of query: document search, text-to-SQL, natural language, or direct SQL';
COMMENT ON COLUMN query_history.feedback_rating IS '1-5 star user satisfaction rating for query results';

CREATE INDEX idx_query_history_user ON query_history(user_id);
CREATE INDEX idx_query_history_tenant ON query_history(tenant_id);
CREATE INDEX idx_query_history_type ON query_history(query_type);
CREATE INDEX idx_query_history_created ON query_history(created_at DESC);
CREATE INDEX idx_query_history_status ON query_history(status);

-- ============================================================================
-- TABLE: saved_queries
-- Description: User-saved queries for quick re-execution
-- Purpose: Enable power users to save and share commonly-used queries
-- ============================================================================

CREATE TABLE IF NOT EXISTS saved_queries (
    saved_query_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User and tenant
    user_id UUID NOT NULL REFERENCES users(user_id),
    tenant_id VARCHAR(255) NOT NULL,
    
    -- Query details
    query_name VARCHAR(255) NOT NULL,
    query_description TEXT,
    
    query_text TEXT NOT NULL,
    -- Natural language query text
    
    query_type VARCHAR(50),
    -- Type of query (same as query_history)
    
    generated_sql TEXT,
    -- Cached SQL generation for text-to-sql queries
    
    -- Usage metrics
    execution_count INTEGER DEFAULT 0,
    last_executed TIMESTAMP WITH TIME ZONE,
    
    -- Sharing
    is_public BOOLEAN DEFAULT FALSE,
    shared_with_users UUID[] DEFAULT '{}',
    
    -- Categorization
    category VARCHAR(100),
    tags VARCHAR(255)[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE saved_queries IS 'User-saved queries for quick re-execution and sharing with team members';
COMMENT ON COLUMN saved_queries.query_type IS 'Type of query for consistent re-execution';
COMMENT ON COLUMN saved_queries.shared_with_users IS 'Array of user IDs with access to this saved query';

CREATE INDEX idx_saved_queries_user ON saved_queries(user_id);
CREATE INDEX idx_saved_queries_tenant ON saved_queries(tenant_id);
CREATE INDEX idx_saved_queries_is_public ON saved_queries(is_public);
CREATE INDEX idx_saved_queries_category ON saved_queries(category);

-- ============================================================================
-- TABLE: access_logs
-- Description: Audit trail of user actions and data access
-- Purpose: Security, compliance, and usage analytics
-- ============================================================================

CREATE TABLE IF NOT EXISTS access_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User and tenant
    user_id UUID NOT NULL REFERENCES users(user_id),
    tenant_id VARCHAR(255) NOT NULL,
    
    -- Action and resource
    action VARCHAR(50) NOT NULL,
    -- action: 'view', 'create', 'update', 'delete', 'download', 'export', 'share'
    
    resource VARCHAR(255),
    -- resource: 'document', 'property', 'financial', 'query', etc.
    
    resource_id VARCHAR(255),
    -- ID of the resource being accessed
    
    resource_name VARCHAR(512),
    -- Human-readable name of the resource
    
    -- Network info
    ip_address INET,
    user_agent TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'success',
    -- success, failed, denied
    
    error_message TEXT,
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE access_logs IS 'Audit trail of user actions for security and compliance';
COMMENT ON COLUMN access_logs.action IS 'Type of action: view, create, update, delete, download, export, share';
COMMENT ON COLUMN access_logs.ip_address IS 'IP address of the request for security analysis';

CREATE INDEX idx_access_logs_user ON access_logs(user_id);
CREATE INDEX idx_access_logs_tenant ON access_logs(tenant_id);
CREATE INDEX idx_access_logs_action ON access_logs(action);
CREATE INDEX idx_access_logs_resource ON access_logs(resource, resource_id);
CREATE INDEX idx_access_logs_created ON access_logs(created_at DESC);

-- ============================================================================
-- TABLE: notifications
-- Description: User notifications and alerts
-- Purpose: Alert users to important events (lease expirations, work orders, etc.)
-- ============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User and tenant
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    tenant_id VARCHAR(255) NOT NULL,
    
    -- Notification content
    type VARCHAR(50) NOT NULL,
    -- type: 'lease_expiration', 'work_order', 'payment_overdue', 'occupancy_change', 'financial_alert'
    
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    
    -- Reference to related object
    related_resource VARCHAR(100),
    related_resource_id VARCHAR(255),
    
    -- Delivery
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- Preference
    notification_method VARCHAR(50) DEFAULT 'in_app',
    -- in_app, email, sms
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP + INTERVAL '30 days'
);

COMMENT ON TABLE notifications IS 'User notifications for important events and alerts';
COMMENT ON COLUMN notifications.type IS 'Notification type for filtering and user preferences';

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);

-- ============================================================================
-- RLS (ROW LEVEL SECURITY) POLICIES
-- Purpose: Enforce tenant isolation and role-based access control
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE query_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_queries ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- RLS POLICIES: users table
-- ============================================================================

CREATE POLICY "Users can view own record"
    ON users
    FOR SELECT
    USING (
        auth.uid() = user_id
        OR auth.jwt()->'claims'->>'role' = 'super_admin'
    );

CREATE POLICY "Tenant admins can view tenant users"
    ON users
    FOR SELECT
    USING (
        tenant_id = auth.jwt()->'claims'->>'tenant_id'
        AND auth.jwt()->'claims'->>'role' IN ('super_admin', 'tenant_admin')
    );

CREATE POLICY "Users can update own record"
    ON users
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id AND role = (SELECT role FROM users WHERE user_id = auth.uid()));

-- ============================================================================
-- RLS POLICIES: documents table
-- ============================================================================

CREATE POLICY "Users can view documents in their tenant"
    ON documents
    FOR SELECT
    USING (
        tenant_id = auth.jwt()->'claims'->>'tenant_id'
        AND (auth.jwt()->'claims'->>'role' != 'viewer' OR property_id IS NOT NULL)
    );

CREATE POLICY "Property managers can view all documents in tenant"
    ON documents
    FOR SELECT
    USING (
        tenant_id = auth.jwt()->'claims'->>'tenant_id'
        AND auth.jwt()->'claims'->>'role' IN ('super_admin', 'tenant_admin', 'property_manager')
    );

CREATE POLICY "Users can insert documents in their tenant"
    ON documents
    FOR INSERT
    WITH CHECK (
        tenant_id = auth.jwt()->'claims'->>'tenant_id'
        AND auth.jwt()->'claims'->>'role' IN ('super_admin', 'tenant_admin', 'property_manager', 'leasing_agent', 'accountant')
        AND uploaded_by = auth.uid()
    );

CREATE POLICY "Document owners can update their documents"
    ON documents
    FOR UPDATE
    USING (
        uploaded_by = auth.uid()
        AND tenant_id = auth.jwt()->'claims'->>'tenant_id'
    )
    WITH CHECK (
        uploaded_by = auth.uid()
        AND tenant_id = auth.jwt()->'claims'->>'tenant_id'
    );

-- ============================================================================
-- RLS POLICIES: document_chunks table
-- ============================================================================

CREATE POLICY "Users can view chunks of their tenant documents"
    ON document_chunks
    FOR SELECT
    USING (
        doc_id IN (
            SELECT doc_id FROM documents
            WHERE tenant_id = auth.jwt()->'claims'->>'tenant_id'
        )
    );

CREATE POLICY "System can insert chunks during processing"
    ON document_chunks
    FOR INSERT
    WITH CHECK (
        doc_id IN (
            SELECT doc_id FROM documents
            WHERE tenant_id = auth.jwt()->'claims'->>'tenant_id'
        )
    );

-- ============================================================================
-- RLS POLICIES: query_history table
-- ============================================================================

CREATE POLICY "Users can view own query history"
    ON query_history
    FOR SELECT
    USING (
        user_id = auth.uid()
        OR (tenant_id = auth.jwt()->'claims'->>'tenant_id' AND auth.jwt()->'claims'->>'role' IN ('super_admin', 'tenant_admin'))
    );

CREATE POLICY "Users can insert own queries"
    ON query_history
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND tenant_id = auth.jwt()->'claims'->>'tenant_id'
    );

-- ============================================================================
-- RLS POLICIES: saved_queries table
-- ============================================================================

CREATE POLICY "Users can view own saved queries"
    ON saved_queries
    FOR SELECT
    USING (
        user_id = auth.uid()
        OR is_public AND tenant_id = auth.jwt()->'claims'->>'tenant_id'
        OR auth.uid() = ANY(shared_with_users)
    );

CREATE POLICY "Users can create saved queries"
    ON saved_queries
    FOR INSERT
    WITH CHECK (
        user_id = auth.uid()
        AND tenant_id = auth.jwt()->'claims'->>'tenant_id'
    );

CREATE POLICY "Users can update own saved queries"
    ON saved_queries
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid() AND tenant_id = auth.jwt()->'claims'->>'tenant_id');

-- ============================================================================
-- RLS POLICIES: access_logs table
-- ============================================================================

CREATE POLICY "Users can view own access logs"
    ON access_logs
    FOR SELECT
    USING (
        user_id = auth.uid()
        OR (tenant_id = auth.jwt()->'claims'->>'tenant_id' AND auth.jwt()->'claims'->>'role' IN ('super_admin', 'tenant_admin'))
    );

CREATE POLICY "System can insert access logs"
    ON access_logs
    FOR INSERT
    WITH CHECK (tenant_id = auth.jwt()->'claims'->>'tenant_id');

-- ============================================================================
-- RLS POLICIES: notifications table
-- ============================================================================

CREATE POLICY "Users can view own notifications"
    ON notifications
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "System can insert notifications"
    ON notifications
    FOR INSERT
    WITH CHECK (user_id = auth.uid() OR auth.jwt()->'claims'->>'role' = 'super_admin');

CREATE POLICY "Users can update own notifications"
    ON notifications
    FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ============================================================================
-- FUNCTION: match_documents
-- Purpose: Vector similarity search for RAG document retrieval
-- Parameters:
--   - query_embedding: VECTOR(3072) - the query embedding
--   - p_tenant_id: VARCHAR - tenant ID for filtering
--   - match_count: INT - number of results to return
--   - similarity_threshold: FLOAT - minimum similarity score (0-1)
-- Returns: document chunks with similarity scores
-- ============================================================================

CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR,
    p_tenant_id VARCHAR,
    match_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.5
)
RETURNS TABLE(
    chunk_id UUID,
    doc_id UUID,
    chunk_text TEXT,
    chunk_index INTEGER,
    doc_title VARCHAR,
    doc_type VARCHAR,
    property_id VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        dc.chunk_id,
        dc.doc_id,
        dc.chunk_text,
        dc.chunk_index,
        d.doc_title,
        d.doc_type,
        d.property_id,
        (1 - (dc.embedding <=> query_embedding))::FLOAT AS similarity
    FROM document_chunks dc
    JOIN documents d ON dc.doc_id = d.doc_id
    WHERE d.tenant_id = p_tenant_id
        AND dc.embedding IS NOT NULL
        AND (1 - (dc.embedding <=> query_embedding)) > similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION match_documents IS 'Vector similarity search for semantic RAG document retrieval using cosine distance';

-- ============================================================================
-- FUNCTION: record_access_log
-- Purpose: Automatically log user access for audit trails
-- ============================================================================

CREATE OR REPLACE FUNCTION record_access_log(
    p_user_id UUID,
    p_tenant_id VARCHAR,
    p_action VARCHAR,
    p_resource VARCHAR,
    p_resource_id VARCHAR,
    p_resource_name VARCHAR,
    p_status VARCHAR DEFAULT 'success'
)
RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO access_logs(
        user_id, tenant_id, action, resource, resource_id, resource_name, status
    )
    VALUES (p_user_id, p_tenant_id, p_action, p_resource, p_resource_id, p_resource_name, p_status)
    RETURNING log_id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION record_access_log IS 'Helper function to log user actions for audit trails';

-- ============================================================================
-- FUNCTION: update_updated_at_timestamp
-- Purpose: Automatically update the updated_at timestamp on record changes
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_updated_at_timestamp IS 'Trigger function to automatically update the updated_at timestamp';

-- ============================================================================
-- TRIGGERS
-- ============================================================================

CREATE TRIGGER trigger_update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

CREATE TRIGGER trigger_update_documents_timestamp
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

CREATE TRIGGER trigger_update_document_chunks_timestamp
    BEFORE UPDATE ON document_chunks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

CREATE TRIGGER trigger_update_saved_queries_timestamp
    BEFORE UPDATE ON saved_queries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_timestamp();

