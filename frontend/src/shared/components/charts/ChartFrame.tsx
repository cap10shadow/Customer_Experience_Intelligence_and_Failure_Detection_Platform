import type { ReactNode } from 'react'

import styles from './ChartFrame.module.css'

export interface ChartTableColumn {
  header: string
  /** Cell values, in the same order as `rowHeaders`. */
  values: string[]
}

export interface ChartFrameProps {
  title: string
  /** States what the chart shows and, where relevant, where the numbers came from. Never an interpretation of them. */
  description: string
  children: ReactNode
  /** Row labels for the equivalent-data table (the chart's non-visual reading). */
  rowHeaders: string[]
  /** The label for the first (row-header) column of that table. */
  rowHeaderLabel: string
  columns: ChartTableColumn[]
}

/**
 * The shared wrapper every chart in the platform sits in: a real heading,
 * a factual description, the plot itself, and -- always -- the same
 * numbers as a plain table.
 *
 * The table is not optional decoration. A chart encodes values as
 * geometry, which is unavailable to a screen-reader user and unreliable
 * for anyone reading exact figures, so every chart here ships its own
 * equivalent tabular reading in a collapsed `<details>`. It also means
 * the visual layer can never be the *only* record of a number the
 * platform is asserting -- consistent with this codebase's rule that
 * presentation never becomes a second source of truth.
 */
export function ChartFrame({ title, description, children, rowHeaders, rowHeaderLabel, columns }: ChartFrameProps) {
  return (
    <figure className={styles.frame}>
      <figcaption className={styles.caption}>
        <p className={styles.title}>{title}</p>
        <p className={styles.description}>{description}</p>
      </figcaption>

      <div className={styles.plot}>{children}</div>

      <details className={styles.dataToggle}>
        <summary>View as data</summary>
        <div className={styles.tableWrapper}>
          <table className={styles.table}>
            <caption className="visually-hidden">{`${title} — the same values shown in the chart above.`}</caption>
            <thead>
              <tr>
                <th scope="col">{rowHeaderLabel}</th>
                {columns.map((column) => (
                  <th key={column.header} scope="col">
                    {column.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowHeaders.map((rowHeader, rowIndex) => (
                <tr key={rowHeader}>
                  <th scope="row">{rowHeader}</th>
                  {columns.map((column) => (
                    <td key={column.header}>{column.values[rowIndex] ?? ''}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  )
}
