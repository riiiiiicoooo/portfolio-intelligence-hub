/**
 * Report Ready Email Template
 *
 * React Email template for notifying users when generated reports are ready for download.
 * Professional layout with download CTA and expiration information.
 *
 * @remarks
 * - Uses React Email for cross-client compatibility
 * - Inline styles for consistent rendering
 * - Responsive design for mobile and desktop
 * - Prominent download button with expiration notice
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

interface ReportReadyProps {
  /** User's first name */
  userName: string;
  /** Report name/title */
  reportName: string;
  /** Report format: excel, pdf, csv */
  format: "excel" | "pdf" | "csv";
  /** File size in bytes */
  fileSize: number;
  /** Download URL (pre-signed S3/GCS URL) */
  downloadUrl: string;
  /** Report expiration timestamp */
  expiresAt: Date;
  /** Original query text */
  queryText: string;
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
    backgroundColor: "#10b981",
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
    color: "#d1fae5",
    fontSize: "14px",
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
  detailsBox: {
    backgroundColor: "#f0fdf4",
    border: "1px solid #86efac",
    borderRadius: "8px",
    padding: "20px",
    marginBottom: "24px",
  },
  detailsGrid: {
    display: "flex",
    gap: "24px",
    marginBottom: "0",
    flexWrap: "wrap" as const,
  },
  detailItem: {
    flex: "1",
    minWidth: "200px",
  },
  detailLabel: {
    fontSize: "12px",
    color: "#047857",
    textTransform: "uppercase" as const,
    letterSpacing: "0.5px",
    marginBottom: "6px",
    fontWeight: "600",
  },
  detailValue: {
    fontSize: "15px",
    color: "#0f172a",
    margin: "0",
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
  ctaSection: {
    backgroundColor: "#ecf9ff",
    border: "1px solid #0ea5e9",
    borderRadius: "8px",
    padding: "32px 24px",
    textAlign: "center" as const,
    marginBottom: "24px",
  },
  ctaText: {
    fontSize: "14px",
    color: "#0c4a6e",
    marginBottom: "20px",
    margin: "0 0 20px 0",
  },
  ctaButton: {
    backgroundColor: "#10b981",
    borderRadius: "6px",
    color: "#ffffff",
    fontSize: "16px",
    fontWeight: "600",
    padding: "14px 32px",
    textDecoration: "none",
    textAlign: "center" as const,
    display: "inline-block",
    margin: "0 auto",
  },
  expirationWarning: {
    backgroundColor: "#fef3c7",
    border: "1px solid #fcd34d",
    borderRadius: "6px",
    padding: "12px 16px",
    marginBottom: "24px",
  },
  warningText: {
    fontSize: "13px",
    color: "#92400e",
    margin: "0",
    lineHeight: "1.5",
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
    color: "#10b981",
    textDecoration: "none",
  },
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Format bytes to human-readable file size.
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * Get format display name.
 */
function getFormatName(format: string): string {
  const names: Record<string, string> = {
    excel: "Excel Workbook (.xlsx)",
    pdf: "PDF Report",
    csv: "CSV Data",
  };
  return names[format] || format;
}

/**
 * Get format icon emoji.
 */
function getFormatIcon(format: string): string {
  const icons: Record<string, string> = {
    excel: "📊",
    pdf: "📄",
    csv: "📋",
  };
  return icons[format] || "📦";
}

// ============================================================================
// Component
// ============================================================================

export const ReportReadyEmail: React.FC<ReportReadyProps> = ({
  userName,
  reportName,
  format,
  fileSize,
  downloadUrl,
  expiresAt,
  queryText,
}) => {
  const expirationTime = new Date(expiresAt).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });

  const hoursUntilExpiration = Math.round(
    (new Date(expiresAt).getTime() - new Date().getTime()) / (1000 * 60 * 60)
  );

  const fileSizeFormatted = formatFileSize(fileSize);
  const formatName = getFormatName(format);
  const formatIcon = getFormatIcon(format);

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
        {`Your report "${reportName}" is ready for download - Portfolio Intelligence Hub`}
      </Preview>
      <Body style={styles.main}>
        <Container style={styles.container}>
          {/* Header */}
          <Section style={styles.header}>
            <Text style={styles.headerText}>Report Ready</Text>
            <Text style={styles.headerSubtext}>
              Your report has been generated successfully
            </Text>
          </Section>

          {/* Greeting */}
          <Section style={styles.section}>
            <Text style={{ fontSize: "16px", color: "#1e293b", marginTop: "0" }}>
              Hi {userName},
            </Text>
            <Text style={{ fontSize: "14px", color: "#475569", marginBottom: "0" }}>
              Your generated report is now ready for download. The file will be
              available for {hoursUntilExpiration} hours.
            </Text>
          </Section>

          {/* Report Details */}
          <Section style={styles.section}>
            <div style={styles.detailsBox}>
              <Row style={styles.detailsGrid}>
                <Column style={styles.detailItem}>
                  <div style={styles.detailLabel}>Report Name</div>
                  <Text style={styles.detailValue}>{reportName}</Text>
                </Column>
                <Column style={styles.detailItem}>
                  <div style={styles.detailLabel}>Format</div>
                  <Text style={styles.detailValue}>
                    {formatIcon} {formatName}
                  </Text>
                </Column>
                <Column style={styles.detailItem}>
                  <div style={styles.detailLabel}>File Size</div>
                  <Text style={styles.detailValue}>{fileSizeFormatted}</Text>
                </Column>
              </Row>
            </div>
          </Section>

          {/* Query Information */}
          <Section style={styles.section}>
            <Heading as="h2" style={styles.sectionTitle}>
              Generated From
            </Heading>
            <div style={styles.queryBox}>
              <Text style={styles.queryText}>"{queryText}"</Text>
            </div>
          </Section>

          {/* Download CTA */}
          <Section style={styles.section}>
            <div style={styles.ctaSection}>
              <Text style={styles.ctaText}>
                Click the button below to download your report
              </Text>
              <Link href={downloadUrl} style={styles.ctaButton}>
                Download Report
              </Link>
            </div>
          </Section>

          {/* Expiration Warning */}
          <Section style={styles.section}>
            <div style={styles.expirationWarning}>
              <Text style={styles.warningText}>
                <strong>⏰ Download Expires:</strong> {expirationTime}
                <br />
                This link will expire in {hoursUntilExpiration} hours. Please download
                before the link expires.
              </Text>
            </div>
          </Section>

          <Hr style={{ margin: "0" }} />

          {/* Footer */}
          <Section style={styles.footer}>
            <Text style={styles.footerText}>
              If you don't need this report, you can safely ignore this email.
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

export default ReportReadyEmail;
