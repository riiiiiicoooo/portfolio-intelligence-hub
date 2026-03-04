/**
 * Portfolio Intelligence Hub Query Interface Component
 *
 * A comprehensive React dashboard for querying and interacting with the
 * real estate portfolio intelligence system. Supports text-to-SQL queries,
 * semantic search, role-based personas, and result visualization.
 */

import React, { useState, useCallback, useEffect } from 'react';

/**
 * Main QueryInterface Component
 *
 * Provides a unified interface for querying property data across different
 * user personas with role-based access control and result visualization.
 */
function QueryInterface() {
  // State management
  const [query, setQuery] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);
  const [activePersona, setActivePersona] = useState('property_manager');
  const [savedQueries, setSavedQueries] = useState([]);
  const [showSavedQueries, setShowSavedQueries] = useState(false);
  const [exportLoading, setExportLoading] = useState(false);

  // Suggested queries by persona
  const suggestedQueries = {
    property_manager: [
      'Which buildings have the most open work orders?',
      'Show me all units with pending maintenance',
      'What is the current occupancy rate for each property?',
      'List all leases expiring in the next 90 days',
    ],
    broker: [
      'Show me all leases with renewal options',
      'Which units are currently vacant and ready for leasing?',
      'What are the average rents by unit type?',
      'List all active leases with their renewal deadlines',
    ],
    finance: [
      'What is the NOI trend for each property?',
      'Show me properties with budget variances exceeding 5%',
      'Calculate the portfolio-wide cap rate weighted average',
      'How much did we spend on maintenance last month?',
    ],
    executive: [
      'What is the total portfolio valuation?',
      'Show portfolio occupancy trends over the last 3 months',
      'Which properties are underperforming?',
      'What is the overall portfolio health summary?',
    ],
  };

  // Fetch results from API
  const submitQuery = useCallback(async (e) => {
    e.preventDefault();

    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/queries', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({
          query: query,
          persona: activePersona,
        }),
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Unauthorized. Please log in.');
        }
        throw new Error(`Query failed with status ${response.status}`);
      }

      const data = await response.json();

      setResults(data);
      setHistory([
        {
          query: query,
          timestamp: new Date().toISOString(),
          persona: activePersona,
          query_id: data.query_id,
        },
        ...history,
      ].slice(0, 20));

      setQuery('');
    } catch (err) {
      setError(err.message);
      setResults(null);
    } finally {
      setLoading(false);
    }
  }, [query, activePersona, history]);

  // Load query from history
  const loadFromHistory = useCallback((historyQuery) => {
    setQuery(historyQuery.query);
    setActivePersona(historyQuery.persona);
  }, []);

  // Save current query
  const saveQuery = useCallback(() => {
    if (query.trim()) {
      setSavedQueries([
        ...savedQueries,
        {
          id: Date.now(),
          query: query,
          persona: activePersona,
        },
      ]);
    }
  }, [query, activePersona, savedQueries]);

  // Delete saved query
  const deleteSavedQuery = useCallback((id) => {
    setSavedQueries(savedQueries.filter((q) => q.id !== id));
  }, [savedQueries]);

  // Export results
  const exportResults = useCallback(async (format = 'pdf') => {
    if (!results || !results.query_id) {
      setError('No results to export');
      return;
    }

    setExportLoading(true);

    try {
      const response = await fetch('/api/v1/export/report', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_token')}`,
        },
        body: JSON.stringify({
          query_id: results.query_id,
          format: format,
        }),
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const data = await response.json();
      // In real implementation, would download the file
      console.log('Export created:', data.export_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setExportLoading(false);
    }
  }, [results]);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        {/* Persona Selector */}
        <div className="p-6 border-b border-gray-200">
          <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-4">
            Persona
          </h3>
          <div className="space-y-2">
            {Object.keys(suggestedQueries).map((persona) => (
              <button
                key={persona}
                onClick={() => setActivePersona(persona)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activePersona === persona
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                {persona
                  .split('_')
                  .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
                  .join(' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Suggested Queries */}
        <div className="flex-1 overflow-y-auto p-6 border-b border-gray-200">
          <h3 className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-4">
            Suggested Queries
          </h3>
          <div className="space-y-2">
            {suggestedQueries[activePersona].map((suggQuery, idx) => (
              <button
                key={idx}
                onClick={() => setQuery(suggQuery)}
                className="w-full text-left text-sm px-3 py-2 rounded-md text-gray-700 hover:bg-gray-100 transition-colors line-clamp-2"
                title={suggQuery}
              >
                {suggQuery}
              </button>
            ))}
          </div>
        </div>

        {/* Saved Queries */}
        <div className="p-6 border-t border-gray-200">
          <button
            onClick={() => setShowSavedQueries(!showSavedQueries)}
            className="w-full text-left text-xs font-semibold text-gray-600 uppercase tracking-wider hover:text-gray-800"
          >
            📌 Saved Queries ({savedQueries.length})
          </button>
          {showSavedQueries && savedQueries.length > 0 && (
            <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
              {savedQueries.map((savedQuery) => (
                <div
                  key={savedQuery.id}
                  className="p-2 bg-yellow-50 rounded-md border border-yellow-200 group"
                >
                  <p className="text-xs text-gray-700 mb-1 line-clamp-2">
                    {savedQuery.query}
                  </p>
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => {
                        setQuery(savedQuery.query);
                        setActivePersona(savedQuery.persona);
                      }}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      Load
                    </button>
                    <button
                      onClick={() => deleteSavedQuery(savedQuery.id)}
                      className="text-xs text-red-600 hover:text-red-800 opacity-0 group-hover:opacity-100"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 p-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Portfolio Intelligence Hub
          </h1>
          <p className="text-gray-600">
            Query your real estate portfolio with natural language
          </p>
        </div>

        {/* Query Section */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl">
            {/* Query Input */}
            <form onSubmit={submitQuery} className="mb-6">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask a question about your portfolio..."
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={loading}
                />
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 transition-colors flex items-center gap-2"
                >
                  {loading ? (
                    <>
                      <span className="inline-block animate-spin">⏳</span>
                      Searching...
                    </>
                  ) : (
                    <>🔍 Search</>
                  )}
                </button>
                {query.trim() && (
                  <button
                    type="button"
                    onClick={saveQuery}
                    className="px-4 py-3 bg-yellow-100 text-yellow-700 rounded-lg font-medium hover:bg-yellow-200 transition-colors"
                    title="Save this query"
                  >
                    📌
                  </button>
                )}
              </div>
            </form>

            {/* Error Message */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
                <strong>Error:</strong> {error}
              </div>
            )}

            {/* Results */}
            {results && (
              <div className="space-y-6">
                {/* Result Metadata */}
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Classification:</span>
                      <span className="ml-2 font-medium">
                        {results.classification}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600">Execution Time:</span>
                      <span className="ml-2 font-medium">
                        {results.execution_time || 'N/A'}
                      </span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-gray-600">Query ID:</span>
                      <span className="ml-2 font-mono text-xs">
                        {results.query_id}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Results Display */}
                <ResultsDisplay results={results} />

                {/* Export Options */}
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 flex gap-2">
                  <button
                    onClick={() => exportResults('pdf')}
                    disabled={exportLoading}
                    className="px-4 py-2 bg-red-100 text-red-700 rounded-lg font-medium hover:bg-red-200 disabled:bg-gray-200 transition-colors"
                  >
                    📄 PDF
                  </button>
                  <button
                    onClick={() => exportResults('csv')}
                    disabled={exportLoading}
                    className="px-4 py-2 bg-green-100 text-green-700 rounded-lg font-medium hover:bg-green-200 disabled:bg-gray-200 transition-colors"
                  >
                    📊 CSV
                  </button>
                  <button
                    onClick={() => exportResults('excel')}
                    disabled={exportLoading}
                    className="px-4 py-2 bg-blue-100 text-blue-700 rounded-lg font-medium hover:bg-blue-200 disabled:bg-gray-200 transition-colors"
                  >
                    📑 Excel
                  </button>
                </div>
              </div>
            )}

            {/* Query History */}
            {history.length > 0 && !results && (
              <div className="mt-8 p-6 bg-white rounded-lg border border-gray-200">
                <h2 className="text-lg font-bold text-gray-900 mb-4">
                  📜 Recent Queries
                </h2>
                <div className="space-y-2">
                  {history.map((histItem, idx) => (
                    <button
                      key={idx}
                      onClick={() => loadFromHistory(histItem)}
                      className="w-full text-left p-3 bg-gray-50 hover:bg-blue-50 rounded-lg transition-colors group"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-sm text-gray-900 font-medium line-clamp-2">
                            {histItem.query}
                          </p>
                          <p className="text-xs text-gray-500 mt-1">
                            {histItem.persona} • {new Date(histItem.timestamp).toLocaleString()}
                          </p>
                        </div>
                        <span className="text-sm text-blue-600 opacity-0 group-hover:opacity-100">
                          Load
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * ResultsDisplay Component
 *
 * Renders query results in appropriate format based on classification.
 * Supports markdown tables for structured queries and search results cards
 * for semantic search.
 */
function ResultsDisplay({ results }) {
  if (!results) return null;

  const { classification, results: data } = results;

  // Handle text-to-sql results as table
  if (classification === 'TEXT_TO_SQL' && Array.isArray(data)) {
    if (data.length === 0) {
      return (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg text-blue-700">
          <strong>No Results</strong>
          <p className="text-sm mt-1">
            Your query returned no matching records.
          </p>
        </div>
      );
    }

    const columns = Object.keys(data[0]);

    return (
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                {columns.map((col) => (
                  <th
                    key={col}
                    className="px-6 py-3 text-left font-semibold text-gray-900"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row, idx) => (
                <tr
                  key={idx}
                  className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
                >
                  {columns.map((col) => (
                    <td
                      key={col}
                      className="px-6 py-3 text-gray-700"
                    >
                      {String(row[col])}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-600">
          Showing {data.length} result{data.length !== 1 ? 's' : ''}
        </div>
      </div>
    );
  }

  // Handle semantic search results
  if (classification === 'SEMANTIC_SEARCH' && data) {
    const searchData = data[0];

    return (
      <div className="space-y-4">
        {/* Synthesized Answer */}
        {searchData.synthesized_answer && (
          <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg">
            <h3 className="font-semibold text-blue-900 mb-2">Answer</h3>
            <p className="text-blue-800 leading-relaxed">
              {searchData.synthesized_answer}
            </p>
            {searchData.confidence !== undefined && (
              <div className="mt-4 flex items-center gap-2">
                <span className="text-sm text-blue-700">Confidence:</span>
                <div className="w-32 h-2 bg-blue-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-600 transition-all"
                    style={{
                      width: `${Math.round(searchData.confidence * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-sm font-medium text-blue-700">
                  {Math.round(searchData.confidence * 100)}%
                </span>
              </div>
            )}
          </div>
        )}

        {/* Retrieved Chunks */}
        {searchData.retrieved_chunks && searchData.retrieved_chunks.length > 0 && (
          <div>
            <h3 className="font-semibold text-gray-900 mb-3">
              📑 Retrieved Sources
            </h3>
            <div className="space-y-3">
              {searchData.retrieved_chunks.map((chunk, idx) => (
                <div
                  key={idx}
                  className="p-4 bg-white border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h4 className="font-medium text-gray-900">{chunk.title}</h4>
                    <span className="text-xs font-mono text-gray-500">
                      {chunk.doc_id}
                    </span>
                  </div>
                  <p className="text-sm text-gray-700 mb-3">{chunk.content}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">
                      Relevance Score
                    </span>
                    <div className="w-24 h-1 bg-gray-200 rounded-full overflow-hidden inline-block">
                      <div
                        className="h-full bg-green-500 transition-all"
                        style={{
                          width: `${Math.round(chunk.score * 100)}%`,
                        }}
                      />
                    </div>
                    <span className="text-xs font-medium text-gray-700 ml-2">
                      {Math.round(chunk.score * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // Default fallback
  return (
    <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-gray-700">
      <pre className="whitespace-pre-wrap text-sm">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export default QueryInterface;
