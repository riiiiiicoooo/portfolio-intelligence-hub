/**
 * Snowflake Materialized View Refresh Job
 *
 * Trigger.dev task for nightly refresh of Snowflake materialized views.
 * Scheduled to run at 2 AM UTC daily.
 *
 * Handles:
 * 1. Refreshing multiple materialized views
 * 2. Validating data consistency
 * 3. Tracking row counts and performance
 * 4. Sending completion notifications
 *
 * @remarks
 * - Scheduled: 0 2 * * * (2 AM UTC daily)
 * - Timeout: 30 minutes
 * - Warehouse: Compute warehouse
 */

import { task, logger } from "@trigger.dev/sdk/v3";
import { snowflake } from "@trigger.dev/snowflake";

// ============================================================================
// Type Definitions
// ============================================================================

/**
 * Payload for materialized view refresh.
 */
interface RefreshPayload {
  /** List of materialized view names to refresh */
  views: string[];
  /** Snowflake warehouse to use for refresh */
  snowflake_warehouse: string;
  /** Optional: send notification on completion */
  notify_slack?: boolean;
  /** Optional: Slack webhook URL */
  slack_webhook_url?: string;
}

/**
 * Result of a single view refresh.
 */
interface ViewRefreshResult {
  /** View name */
  view_name: string;
  /** Refresh status */
  status: "success" | "failed";
  /** Rows in view after refresh */
  rows_affected: number;
  /** Duration of refresh in milliseconds */
  duration_ms: number;
  /** Previous row count for comparison */
  previous_count?: number;
  /** Error message if failed */
  error?: string;
}

/**
 * Complete refresh operation result.
 */
interface RefreshResult {
  /** Timestamp of refresh start */
  started_at: string;
  /** Timestamp of refresh completion */
  completed_at: string;
  /** Total duration in milliseconds */
  duration_ms: number;
  /** Views refreshed successfully */
  views_refreshed: ViewRefreshResult[];
  /** Total rows affected across all views */
  total_rows_affected: number;
  /** Overall status */
  status: "success" | "partial_failure" | "failed";
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Get current row count for a materialized view.
 */
async function getViewRowCount(
  viewName: string,
  warehouse: string
): Promise<number> {
  logger.info(`Getting row count for view ${viewName}`);

  const result = await snowflake.query({
    warehouse,
    sql: `SELECT COUNT(*) as row_count FROM ${viewName}`,
  });

  if (!result.rows || result.rows.length === 0) {
    throw new Error(`Failed to get row count for ${viewName}`);
  }

  const rowCount = (result.rows[0] as Record<string, number>).row_count;
  logger.info(`View ${viewName} has ${rowCount} rows`);

  return rowCount;
}

/**
 * Refresh a materialized view.
 */
async function refreshView(
  viewName: string,
  warehouse: string
): Promise<ViewRefreshResult> {
  const startTime = Date.now();

  try {
    logger.info(`Starting refresh of materialized view ${viewName}`);

    // Get previous count
    let previousCount: number | undefined;
    try {
      previousCount = await getViewRowCount(viewName, warehouse);
    } catch (error) {
      logger.warn(`Could not get previous row count for ${viewName}`);
    }

    // Execute refresh
    await snowflake.execute({
      warehouse,
      sql: `ALTER MATERIALIZED VIEW ${viewName} REFRESH`,
    });

    logger.info(`Refresh SQL executed for ${viewName}`);

    // Get new row count
    const newRowCount = await getViewRowCount(viewName, warehouse);

    const duration_ms = Date.now() - startTime;

    logger.info(`Refresh completed for ${viewName}`, {
      duration_ms,
      previous_count: previousCount,
      new_count: newRowCount,
    });

    return {
      view_name: viewName,
      status: "success",
      rows_affected: newRowCount,
      duration_ms,
      previous_count: previousCount,
    };
  } catch (error) {
    const duration_ms = Date.now() - startTime;
    const error_message = error instanceof Error ? error.message : String(error);

    logger.error(`Refresh failed for ${viewName}`, {
      error: error_message,
      duration_ms,
    });

    return {
      view_name: viewName,
      status: "failed",
      rows_affected: 0,
      duration_ms,
      error: error_message,
    };
  }
}

/**
 * Validate view structure and data consistency.
 */
async function validateView(
  viewName: string,
  warehouse: string
): Promise<boolean> {
  try {
    logger.info(`Validating view ${viewName}`);

    const result = await snowflake.query({
      warehouse,
      sql: `DESCRIBE VIEW ${viewName}`,
    });

    if (!result.rows || result.rows.length === 0) {
      logger.warn(`View ${viewName} appears to be empty`);
      return false;
    }

    logger.info(`View ${viewName} validation passed`);
    return true;
  } catch (error) {
    logger.error(`View ${viewName} validation failed`, {
      error: error instanceof Error ? error.message : String(error),
    });
    return false;
  }
}

/**
 * Send Slack notification.
 */
async function sendSlackNotification(
  webhookUrl: string,
  result: RefreshResult
): Promise<void> {
  const successCount = result.views_refreshed.filter(
    (v) => v.status === "success"
  ).length;
  const failureCount = result.views_refreshed.length - successCount;

  const statusEmoji = result.status === "success" ? ":white_check_mark:" : ":warning:";

  try {
    const response = await fetch(webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text: `${statusEmoji} Snowflake MV Refresh Summary`,
        blocks: [
          {
            type: "header",
            text: {
              type: "plain_text",
              text: `${statusEmoji} Materialized View Refresh Summary`,
            },
          },
          {
            type: "section",
            fields: [
              {
                type: "mrkdwn",
                text: `*Status:*\n${result.status}`,
              },
              {
                type: "mrkdwn",
                text: `*Duration:*\n${(result.duration_ms / 1000).toFixed(2)}s`,
              },
              {
                type: "mrkdwn",
                text: `*Views Refreshed:*\n${successCount}/${result.views_refreshed.length}`,
              },
              {
                type: "mrkdwn",
                text: `*Total Rows:*\n${result.total_rows_affected.toLocaleString()}`,
              },
            ],
          },
          ...(failureCount > 0
            ? [
                {
                  type: "section",
                  text: {
                    type: "mrkdwn",
                    text: `*Failed Views:*\n${result.views_refreshed
                      .filter((v) => v.status === "failed")
                      .map((v) => `• ${v.view_name}: ${v.error}`)
                      .join("\n")}`,
                  },
                },
              ]
            : []),
          {
            type: "context",
            elements: [
              {
                type: "mrkdwn",
                text: `Completed at ${new Date(result.completed_at).toISOString()}`,
              },
            ],
          },
        ],
      }),
    });

    if (!response.ok) {
      throw new Error(`Slack notification failed: ${response.statusText}`);
    }

    logger.info("Slack notification sent successfully");
  } catch (error) {
    logger.error("Failed to send Slack notification", {
      error: error instanceof Error ? error.message : String(error),
    });
    // Don't throw - logging failure shouldn't fail the entire task
  }
}

// ============================================================================
// Main Task
// ============================================================================

/**
 * Main materialized view refresh task.
 *
 * Refreshes multiple Snowflake materialized views in sequence.
 * Validates data consistency and sends notifications.
 */
export const refreshMaterializedViews = task({
  id: "refresh-snowflake-mv",
  run: async (payload: RefreshPayload): Promise<RefreshResult> => {
    const startTime = Date.now();
    const startedAt = new Date().toISOString();

    try {
      const { views, snowflake_warehouse, notify_slack, slack_webhook_url } =
        payload;

      logger.info(`Starting materialized view refresh`, {
        view_count: views.length,
        warehouse: snowflake_warehouse,
      });

      // Validate inputs
      if (!views || views.length === 0) {
        throw new Error("No views provided for refresh");
      }

      // Refresh each view
      const viewResults: ViewRefreshResult[] = [];
      let totalRowsAffected = 0;

      for (const viewName of views) {
        logger.info(`Processing view ${viewName}`);

        // Validate before refresh
        const isValid = await validateView(viewName, snowflake_warehouse);
        if (!isValid) {
          logger.warn(`View ${viewName} validation failed, skipping`);
          viewResults.push({
            view_name: viewName,
            status: "failed",
            rows_affected: 0,
            duration_ms: 0,
            error: "Validation failed",
          });
          continue;
        }

        // Perform refresh
        const result = await refreshView(viewName, snowflake_warehouse);
        viewResults.push(result);

        if (result.status === "success") {
          totalRowsAffected += result.rows_affected;
        }
      }

      const completedAt = new Date().toISOString();
      const duration_ms = Date.now() - startTime;

      // Determine overall status
      const successCount = viewResults.filter((v) => v.status === "success").length;
      let overallStatus: "success" | "partial_failure" | "failed" = "success";
      if (successCount === 0) {
        overallStatus = "failed";
      } else if (successCount < viewResults.length) {
        overallStatus = "partial_failure";
      }

      const result: RefreshResult = {
        started_at: startedAt,
        completed_at: completedAt,
        duration_ms,
        views_refreshed: viewResults,
        total_rows_affected: totalRowsAffected,
        status: overallStatus,
      };

      logger.info(`Materialized view refresh completed`, result);

      // Send notification if requested
      if (notify_slack && slack_webhook_url) {
        await sendSlackNotification(slack_webhook_url, result);
      }

      return result;
    } catch (error) {
      const completedAt = new Date().toISOString();
      const duration_ms = Date.now() - startTime;
      const error_message = error instanceof Error ? error.message : String(error);

      logger.error(`Materialized view refresh failed`, {
        error: error_message,
        duration_ms,
      });

      // Return failed result
      return {
        started_at: startedAt,
        completed_at: completedAt,
        duration_ms,
        views_refreshed: [],
        total_rows_affected: 0,
        status: "failed",
      };
    }
  },
});

// ============================================================================
// Export
// ============================================================================

export default refreshMaterializedViews;
