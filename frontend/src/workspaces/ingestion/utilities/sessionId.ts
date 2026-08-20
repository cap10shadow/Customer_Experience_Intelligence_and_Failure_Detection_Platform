/**
 * One `analysisSessionId` per upload/review round -- generated once per
 * `DatasetDetailView` mount (a fresh dataset selection) and regenerated
 * on "Start over". Reused across every `:analyze` re-run within that
 * round (row edits, page changes, post-approval refreshes) so mapping
 * occurrence counts are never inflated by re-analyzing the same rows
 * (see the occurrence-session design in the mapping-persistence layer).
 */
export function createAnalysisSessionId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`
}
