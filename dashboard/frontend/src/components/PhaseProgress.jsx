import React from 'react';
import './PhaseProgress.css';

/**
 * Component to display the three-phase pipeline progress.
 * Shows: Phase 1 (DAG Generation) -> Phase 2 (DAG Processing) -> Phase 3 (Report Generation)
 */
const PhaseProgress = ({ phases, currentPhase, isThreePhase }) => {
  if (!isThreePhase) {
    return null; // Don't show for legacy runs
  }

  const phaseDefinitions = [
    {
      id: 'dag_generation',
      name: 'Phase 1',
      title: 'DAG Generation',
      icon: '🗺️',
    },
    {
      id: 'dag_processing',
      name: 'Phase 2',
      title: 'DAG Processing',
      icon: '⚙️',
    },
    {
      id: 'report_generation',
      name: 'Phase 3',
      title: 'Report Generation',
      icon: '📄',
    },
  ];

  // Map phases array to status lookup
  const phaseStatus = {};
  if (phases && Array.isArray(phases)) {
    phases.forEach((phase) => {
      phaseStatus[phase.phase] = phase;
    });
  }

  // Determine if a phase is complete, in progress, or pending
  const getPhaseState = (phaseId) => {
    if (phaseStatus[phaseId]) {
      return 'completed';
    }
    if (currentPhase === phaseId) {
      return 'in-progress';
    }
    return 'pending';
  };

  return (
    <div className="phase-progress">
      <h3 className="phase-progress-title">Pipeline Progress</h3>
      <div className="phase-progress-bar">
        {phaseDefinitions.map((phase, index) => {
          const state = getPhaseState(phase.id);
          const phaseData = phaseStatus[phase.id];

          return (
            <React.Fragment key={phase.id}>
              <div className={`phase-step phase-${state}`}>
                <div className="phase-icon">{phase.icon}</div>
                <div className="phase-info">
                  <div className="phase-name">{phase.name}</div>
                  <div className="phase-title">{phase.title}</div>
                  {phaseData && phaseData.metrics && (
                    <div className="phase-metrics">
                      {phase.id === 'dag_generation' && (
                        <>
                          <span>Nodes: {phaseData.metrics.total_nodes || 0}</span>
                          <span>Depth: {phaseData.metrics.max_depth_reached || 0}</span>
                        </>
                      )}
                      {phase.id === 'dag_processing' && (
                        <>
                          <span>Completed: {phaseData.metrics.completed_nodes || 0}</span>
                        </>
                      )}
                      {phase.id === 'report_generation' && (
                        <>
                          <span>Citations: {phaseData.metrics.num_citations || 0}</span>
                        </>
                      )}
                    </div>
                  )}
                </div>
                <div className="phase-status-indicator">
                  {state === 'completed' && <span className="status-icon">✓</span>}
                  {state === 'in-progress' && <span className="status-icon">⏳</span>}
                  {state === 'pending' && <span className="status-icon">○</span>}
                </div>
              </div>
              {index < phaseDefinitions.length - 1 && (
                <div className={`phase-connector phase-connector-${state}`}>
                  <div className="connector-line"></div>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default PhaseProgress;

