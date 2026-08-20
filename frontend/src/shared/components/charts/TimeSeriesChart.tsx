import styles from './TimeSeriesChart.module.css'

export interface TimeSeriesPoint {
  /** The x-axis value exactly as the backend returned it (an ISO date here) -- never re-derived or re-bucketed. */
  label: string
  value: number
}

export interface TimeSeriesChartProps {
  points: TimeSeriesPoint[]
  /** Describes the whole plot for a screen reader, e.g. "Complaint volume per day". */
  ariaLabel: string
  /** Formats a value for the axis and for a point's hover title. */
  formatValue?: (value: number) => string
  /**
   * Forces zero into the value range. Correct for a count (a bar of
   * volume starting at 40 would exaggerate variation); wrong for a
   * bounded score that never approaches zero. Callers choose per measure.
   */
  includeZero?: boolean
  /** Draws a dashed reference line at zero -- only meaningful when the measure is signed (e.g. a sentiment score). */
  showZeroBaseline?: boolean
}

const WIDTH = 760
const HEIGHT = 220
const PADDING = { top: 12, right: 14, bottom: 26, left: 46 }
const PLOT_WIDTH = WIDTH - PADDING.left - PADDING.right
const PLOT_HEIGHT = HEIGHT - PADDING.top - PADDING.bottom
const GRID_LINES = 4

function defaultFormat(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

/**
 * A single-series line-and-area chart over an ordered sequence of
 * observations. One series only, and therefore no legend and no
 * categorical palette: the chart's own title names the measure, and one
 * hue (`--color-chart-mark`) carries it.
 *
 * Deliberately hand-drawn SVG rather than a charting dependency. This
 * repository has never had one (`frontend/package.json`), the API
 * client's own header records the same reasoning for using native
 * `fetch`, and a two-form chart need (this and `CategoryBarChart`) does
 * not justify adding a runtime dependency, its bundle, and its own
 * theming layer to a design system that is already fully tokenized.
 *
 * Plots exactly the points it is given, in the order given. It never
 * interpolates a missing date, never smooths, never extrapolates beyond
 * the returned range, and never computes a trend line -- the backend
 * owns every number here (see the Analytics adapter's own "transform,
 * never invent" note).
 */
export function TimeSeriesChart({
  points,
  ariaLabel,
  formatValue = defaultFormat,
  includeZero = false,
  showZeroBaseline = false,
}: TimeSeriesChartProps) {
  if (points.length === 0) {
    return null
  }

  const values = points.map((point) => point.value)
  const rawMin = Math.min(...values, includeZero ? 0 : Number.POSITIVE_INFINITY)
  const rawMax = Math.max(...values, includeZero ? 0 : Number.NEGATIVE_INFINITY)
  // A flat series would otherwise divide by zero; give it a symmetric
  // band so the line renders through the middle rather than on an edge.
  const span = rawMax - rawMin
  const min = span === 0 ? rawMin - 1 : rawMin
  const max = span === 0 ? rawMax + 1 : rawMax
  const range = max - min

  const toX = (index: number) =>
    points.length === 1 ? PADDING.left + PLOT_WIDTH / 2 : PADDING.left + (index / (points.length - 1)) * PLOT_WIDTH
  const toY = (value: number) => PADDING.top + PLOT_HEIGHT - ((value - min) / range) * PLOT_HEIGHT

  const coordinates = points.map((point, index) => ({ x: toX(index), y: toY(point.value), point }))
  const linePath = coordinates.map(({ x, y }, index) => `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`).join(' ')
  const baseY = PADDING.top + PLOT_HEIGHT
  const areaPath = `${linePath} L${coordinates[coordinates.length - 1].x.toFixed(2)} ${baseY} L${coordinates[0].x.toFixed(2)} ${baseY} Z`

  const gridValues = Array.from({ length: GRID_LINES + 1 }, (_, index) => min + (range * index) / GRID_LINES)

  // Only three x labels (first / middle / last). Labelling every
  // observation collides as soon as the period is longer than a couple
  // of weeks, and the exact per-point values are always available from
  // ChartFrame's data table and each point's hover title.
  const labelIndices = new Set(
    points.length <= 2 ? points.map((_, index) => index) : [0, Math.floor((points.length - 1) / 2), points.length - 1],
  )

  return (
    <svg
      className={styles.svg}
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={ariaLabel}
    >
      {gridValues.map((value) => {
        const y = toY(value)
        return (
          <g key={`grid-${value}`}>
            <line className={styles.grid} x1={PADDING.left} x2={WIDTH - PADDING.right} y1={y} y2={y} />
            <text className={styles.axisLabel} x={PADDING.left - 8} y={y + 4} textAnchor="end">
              {formatValue(value)}
            </text>
          </g>
        )
      })}

      {showZeroBaseline && min < 0 && max > 0 ? (
        <line className={styles.baseline} x1={PADDING.left} x2={WIDTH - PADDING.right} y1={toY(0)} y2={toY(0)} />
      ) : null}

      <path className={styles.area} d={areaPath} />
      <path className={styles.line} d={linePath} />

      {coordinates.map(({ x, y, point }) => (
        <g key={point.label}>
          <circle className={styles.point} cx={x} cy={y} r={3} />
          {/* Native per-mark hover, with no JavaScript and no portal:
              the browser renders `<title>` as a tooltip and assistive
              technology reads it as the mark's accessible name. */}
          <rect
            className={styles.hitArea}
            x={x - 10}
            y={PADDING.top}
            width={20}
            height={PLOT_HEIGHT}
            tabIndex={-1}
            role="presentation"
          >
            <title>{`${point.label}: ${formatValue(point.value)}`}</title>
          </rect>
        </g>
      ))}

      {coordinates.map(({ x, point }, index) =>
        labelIndices.has(index) ? (
          <text
            key={`label-${point.label}`}
            className={styles.axisLabel}
            x={x}
            y={HEIGHT - 8}
            textAnchor={index === 0 ? 'start' : index === points.length - 1 ? 'end' : 'middle'}
          >
            {point.label}
          </text>
        ) : null,
      )}
    </svg>
  )
}
