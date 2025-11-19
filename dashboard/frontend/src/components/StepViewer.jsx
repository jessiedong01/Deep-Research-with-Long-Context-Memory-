/**
 * Component to display data for a specific pipeline step
 */
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import "./StepViewer.css";

export function StepViewer({ stepData, stepInfo }) {
  const [expandedSections, setExpandedSections] = useState({});

  const toggleSection = (section) => {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  if (!stepData || !stepData.data) {
    return (
      <div className="step-viewer">
        <p className="no-data">No data available for this step.</p>
      </div>
    );
  }

  const data = stepData.data;

  // Render purpose generation step
  const renderPurposeGeneration = () => (
    <div className="step-content">
      <h2>Research Needs</h2>
      <div className="research-needs">
        {data.research_needs?.map((need, idx) => (
          <div key={idx} className="research-need-card">
            <h3>Research Need {idx + 1}</h3>
            <p>{need}</p>
          </div>
        ))}
      </div>
      {data.topic && (
        <div className="info-section">
          <h3>Topic</h3>
          <p>{data.topic}</p>
        </div>
      )}
    </div>
  );

  // Render outline generation step
  const renderOutlineGeneration = () => {
    // Extract markdown content from the outline
    let markdownContent = null;

    if (data.outline?.markdown) {
      const rawMarkdown = data.outline.markdown;

      // Check if it's a ModelResponse string representation
      if (
        typeof rawMarkdown === "string" &&
        rawMarkdown.startsWith("ModelResponse(")
      ) {
        // Extract content from the ModelResponse string
        const contentMatch = rawMarkdown.match(
          /content='([^']*(?:\\.[^']*)*)'/
        );
        if (contentMatch) {
          // Unescape the content
          markdownContent = contentMatch[1]
            .replace(/\\n/g, "\n")
            .replace(/\\'/g, "'")
            .replace(/\\"/g, '"')
            .replace(/\\\\/g, "\\");
        }
      } else {
        // It's already properly formatted markdown
        markdownContent = rawMarkdown;
      }
    }

    return (
      <div className="step-content">
        <h2>Report Outline</h2>
        {data.topic && (
          <div className="info-section">
            <h3>Topic</h3>
            <p>{data.topic}</p>
          </div>
        )}
        {markdownContent ? (
          <div className="markdown-content">
            <ReactMarkdown>{markdownContent}</ReactMarkdown>
          </div>
        ) : data.outline?.markdown ? (
          <div className="raw-content">
            <p className="no-data">
              Unable to parse outline format. Showing raw content:
            </p>
            <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {data.outline.markdown}
            </pre>
          </div>
        ) : (
          <p className="no-data">No outline available.</p>
        )}
      </div>
    );
  };

  // Render literature search step
  const renderLiteratureSearch = () => (
    <div className="step-content">
      <h2>Literature Search Results</h2>

      {/* Summary Information */}
      {data.research_needs && (
        <div className="info-section">
          <h3>Research Needs</h3>
          {data.research_needs.map((need, idx) => (
            <div key={idx} className="research-need-card">
              <p>{need}</p>
            </div>
          ))}
        </div>
      )}

      {stepData.metadata && (
        <div className="metadata-section">
          <h3>Search Statistics</h3>
          <div className="metadata-grid">
            {data.results_count !== undefined && (
              <div className="metadata-item">
                <span className="label">Results Found:</span>
                <span className="value">{data.results_count}</span>
              </div>
            )}
            {data.total_cited_documents !== undefined && (
              <div className="metadata-item">
                <span className="label">Total Documents Cited:</span>
                <span className="value">{data.total_cited_documents}</span>
              </div>
            )}
            {stepData.metadata.research_needs_count !== undefined && (
              <div className="metadata-item">
                <span className="label">Research Needs:</span>
                <span className="value">
                  {stepData.metadata.research_needs_count}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* RAG Responses (if available in old format) */}
      {data.rag_responses?.map((ragResponse, idx) => (
        <div key={idx} className="rag-response-card">
          <h3>Search {idx + 1}</h3>
          <div className="question-section">
            <h4>Question</h4>
            <p>{ragResponse.question}</p>
          </div>
          <div className="answer-section">
            <h4>Answer</h4>
            <div className="markdown-content">
              <ReactMarkdown>{ragResponse.answer}</ReactMarkdown>
            </div>
          </div>
          {ragResponse.key_insight && (
            <div className="insight-section">
              <h4>Key Insight</h4>
              <p>{ragResponse.key_insight}</p>
            </div>
          )}
          {ragResponse.cited_documents &&
            ragResponse.cited_documents.length > 0 && (
              <div className="documents-section">
                <h4
                  onClick={() => toggleSection(`cited-${idx}`)}
                  className="collapsible-header"
                >
                  Cited Documents ({ragResponse.cited_documents.length})
                  <span className="toggle-icon">
                    {expandedSections[`cited-${idx}`] ? "▼" : "▶"}
                  </span>
                </h4>
                {expandedSections[`cited-${idx}`] && (
                  <div className="documents-list">
                    {ragResponse.cited_documents.map((doc, docIdx) => (
                      <div key={docIdx} className="document-card">
                        <a
                          href={doc.url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {doc.title || doc.url}
                        </a>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
        </div>
      ))}

      {!data.rag_responses && !data.research_needs && (
        <p className="no-data">No literature search data available.</p>
      )}
    </div>
  );

  // Render report generation step
  const renderReportGeneration = () => {
    // Handle both array format and object with reports key
    const reports = Array.isArray(data) ? data : data.reports;

    return (
      <div className="step-content">
        <h2>Individual Reports</h2>

        {stepData.metadata && stepData.metadata.reports_count && (
          <div className="info-section">
            <p>
              <strong>Total Reports:</strong> {stepData.metadata.reports_count}
            </p>
          </div>
        )}

        {reports?.map((report, idx) => (
          <div key={idx} className="report-card">
            <h3>Report {idx + 1}</h3>

            {report.research_need && (
              <div className="info-section">
                <h4>Research Need</h4>
                <p>{report.research_need}</p>
              </div>
            )}

            <div className="markdown-content">
              <ReactMarkdown>{report.report || report}</ReactMarkdown>
            </div>

            {report.cited_documents_count !== undefined && (
              <div className="metadata-section">
                <p>
                  <strong>Documents Cited:</strong>{" "}
                  {report.cited_documents_count}
                </p>
              </div>
            )}
          </div>
        ))}

        {!reports && <p className="no-data">No reports available.</p>}
      </div>
    );
  };

  // Render final report step
  const renderFinalReport = () => (
    <div className="step-content">
      <h2>Final Report</h2>
      {data.final_report && (
        <div className="final-report">
          <div className="markdown-content">
            <ReactMarkdown>{data.final_report}</ReactMarkdown>
          </div>
        </div>
      )}
      {stepData.metadata && (
        <div className="metadata-section">
          <h3>Metadata</h3>
          <div className="metadata-grid">
            {stepData.metadata.report_length && (
              <div className="metadata-item">
                <span className="label">Report Length:</span>
                <span className="value">
                  {stepData.metadata.report_length} characters
                </span>
              </div>
            )}
            {data.total_research_needs !== undefined && (
              <div className="metadata-item">
                <span className="label">Total Research Needs:</span>
                <span className="value">{data.total_research_needs}</span>
              </div>
            )}
            {data.total_reports !== undefined && (
              <div className="metadata-item">
                <span className="label">Total Reports:</span>
                <span className="value">{data.total_reports}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );

  // Render root literature search step for the recursive pipeline
  const renderRootLiteratureSearch = () => (
    <div className="step-content">
      <h2>Root Literature Search</h2>
      {data.topic && (
        <div className="info-section">
          <h3>Topic</h3>
          <p>{data.topic}</p>
        </div>
      )}
      {data.writeup && (
        <div className="markdown-content">
          <ReactMarkdown>{data.writeup}</ReactMarkdown>
        </div>
      )}
      {Array.isArray(data.cited_documents) && data.cited_documents.length > 0 && (
        <div className="documents-section">
          <h3>Cited Documents</h3>
          <div className="documents-list">
            {data.cited_documents.map((doc, idx) => (
              <div key={idx} className="document-card">
                <a
                  href={doc.url}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {doc.title || doc.url}
                </a>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  // Render root answerability decision step
  const renderRootIsAnswerable = () => (
    <div className="step-content">
      <h2>Root Answerability Decision</h2>
      {data.topic && (
        <div className="info-section">
          <h3>Topic</h3>
          <p>{data.topic}</p>
        </div>
      )}
      <div className="info-section">
        <h3>Is Answerable?</h3>
        <p>{data.is_answerable ? "Yes" : "No"}</p>
      </div>
      {data.reasoning && (
        <div className="info-section">
          <h3>Reasoning</h3>
          <p>{data.reasoning}</p>
        </div>
      )}
    </div>
  );

  // Render root subtask generation step
  const renderRootSubtaskGeneration = () => (
    <div className="step-content">
      <h2>Root Subtask Generation</h2>
      {data.topic && (
        <div className="info-section">
          <h3>Topic</h3>
          <p>{data.topic}</p>
        </div>
      )}
      {Array.isArray(data.subtasks) && data.subtasks.length > 0 ? (
        <div className="research-needs">
          {data.subtasks.map((subtask, idx) => (
            <div key={idx} className="research-need-card">
              <h3>Subtask {idx + 1}</h3>
              <p>{subtask}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="no-data">No subtasks were generated for the root question.</p>
      )}
      {data.composition_explanation && (
        <div className="info-section">
          <h3>Composition Explanation</h3>
          <p>{data.composition_explanation}</p>
        </div>
      )}
    </div>
  );

  // Render recursive DAG step
  const renderRecursiveGraph = () => {
    const nodes = data.nodes || {};
    const rootId = data.root_id;

    if (!rootId || !nodes[rootId]) {
      return (
        <div className="step-content">
          <h2>Recursive Research DAG</h2>
          <p className="no-data">
            No graph structure found for this run. Showing raw data instead.
          </p>
          <pre>{JSON.stringify(data, null, 2)}</pre>
        </div>
      );
    }

    const renderNode = (nodeId, visited) => {
      const node = nodes[nodeId];
      if (!node) return null;

      const nextVisited = new Set(visited);
      const alreadyVisited = nextVisited.has(nodeId);
      nextVisited.add(nodeId);

      const status = (node.status || "pending").toLowerCase();
      const isReused =
        Array.isArray(node.parents) && node.parents.length > 1 && nodeId !== rootId;
      const isRoot = nodeId === rootId;
      const isLeaf =
        (!Array.isArray(node.children) || node.children.length === 0) &&
        (Array.isArray(node.subtasks) ? node.subtasks.length === 0 : true);

      return (
        <li key={nodeId}>
          <div
            className={`graph-node graph-node-status-${status} ${
              isRoot ? "graph-node-root" : ""
            } ${isLeaf ? "graph-node-leaf" : ""}`}
          >
            <div className="graph-node-header">
              <span className="graph-node-title">{node.question}</span>
              <span className={`graph-node-status-pill status-${status}`}>
                {status}
              </span>
              {isRoot && (
                <span className="graph-node-badge graph-node-badge-root">
                  Root
                </span>
              )}
              {isReused && (
                <span className="graph-node-badge">Reused</span>
              )}
            </div>
            <div className="graph-node-meta">
              <span>Depth: {node.depth ?? 0}</span>
              {node.is_answerable !== undefined && (
                <span>
                  Answerable: {node.is_answerable ? "Yes" : "No"}
                </span>
              )}
              {Array.isArray(node.subtasks) && node.subtasks.length > 0 && (
                <span>Subtasks: {node.subtasks.length}</span>
              )}
            </div>
          </div>
          {!alreadyVisited &&
            Array.isArray(node.children) &&
            node.children.length > 0 && (
              <ul className="graph-children">
                {node.children.map((childId) =>
                  renderNode(childId, nextVisited)
                )}
              </ul>
            )}
        </li>
      );
    };

    return (
      <div className="step-content">
        <h2>Recursive Research DAG</h2>

        {stepData.metadata && (
          <div className="metadata-section">
            <h3>Graph Summary</h3>
            <div className="metadata-grid">
              {stepData.metadata.total_nodes !== undefined && (
                <div className="metadata-item">
                  <span className="label">Total Nodes:</span>
                  <span className="value">
                    {stepData.metadata.total_nodes}
                  </span>
                </div>
              )}
              {stepData.metadata.max_depth !== undefined && (
                <div className="metadata-item">
                  <span className="label">Max Depth:</span>
                  <span className="value">
                    {stepData.metadata.max_depth}
                  </span>
                </div>
              )}
              {stepData.metadata.max_nodes !== undefined && (
                <div className="metadata-item">
                  <span className="label">Node Budget:</span>
                  <span className="value">
                    {stepData.metadata.max_nodes}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="graph-tree">
          <ul className="graph-root">
            {renderNode(rootId, new Set())}
          </ul>
        </div>
      </div>
    );
  };

  // Render Phase 1: DAG Generation
  const renderDAGGeneration = () => {
    const metadata = stepData.metadata || {};
    const formatCounts = {};
    
    // Count output format types if available
    if (data.nodes) {
      Object.values(data.nodes).forEach(node => {
        const format = node.expected_output_format || 'unknown';
        formatCounts[format] = (formatCounts[format] || 0) + 1;
      });
    }

    return (
      <div className="step-content">
        <h2>Phase 1: DAG Generation</h2>
        <div className="info-section">
          <h3>Generation Summary</h3>
          <div className="metadata-grid">
            <div className="metadata-item">
              <span className="label">Total Nodes:</span>
              <span className="value">{metadata.total_nodes || 0}</span>
            </div>
            <div className="metadata-item">
              <span className="label">Max Depth Reached:</span>
              <span className="value">{metadata.max_depth_reached || 0}</span>
            </div>
            <div className="metadata-item">
              <span className="label">Leaf Nodes:</span>
              <span className="value">{metadata.leaf_nodes || 0}</span>
            </div>
          </div>
        </div>

        {Object.keys(formatCounts).length > 0 && (
          <div className="info-section">
            <h3>Node Breakdown by Format</h3>
            <div className="format-breakdown">
              {Object.entries(formatCounts).map(([format, count]) => (
                <div key={format} className="format-item">
                  <span className="format-name">{format}</span>
                  <span className="format-count">{count} nodes</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="info-section">
          <h3>Root Question</h3>
          <p>{data.nodes?.[data.root_id]?.question || 'N/A'}</p>
        </div>
      </div>
    );
  };

  // Render Phase 2: DAG Processing
  const renderDAGProcessed = () => {
    const metadata = stepData.metadata || {};
    const nodes = data.nodes || {};
    const completedNodes = Object.values(nodes).filter(n => n.status === 'complete' || n.status === 'completed');

    return (
      <div className="step-content">
        <h2>Phase 2: DAG Processing</h2>
        <div className="info-section">
          <h3>Processing Summary</h3>
          <div className="metadata-grid">
            <div className="metadata-item">
              <span className="label">Nodes Completed:</span>
              <span className="value">{completedNodes.length} / {Object.keys(nodes).length}</span>
            </div>
            {metadata.processing_time && (
              <div className="metadata-item">
                <span className="label">Processing Time:</span>
                <span className="value">{metadata.processing_time}s</span>
              </div>
            )}
          </div>
        </div>

        <div className="info-section">
          <h3>Node Results</h3>
          <div className="node-results">
            {completedNodes.map((node, idx) => (
              <div key={node.id || idx} className="node-result-card">
                <div className="node-result-header">
                  <span className="node-question-title">{node.question}</span>
                  {node.expected_output_format && (
                    <span className="node-format-badge">{node.expected_output_format}</span>
                  )}
                </div>
                {node.report && (
                  <div className="node-result-answer">
                    <ReactMarkdown>{node.report}</ReactMarkdown>
                  </div>
                )}
                {node.cited_documents && node.cited_documents.length > 0 && (
                  <div className="node-citations">
                    <span className="citations-count">
                      📚 {node.cited_documents.length} citations
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // Render Phase 3: Final Report (enhanced version of existing renderFinalReport)
  const renderThreePhaseFinalReport = () => {
    const metadata = stepData.metadata || {};

    return (
      <div className="step-content">
        <h2>Phase 3: Final Report</h2>
        <div className="info-section">
          <h3>Report Statistics</h3>
          <div className="metadata-grid">
            {metadata.report_length && (
              <div className="metadata-item">
                <span className="label">Report Length:</span>
                <span className="value">{metadata.report_length} characters</span>
              </div>
            )}
            {metadata.num_citations !== undefined && (
              <div className="metadata-item">
                <span className="label">Citations:</span>
                <span className="value">{metadata.num_citations}</span>
              </div>
            )}
          </div>
        </div>

        {data.outline && (
          <div className="info-section">
            <h3>Report Outline</h3>
            <div className="outline-content">
              <ReactMarkdown>{data.outline}</ReactMarkdown>
            </div>
          </div>
        )}

        {data.report && (
          <div className="info-section">
            <h3>Final Report</h3>
            <div className="markdown-content">
              <ReactMarkdown>{data.report}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Route to appropriate renderer based on step name
  const renderStepContent = () => {
    switch (stepInfo.step_name) {
      // Three-phase pipeline steps
      case "00_dag_generation":
        return renderDAGGeneration();
      case "01_dag_processed":
        return renderDAGProcessed();
      case "02_final_report":
        return renderThreePhaseFinalReport();
      
      // Legacy pipeline steps
      case "01_purpose_generation":
        return renderPurposeGeneration();
      case "02_outline_generation":
        return renderOutlineGeneration();
      case "03_literature_search":
        return renderLiteratureSearch();
      case "04_report_generation":
        return renderReportGeneration();
      case "05_final_report":
        return renderFinalReport();
      case "00_root_literature_search":
        return renderRootLiteratureSearch();
      case "01_root_is_answerable":
        return renderRootIsAnswerable();
      case "02_root_subtask_generation":
        return renderRootSubtaskGeneration();
      case "recursive_graph":
        return renderRecursiveGraph();
      default:
        return (
          <div className="step-content">
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </div>
        );
    }
  };

  return (
    <div className="step-viewer">
      <div className="step-header">
        <h1>{stepInfo.step_name.replace(/_/g, " ").toUpperCase()}</h1>
        <span className={`status-badge status-${stepInfo.status}`}>
          {stepInfo.status}
        </span>
      </div>
      {renderStepContent()}
    </div>
  );
}
