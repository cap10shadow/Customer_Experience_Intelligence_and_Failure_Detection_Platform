export type ClassValue = string | number | false | null | undefined

/** Joins truthy class name fragments with a single space -- the one place conditional class logic lives, so components never hand-roll template-string concatenation. */
export function classNames(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
