import type { DatasetDetail, DatasetSummary, DatasetVersion, RecentComplaint } from '../types'
import type {
  DatasetDetailApiResponse,
  DatasetSummaryApiResponse,
  DatasetVersionApiResponse,
  IngestionComplaintApiResponse,
  IngestionComplaintListApiResponse,
} from './types'

function toRecentComplaint(complaint: IngestionComplaintApiResponse): RecentComplaint {
  return {
    id: complaint.id,
    complaintText: complaint.complaintText,
    complaintTitle: complaint.complaintTitle ?? undefined,
    customerRegion: complaint.customerRegion ?? undefined,
    operationalArea: complaint.operationalArea ?? undefined,
    complaintStatus: complaint.complaintStatus,
    processingStage: complaint.processingStage,
    insertedAt: complaint.insertedAt,
  }
}

export interface RecentComplaintsViewModel {
  items: RecentComplaint[]
  totalCount: number
}

export function toRecentComplaintsViewModel(response: IngestionComplaintListApiResponse): RecentComplaintsViewModel {
  return {
    items: response.items.map(toRecentComplaint),
    totalCount: response.totalCount,
  }
}

export function toDatasetVersion(response: DatasetVersionApiResponse): DatasetVersion {
  return {
    id: response.id,
    datasetId: response.datasetId,
    versionNumber: response.versionNumber,
    status: response.status,
    cumulativeRecordCount: response.cumulativeRecordCount,
    newRecordCount: response.newRecordCount,
    analysisStartedAt: response.analysisStartedAt ?? undefined,
    analysisCompletedAt: response.analysisCompletedAt ?? undefined,
    failureReason: response.failureReason ?? undefined,
    insertedAt: response.insertedAt,
  }
}

export function toDatasetSummary(response: DatasetSummaryApiResponse): DatasetSummary {
  return {
    id: response.id,
    name: response.name,
    description: response.description ?? undefined,
    insertedAt: response.insertedAt,
    isLegacy: response.isLegacy ?? false,
    currentVersion: response.currentVersion ? toDatasetVersion(response.currentVersion) : undefined,
    latestVersion: response.latestVersion ? toDatasetVersion(response.latestVersion) : undefined,
    openIncidentCount: response.openIncidentCount ?? undefined,
  }
}

export function toDatasetDetail(response: DatasetDetailApiResponse): DatasetDetail {
  return {
    id: response.dataset.id,
    name: response.dataset.name,
    description: response.dataset.description ?? undefined,
    insertedAt: response.dataset.insertedAt,
    isLegacy: response.dataset.isLegacy ?? false,
    versions: response.versions.map(toDatasetVersion),
    currentVersion: response.currentVersion ? toDatasetVersion(response.currentVersion) : undefined,
    latestVersion: response.latestVersion ? toDatasetVersion(response.latestVersion) : undefined,
  }
}
