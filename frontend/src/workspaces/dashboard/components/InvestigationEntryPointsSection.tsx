import { Link } from 'react-router-dom'

import { ROUTE_PATHS } from '@/app/routing/routePaths'
import { Grid, SectionContainer } from '@/shared/components/layout'
import { Icon, type IconName } from '@/shared/icons'

import styles from './InvestigationEntryPointsSection.module.css'

interface EntryPoint {
  label: string
  description: string
  path: string
  icon: IconName
}

const ENTRY_POINTS: EntryPoint[] = [
  {
    label: 'Action Center',
    description: 'Everything currently requiring operational attention.',
    path: ROUTE_PATHS.actionCenter,
    icon: 'actionCenter',
  },
  {
    label: 'Investigations',
    description: 'Continue an in-progress investigation.',
    path: ROUTE_PATHS.investigations,
    icon: 'investigations',
  },
  {
    label: 'Recommendations',
    description: 'Review and manage open recommendations.',
    path: ROUTE_PATHS.recommendations,
    icon: 'recommendations',
  },
]

/**
 * Section 3: real, functional navigation toward ongoing operational
 * work -- unlike the other three Home sections, entry points *are*
 * navigation, not business data, so these links are genuinely wired to
 * their destination workspaces rather than placeholders.
 */
export function InvestigationEntryPointsSection() {
  return (
    <SectionContainer title="Investigation Entry Points" description="Continue ongoing operational work.">
      <Grid minColumnWidth={220}>
        {ENTRY_POINTS.map((entry) => (
          <Link key={entry.path} to={entry.path} className={styles.entryLink}>
            <span className={styles.entryIcon} aria-hidden="true">
              <Icon name={entry.icon} size={18} />
            </span>
            <span>
              <span className={styles.entryLabel}>{entry.label}</span>
              <br />
              <span className={styles.entryDescription}>{entry.description}</span>
            </span>
          </Link>
        ))}
      </Grid>
    </SectionContainer>
  )
}
