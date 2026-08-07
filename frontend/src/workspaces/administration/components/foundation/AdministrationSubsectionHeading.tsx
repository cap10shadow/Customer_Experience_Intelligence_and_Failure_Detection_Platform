import styles from './AdministrationSubsectionHeading.module.css'

export interface AdministrationSubsectionHeadingProps {
  title: string
  description?: string
}

/**
 * A subsection heading with no landmark region attached -- mirrors
 * `DashboardSubsectionHeading` exactly (a real `<h3>` preserving heading
 * hierarchy, no nested `<section>` landmark, since a subsection is not an
 * independently navigable area of the page). Used for Platform Overview's
 * "Connected Services" and Data Sources & Integrations' "Connected
 * Systems" so ADM-006's distinction is carried by a real heading, not
 * just paragraph text.
 */
export function AdministrationSubsectionHeading({ title, description }: AdministrationSubsectionHeadingProps) {
  return (
    <div>
      <h3 className={styles.heading}>{title}</h3>
      {description ? <p className={styles.description}>{description}</p> : null}
    </div>
  )
}
