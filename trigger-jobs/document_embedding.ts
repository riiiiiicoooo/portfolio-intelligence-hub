/**
 * Document Embedding Job
 *
 * Trigger.dev task that handles batch embedding of document chunks.
 * Processes documents by:
 * 1. Fetching document chunks from storage
 * 2. Batch embedding via OpenAI API with rate limiting
 * 3. Storing embeddings in Supabase pgvector
 * 4. Updating document processing status
 * 5. Tracking costs and token usage
 *
 * @remarks
 * - Max retries: 3 with exponential backoff
 * - Batch size: 100 chunks per API call
 * - Rate limit: 3 requests per minute
 * - Timeout: 5 minutes per document
 */

import { task, logger } from "@trigger.dev/sdk/v3";
import { OpenAI } from "openai";
import { createClient } from "@supabase/supabase-js";

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Payload for document embedding task.
 */
interface DocumentEmbeddingPayload {
  /** Document ID from database */
  doc_id: string;
  /** Tenant ID for isolation */
  tenant_id: string;
  /** Property ID for context */
  property_id: string;
  /** Document chunks to embed */
  chunks: string[];
  /** Optional metadata */
  metadata?: Record<string, string>;
}

/**
 * Result of embedding operation.
 */
interface EmbeddingResult {
  /** Document ID */
  doc_id: string;
  /** Number of chunks successfully embedded */
  chunks_embedded: number;
  /** Total tokens used for this document */
  total_tokens: number;
  /** Duration of embedding in milliseconds */
  duration_ms: number;
  /** Cost in USD (approximate) */
  cost_usd: number;
  /** Timestamp of completion */
  completed_at: string;
}

/**
 * Single chunk with embedding.
 */
interface EmbeddedChunk {
  /** Chunk text */
  text: string;
  /** Position in document */
  position: number;
  /** Embedding vector (1536 dimensions for OpenAI text-embedding-3-small) */
  embedding: number[];
  /** Tokens used for this chunk */
  tokens: number;
}

// ============================================================================
// Configuration
// ============================================================================

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY;
const BATCH_SIZE = 100;
const RATE_LIMIT_DELAY_MS = 20000; // 3 requests per minute = 1 request per 20 seconds
const MAX_RETRIES = 3;

// Initialize clients
const openai = new OpenAI({
  apiKey: OPENAI_API_KEY,
});

const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_KEY);

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Sleep for specified milliseconds.
 */
async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Batch array into chunks of specified size.
 */
function batchArray<T>(array: T[], batchSize: number): T[][] {
  const batches: T[][] = [];
  for (let i = 0; i < array.length; i += batchSize) {
    batches.push(array.slice(i, i + batchSize));
  }
  return batches;
}

/**
 * Retry function with exponential backoff.
 */
async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = MAX_RETRIES
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      if (attempt < maxRetries) {
        const backoffMs = Math.pow(2, attempt) * 1000; // 1s, 2s, 4s
        logger.warn(
          `Attempt ${attempt + 1} failed. Retrying in ${backoffMs}ms...`,
          {
            error: lastError.message,
          }
        );
        await sleep(backoffMs);
      }
    }
  }

  throw lastError;
}

/**
 * Embed text chunks using OpenAI API.
 */
async function embedChunks(texts: string[]): Promise<number[][]> {
  logger.info(`Embedding ${texts.length} chunks via OpenAI API`);

  const response = await openai.embeddings.create({
    model: "text-embedding-3-small",
    input: texts,
    encoding_format: "float",
  });

  // Extract embeddings and sort by index to maintain order
  const embeddings = response.data
    .sort((a, b) => a.index - b.index)
    .map((item) => item.embedding as number[]);

  logger.info(`Successfully embedded ${embeddings.length} chunks`, {
    prompt_tokens: response.usage.prompt_tokens,
    total_tokens: response.usage.total_tokens,
  });

  return embeddings;
}

/**
 * Store embeddings in Supabase pgvector.
 */
async function storeEmbeddings(
  doc_id: string,
  tenant_id: string,
  embedded_chunks: EmbeddedChunk[]
): Promise<void> {
  logger.info(`Storing ${embedded_chunks.length} embeddings in Supabase`);

  // Prepare records for batch insert
  const records = embedded_chunks.map((chunk) => ({
    doc_id,
    tenant_id,
    chunk_text: chunk.text,
    chunk_position: chunk.position,
    embedding: chunk.embedding, // pgvector format
    tokens_used: chunk.tokens,
    created_at: new Date().toISOString(),
  }));

  // Insert in batches to avoid payload size limits
  const batches = batchArray(records, 100);

  for (const batch of batches) {
    await retryWithBackoff(async () => {
      const { error } = await supabase
        .from("document_embeddings")
        .insert(batch);

      if (error) {
        throw new Error(`Failed to insert embeddings: ${error.message}`);
      }

      logger.debug(`Inserted ${batch.length} embeddings`);
    });
  }

  logger.info("All embeddings stored successfully");
}

/**
 * Update document processing status.
 */
async function updateDocumentStatus(
  doc_id: string,
  status: "processing" | "completed" | "failed",
  error?: string
): Promise<void> {
  const update: Record<string, any> = {
    processing_status: status,
    updated_at: new Date().toISOString(),
  };

  if (error) {
    update.processing_error = error;
  }

  if (status === "completed") {
    update.embedding_completed_at = new Date().toISOString();
  }

  await retryWithBackoff(async () => {
    const { error: updateError } = await supabase
      .from("documents")
      .update(update)
      .eq("doc_id", doc_id);

    if (updateError) {
      throw new Error(`Failed to update document: ${updateError.message}`);
    }
  });

  logger.info(`Document ${doc_id} status updated to ${status}`);
}

/**
 * Log cost and usage metrics.
 */
async function logCostMetrics(
  doc_id: string,
  tenant_id: string,
  total_tokens: number,
  duration_ms: number
): Promise<void> {
  // OpenAI text-embedding-3-small: $0.02 per 1M tokens
  const cost_usd = (total_tokens / 1000000) * 0.02;

  logger.info(`Cost metrics for ${doc_id}:`, {
    tokens: total_tokens,
    cost_usd: cost_usd.toFixed(6),
    duration_ms,
  });

  // Store in analytics table for billing
  await retryWithBackoff(async () => {
    const { error } = await supabase.from("embedding_costs").insert({
      doc_id,
      tenant_id,
      tokens_used: total_tokens,
      cost_usd,
      duration_ms,
      created_at: new Date().toISOString(),
    });

    if (error) {
      // Log but don't fail if metrics logging fails
      logger.warn("Failed to log cost metrics", { error: error.message });
    }
  });
}

// ============================================================================
// Main Task
// ============================================================================

/**
 * Main document embedding task.
 *
 * Processes document chunks by embedding and storing in vector database.
 * Handles batch processing, rate limiting, and error recovery.
 */
export const embedDocumentChunks = task({
  id: "embed-document-chunks",
  run: async (payload: DocumentEmbeddingPayload): Promise<EmbeddingResult> => {
    const startTime = Date.now();
    let total_tokens = 0;
    let chunks_embedded = 0;

    try {
      const { doc_id, tenant_id, property_id, chunks, metadata } = payload;

      logger.info(`Starting embedding for document ${doc_id}`, {
        chunk_count: chunks.length,
        property_id,
        tenant_id,
      });

      // Update status to processing
      await updateDocumentStatus(doc_id, "processing");

      // Validate chunks
      if (!chunks || chunks.length === 0) {
        throw new Error("No chunks provided for embedding");
      }

      if (chunks.some((chunk) => !chunk || chunk.trim().length === 0)) {
        throw new Error("Found empty chunks");
      }

      // Create batches
      const batches = batchArray(chunks, BATCH_SIZE);
      logger.info(`Processing ${batches.length} batches of up to ${BATCH_SIZE} chunks`);

      const allEmbeddedChunks: EmbeddedChunk[] = [];

      // Process batches with rate limiting
      for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
        const batch = batches[batchIndex];

        logger.info(`Processing batch ${batchIndex + 1}/${batches.length}`);

        // Embed batch
        const embeddings = await retryWithBackoff(
          () => embedChunks(batch),
          3
        );

        // Estimate tokens (rough: 1 token per 4 characters)
        const batchTokens = batch.reduce(
          (sum, chunk) => sum + Math.ceil(chunk.length / 4),
          0
        );
        total_tokens += batchTokens;

        // Create embedded chunk objects
        const chunkStartIndex = batchIndex * BATCH_SIZE;
        for (let i = 0; i < batch.length; i++) {
          allEmbeddedChunks.push({
            text: batch[i],
            position: chunkStartIndex + i,
            embedding: embeddings[i],
            tokens: Math.ceil(batch[i].length / 4),
          });
        }

        chunks_embedded += batch.length;

        // Rate limiting between batches
        if (batchIndex < batches.length - 1) {
          logger.debug(
            `Rate limiting: waiting ${RATE_LIMIT_DELAY_MS}ms before next batch`
          );
          await sleep(RATE_LIMIT_DELAY_MS);
        }
      }

      // Store all embeddings
      await storeEmbeddings(doc_id, tenant_id, allEmbeddedChunks);

      // Update document status to completed
      await updateDocumentStatus(doc_id, "completed");

      // Log metrics
      const duration_ms = Date.now() - startTime;
      await logCostMetrics(doc_id, tenant_id, total_tokens, duration_ms);

      const result: EmbeddingResult = {
        doc_id,
        chunks_embedded,
        total_tokens,
        duration_ms,
        cost_usd: (total_tokens / 1000000) * 0.02,
        completed_at: new Date().toISOString(),
      };

      logger.info(`Embedding completed successfully for ${doc_id}`, result);

      return result;
    } catch (error) {
      const duration_ms = Date.now() - startTime;
      const error_message = error instanceof Error ? error.message : String(error);

      logger.error(`Embedding failed for ${payload.doc_id}`, {
        error: error_message,
        duration_ms,
        chunks_processed: chunks_embedded,
      });

      // Update document status to failed
      await updateDocumentStatus(payload.doc_id, "failed", error_message).catch(
        (updateError) => {
          logger.error("Failed to update document status", {
            error: updateError.message,
          });
        }
      );

      throw error;
    }
  },
});

// ============================================================================
// Export
// ============================================================================

export default embedDocumentChunks;
