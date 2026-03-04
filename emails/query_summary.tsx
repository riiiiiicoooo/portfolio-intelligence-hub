/**
 * Query Summary Email Template
 *
 * React Email template for sending query results via email.
 * Professional layout with branding, query details, and results preview.
 *
 * @remarks
 * - Uses React Email for cross-client compatibility
 * - Inline styles for consistent rendering
 * - Responsive design for mobile and desktop
 * - Includes CTA for viewing full results
 */

import React from "react";
import {
  Body,
  Container,
  Head,
  Hr,
  Html,
  Img,
  Link,
  Preview,
  Row,
  Section,
  Text,
  Column,
  Heading,
  Button,
  Font,
} from "react-email";

// ============================================================================
// Types
// ============================================================================

interface QuerySummaryProps {
  /** User's first name */
  userName: string;
  /** Original query text */
  queryText: string;
  /** Query type: sql, semantic, hybrid */
  queryType: "sql" | "semantic" | "hybrid";
  /** Number of results returned */
  resultCount: number;
  /** Query execution time in milliseconds */
  executionTime: number;
  /** Top 3-5 result items */
  topResults: Array<{
    id: string;
    title: string;
    description: string;
    highlight?: string;
  }>;
  /** URL to view full results */
  queryUrl: string;
  /** Timestamp of query execution */
  timestamp: Date;
}

// ============================================================================
// Styles
// ============================================================================

const styles = {
  main: {
    backgroundColor: "#f9fafb",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Ubuntu, sans-serif',
  },
  container: {
    backgroundColor: "#ffffff",
    margin: "0 auto",
    padding: "20px 0",
    marginBottom: "64px",
  },
  header: {
    backgroundColor: "#0f172a",
    padding: "24px 0",
    textAlign: "center" as const,
  },
  headerText: {
    color: "#ffffff",
    fontSize: "24px",
    fontWeight: "bold",
    marginBottom: "8px",
  },
  headerSubtext: {
    color: "#cbd5e1",
    fontSize: "14px",
    marginTop: "0",
  },
  box: {
    padding: "24px",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    marginBottom: "16px",
    backgroundColor: "#f8fafc",
  },
  boxTitle: {
    fontSize: "16px",
    fontWeight: "600",
    color: "#1e293b",
    marginTop: "0",
    marginBottom: "12px",
  },
  boxContent: {
    fontSize: "14px",
    color: "#475569",
    lineHeight: "1.5",
    marginTop: "0",
  },
  section: {
    padding: "32px 40px",
  },
  sectionTitle: {
    fontSize: "20px",
    fontWeight: "600",
    color: "#0f172a",
    marginBottom: "20px",
    marginTop: "0",
  },
  queryBox: {
    backgroundColor: "#f1f5f9",
    border: "1px solid #cbd5e1",
    borderRadius: "6px",
    padding: "16px",
    marginBottom: "24px",
  },
  queryText: {
    fontSize: "14px",
    color: "#1e293b",
    fontStyle: "italic",
    margin: "0",
    lineHeight: "1.6",
  },
  metricsContainer: {
    display: "flex",
    gap: "16px",
    marginBottom: "24px",
    flexWrap: "wrap" as const,
  },
  metricBox: {
    flex: "1",
    minWidth: "150px",
    backgroundColor: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: "6px",
    padding: "12px",
    textAlign: "center" as const,
  },
  metricLabel: {
    fontSize: "12px",
    color: "#64748b",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: "4px",
  },
  metricValue: {
    fontSize: "24px",
    fontWeight: "bold",
    color: "#0f172a",
    margin: "0",
  },
  resultsList: {
    marginTop: "20px",
  },
  resultItem: {
    backgroundColor: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "6px",
    padding: "16px",
    marginBottom: "12px",
  },
  resultTitle: {
    fontSize: "15px",
    fontWeight: "600",
    color: "#0f172a",
    marginTop: "0",
    marginBottom: "8px",
  },
  resultDescription: {
    fontSize: "14px",
    color: "#475569",
    margin: "0 0 8px 0",
    lineHeight: "1.5",
  },
  resultHighlight: {
    fontSize: "13px",
    color: "#0ea5e9",
    margin: "0",
    fontStyle: "italic",
  },
  ctaButton: {
    backgroundColor: "#3b82f6",
    borderRadius: "6px",
    color: "#ffffff",
    fontSize: "15px",
    fontWeight: "600",
    padding: "12px 24px",
    textDecoration: "none",
    textAlign: "center" as const,
    display: "inline-block",
    marginTop: "20px",
  },
  ctaButtonHover: {
    backgroundColor: "#2563eb",
  },
  footer: {
    backgroundColor: "#f8fafc",
    borderTop: "1px solid #e2e8f0",
    padding: "24px 40px",
    textAlign: "center" as const,
  },
  footerText: {
    fontSize: "12px",
    color: "#64748b",
    margin: "0 0 8px 0",
  },
  footerLink: {
    color: "#3b82f6",
    textDecoration: "none",
  },
};

// ============================================================================
// Component
// ============================================================================

export const QuerySummaryEmail: React.FC<QuerySummaryProps> = ({
  userName,
  queryText,
  queryType,
  resultCount,
  executionTime,
  topResults,
  queryUrl,
  timestamp,
}) => {
  const formattedTime = new Date(timestamp).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });

  const executionTimeMs = executionTime;

  return (
    <Html>
      <Head>
        <Font
          fontFamily="Segoe UI"
          fallbackFontFamily="Verdana"
          webFont={{
            url: "https://fonts.gstatic.com/s/segoeui/v0e/a5d_bv2Z37Os2PrEiZiQkFZ-ZQso.woff2",
            format: "woff2",
          }}
        />
      </Head>
      <Preview>
        {`Your query returned ${resultCount} result${resultCount !== 1 ? "s" : ""} - Portfolio Intelligence Hub`}
      </Preview>
      <Body style={styles.main}>
        <Container style={styles.container}>
          {/* Header */}
          <Section style={styles.header}>
            <Text style={styles.headerText}>Portfolio Intelligence Hub</Text>
            <Text style={styles.headerSubtext}>
              Query Results Summary
            </Text>
          </Section>

          {/* Greeting */}
          <Section style={styles.section}>
            <Text style={{ fontSize: "16px", color: "#1e293b", marginTop: "0" }}>
              Hi {userName},
            </Text>
            <Text style={{ fontSize: "14px", color: "#475569", marginBottom: "0" }}>
              Your query has been executed successfully. Here's a summary of
              the results.
            </Text>
          </Section>

          {/* Query Box */}
          <Section style={styles.section}>
            <Heading as="h2" style={styles.sectionTitle}>
              Your Query
            </Heading>
            <div style={styles.queryBox}>
              <Text style={styles.queryText}>"{queryText}"</Text>
            </div>
          </Section>

          {/* Metrics */}
          <Section style={styles.section}>
            <Heading as="h2" style={styles.sectionTitle}>
              Query Metrics
            </Heading>
            <Row style={{ display: "flex", gap: "16px", marginBottom: "24px" }}>
              <Column style={styles.metricBox}>
                <div style={styles.metricLabel}>Results Found</div>
                <div style={styles.metricValue}>{resultCount}</div>
              </Column>
              <Column style={styles.metricBox}>
                <div style={styles.metricLabel}>Execution Time</div>
                <div style={styles.metricValue}>{executionTimeMs}ms</div>
              </Column>
              <Column style={styles.metricBox}>
                <div style={styles.metricLabel}>Query Type</div>
                <div style={styles.metricValue} style={{ fontSize: "16px" }}>
                  {queryType}
                </div>
              </Column>
            </Row>
          </Section>

          {/* Results Preview */}
          {topResults.length > 0 && (
            <Section style={styles.section}>
              <Heading as="h2" style={styles.sectionTitle}>
                Top Results
              </Heading>
              <div style={styles.resultsList}>
                {topResults.slice(0, 5).map((result, index) => (
                  <div key={result.id} style={styles.resultItem}>
                    <p style={styles.resultTitle}>
                      {index + 1}. {result.title}
                    </p>
                    <p style={styles.resultDescription}>
                      {result.description}
                    </p>
                    {result.highlight && (
                      <p style={styles.resultHighlight}>
                        {'"'}
                        {result.highlight}
                        {'"'}
                      </p>
                    )}
                  </div>
                ))}
              </div>
              {resultCount > 5 && (
                <Text style={{ fontSize: "13px", color: "#64748b", marginTop: "12px" }}>
                  ... and {resultCount - 5} more result{resultCount - 5 !== 1 ? "s" : ""}
                </Text>
              )}
            </Section>
          )}

          {/* CTA */}
          <Section style={styles.section}>
            <div style={{ textAlign: "center" as const }}>
              <Link href={queryUrl} style={styles.ctaButton}>
                View Full Results
              </Link>
            </div>
          </Section>

          <Hr style={{ margin: "0" }} />

          {/* Footer */}
          <Section style={styles.footer}>
            <Text style={styles.footerText}>
              Query executed on {formattedTime}
            </Text>
            <Text style={styles.footerText}>
              Need help?{" "}
              <Link href="https://support.portfoliointelligence.hub" style={styles.footerLink}>
                Contact Support
              </Link>
            </Text>
            <Text style={styles.footerText}>
              <Link
                href="https://app.portfoliointelligence.hub/settings/notifications"
                style={styles.footerLink}
              >
                Manage Email Preferences
              </Link>
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
};

export default QuerySummaryEmail;
