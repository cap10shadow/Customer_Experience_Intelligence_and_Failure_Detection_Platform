/**
 * Canonical TypeScript mirror of the backend's real, closed enums
 * (`backend/shared/constants/enums/complaint.py`,
 * `backend/shared/constants/enums/business_impact.py`) -- hand-synced,
 * not generated. These are the only fields `ingestion_service`'s
 * `ComplaintCreateRequest` accepts a Pydantic enum for (rather than a
 * free-text string); submitting any other value, in any casing, is
 * rejected with a real 422. Kept here so the Data workspace can
 * normalize and validate a row's enum fields client-side, before
 * submission, instead of only discovering a casing mismatch from a
 * failed request.
 */
export const SOURCE_CHANNELS = [
  'email',
  'chat',
  'support_ticket',
  'social_media',
  'mobile_app',
  'website_form',
  'call_center',
  'marketplace',
  'internal_system',
] as const

export const CUSTOMER_SEGMENTS = ['individual', 'premium', 'enterprise', 'partner', 'reseller', 'unknown'] as const

export const CUSTOMER_TYPES = [
  'new_customer',
  'existing_customer',
  'high_value_customer',
  'at_risk_customer',
  'churned_customer',
  'unidentified',
] as const

export const OPERATIONAL_AREAS = [
  'logistics',
  'payments',
  'customer_support',
  'delivery',
  'inventory',
  'product_quality',
  'returns',
  'account_management',
  'subscription_services',
  'technical_platform',
  'packaging',
  'refunds',
  'order_management',
  'fulfillment',
] as const

export const SERVICE_TYPES = [
  'fulfillment',
  'payment_processing',
  'customer_service',
  'delivery_operations',
  'digital_services',
  'subscription_management',
  'platform_operations',
] as const

export type SourceChannel = (typeof SOURCE_CHANNELS)[number]
export type CustomerSegment = (typeof CUSTOMER_SEGMENTS)[number]
export type CustomerType = (typeof CUSTOMER_TYPES)[number]
export type OperationalArea = (typeof OPERATIONAL_AREAS)[number]
export type ServiceType = (typeof SERVICE_TYPES)[number]

// Normalization/validation for these fields is no longer performed
// client-side (Ingestion Normalization & Mapping Layer plan, requirement
// 5: the backend owns normalization/mapping/validation for every field,
// not just customer_region/operational_area -- one consistent code
// path). `POST .../complaints:analyze` reports a structured
// `invalid_enum` issue for any of these five fields, same as it does for
// mapping-eligible fields. These arrays remain exported for display
// purposes only (e.g. UploadPanel's "accepted values" help text).
