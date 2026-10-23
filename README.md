# Public media releases

Reviewed, publicly served static files for oyunpiksel.com, bytepusula.com and
perdepop.com. This repository does not contain private archives, unpublished
research, credentials, customer information or API keys.

Deployment targets are the three existing Azure Static Web Apps Free resources.
Only standard GitHub-hosted Ubuntu runners are used; no artifact upload, cache,
larger runner, paid resource creation or billing upgrade is configured.

Pushes to main deploy reviewed packages after checksum and brand/key checks.
The hourly maintenance run removes expired entries from news sitemaps only when
needed. It never rewrites article dates or generates articles. Editorial research
and publication remain a separate reviewed workflow. Website visits are currently
unmeasured; health-check requests are not reader traffic.

Deployment keys must be supplied ONLY as GitHub Actions Secrets. Pull-request
workflows and arbitrary repository contributions cannot access these keys.

The repository variable `DEPLOY_ENABLED` remains unset until all three existing
Azure keys have been installed and verified. This prevents missing-key retries
and scheduled uploads before setup is complete. A prepared repository is not a
successful production deployment.
