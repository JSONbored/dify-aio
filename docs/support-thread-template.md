# Unraid Support Thread Template

This document is the standard template for Unraid forum support threads for JSONbored AIO apps.

Use it for:

- first-time CA submission support threads
- major app relaunches
- future AIO app launches

Do not treat this as marketing copy first. The support thread should primarily help a real Unraid user understand:

1. what the app is
2. why this AIO exists
3. what to expect on first install
4. where to go for help

## Strategy

### One thread per app

Create one dedicated support thread per app.

This is the best fit for CA because:

- each app has a single support destination
- support history stays clean
- search relevance is better
- future updates are easier to post in one place

### Where to post

Preferred destination:

- `Docker Containers` on the Unraid forums

If you cannot post there directly:

- create the thread elsewhere on the Unraid forums
- ask a moderator to move it into the correct section

### What is allowed

Safe and recommended:

- GitHub repo links
- upstream project links
- documentation links
- GitHub Sponsors link
- Ko-fi link
- portfolio / maintainer website link
- LinkedIn / X / Discord / Reddit in a light-touch maintainer section

Avoid:

- referral or affiliate links
- hard-sell language
- explicit “hire me” or contracting solicitation inside the support thread body

If you want consulting or contract-work visibility, put that on your portfolio, GitHub profile, or maintainer website instead of making it part of the support thread CTA.

### Recommended length

Target:

- roughly 250 to 600 words in the first post

That is enough for:

- clarity
- support usefulness
- credibility

Without becoming a wall of text.

### Screenshots

Screenshots are not mandatory, but they are strongly recommended for GUI apps.

Recommended:

- 1 hero screenshot minimum for GUI-heavy apps
- 2 to 3 screenshots max in the first post

Best screenshot types:

- dashboard/home screen
- primary workflow UI
- setup/settings page only if it reduces confusion

For non-GUI apps:

- use a Telegram screenshot, architecture diagram, or setup image only if it actually helps

## Required Information Checklist

Every support thread should include:

- app name
- one-sentence overview
- why this AIO exists
- who it is for
- install notes
- first-boot expectations
- persistence paths
- key limitations
- support scope
- project links

## Strongly Recommended Extras

- screenshots
- upstream project link
- GitHub repo link
- release/update policy note
- tasteful donation links
- small maintainer section

## Tradeoffs

- Updates can lag upstream releases because the AIO packaging has to be tested and republished separately.
- Some advanced upstream configuration paths may stay undocumented or unsupported in the default Unraid template.
- Packaging decisions can differ from the official multi-container deployment guides when the AIO wrapper favors simpler first boot behavior.
- Users depend on the AIO maintainer for packaging fixes, security updates, and catalog refreshes.

## Copy-Paste Template

Replace all placeholders before posting.

```md
# Support: {{APP_NAME}} ({{SHORT_DESCRIPTOR}} for Unraid)

## What this is

{{APP_NAME}} is {{ONE_SENTENCE_APP_DESCRIPTION}}.

This AIO package exists to make {{UPSTREAM_APP_NAME}} easier to install and maintain on Unraid without forcing users to manually translate a multi-container setup, wire extra dependencies, or guess at first-boot defaults.

## Why this AIO exists

This package is designed for Unraid users who want:

- a cleaner first install
- fewer moving parts
- sane defaults for homelab use
- the option to go deeper later if they want advanced overrides

## Who this is for

- Beginners who want the easiest reliable Unraid install path
- Intermediate users who want a cleaner AIO baseline
- Power users who still want access to supported advanced settings

## Tradeoffs

- Updates to {{UPSTREAM_APP_NAME}} may lag while the AIO packaging is validated and rebuilt.
- Some advanced upstream configuration paths may not be exposed in the default Unraid template.
- This packaging may behave differently from the official multi-container deployment guide when the AIO wrapper chooses simpler defaults.
- You are relying on the AIO maintainer for packaging fixes, security patches, and catalog refreshes.

## Quick install notes

- Image: `{{IMAGE_NAME}}`
- Default WebUI: `{{WEBUI_URL_OR_NOTE}}`
- Main appdata path: `{{APPDATA_PATHS}}`
- Required setup fields: `{{REQUIRED_FIELDS}}`

### First boot expectations

{{FIRST_BOOT_EXPECTATIONS}}

## Important limitations / caveats

- {{LIMITATION_1}}
- {{LIMITATION_2}}
- {{LIMITATION_3}}

## Persistence

Important persistent paths:

- `{{PATH_1}}`
- `{{PATH_2}}`
- `{{PATH_3}}`

## Support scope

This thread covers the JSONbored Unraid AIO packaging for {{APP_NAME}}.

For support, please include:

- your Unraid version
- your container template settings that matter to the issue
- relevant container logs
- screenshots if the issue is UI-related
- what you expected to happen vs what actually happened

If the issue appears to be upstream behavior rather than the Unraid packaging layer, I may redirect you to the upstream project as appropriate.

## Links

- Project repo: {{PROJECT_REPO_URL}}
- Upstream project: {{UPSTREAM_URL}}
- Catalog repo: {{CATALOG_REPO_URL}}
- Donations:
  - GitHub Sponsors: {{GITHUB_SPONSORS_URL}}
  - Ko-fi: {{KOFI_URL}}

## About the maintainer

Built and maintained by {{MAINTAINER_NAME}} / JSONbored.

- GitHub: {{GITHUB_PROFILE_URL}}
- Portfolio: {{PORTFOLIO_URL}}
- LinkedIn: {{LINKEDIN_URL}}
- X / Twitter: {{TWITTER_URL}}

If this AIO saves you time, support is appreciated. The main goal here is making powerful self-hosted software easier to run well on Unraid.
```

## Posting Notes

After posting:

1. save the final thread URL
2. update the app XML `<Support>` field to that URL
3. sync the XML into `awesome-unraid`
4. only then submit or refresh the CA catalog state

## Drafting Rules For Automation

If this template is later used by automation:

- never invent social URLs
- use placeholders when data is missing
- never include contracting solicitation in the support-thread CTA
- keep the tone helpful and support-oriented, not salesy
- bias toward short, readable first posts instead of long essays
