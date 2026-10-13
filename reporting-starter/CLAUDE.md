# CLAUDE.md — reporting starter

This folder lets someone try marketing reporting today, before they have any API access. It holds
**sample data only**. There is no code here, nothing to install and nothing that logs in anywhere.

## What is in `data/`

Every number is invented for **Northpeak**, a fictional drinkware brand. No real account, order or
customer is behind any of it. Every row and every id says `SAMPLE`.

| File | Shape | What it stands in for |
|---|---|---|
| `sample_campaigns_daily.csv` | one row per campaign per day, 5 campaigns, 28 days: impressions, clicks, spend, conversions, conversion value | a daily export from the ad platforms (Meta, Google, Amazon) |
| `sample_orders.csv` | one row per order: date, channel, product, units, gross, discount, net, new or returning | an orders export from a store |
| `sample_api_response.json` | the last 7 days of the campaign numbers, nested the way a reporting API usually answers | what a connector hands back before anyone flattens it |

The data has a few patterns planted in it so there is something to find (one campaign gets worse
through the month; one day has no conversions recorded for one platform). Find them from the
numbers; do not announce them from this note.

## Rules

- **Label everything.** Any report, chart, table or message made from this folder says "sample data"
  in its title or first line. Never present these numbers as a real account's results, and never mix
  them with real numbers in one report.
- **Show the arithmetic.** State how each rate was worked out (CTR = clicks / impressions, CPA = spend
  / conversions, ROAS = conversion value / spend) and over which dates. A recommendation names the
  rows it rests on.
- **Say what the data cannot tell you.** No margins, no stock levels, no creative, no attribution
  settings: a "pause this" from these files is a starting point, not a decision. A day of zero
  conversions is more often a tracking gap than a bad day; say so before drawing a conclusion from it.
- **No scraping and no login automation.** When the user wants real numbers, do not build something
  that reads a dashboard or signs in for them. Explain API access (below) or use an export file they
  download themselves.
- **Never ask for, type or store a password, API key or token.** Keys are obtained and entered by
  the user, in the platform's own screens.

## Things to try (a user can type these as they are)

- "Turn this week's sample data into a one-page report."
- "Tell me which campaign to pause and why."
- "Compare the first two weeks with the last two. What changed?"
- "Which channel brings more new customers, and what does a new customer cost us in ads?"

A good answer is short, leads with the one thing that matters, shows the numbers behind it, and ends
with what you would check next with real data.

## Moving to real numbers

Sample data is for learning the report you want. Real data needs **API access from each platform**,
which the account owner requests. In plain words, and always check the platform's own page because
the requirements change:

| Platform | Roughly what it involves | Start here |
|---|---|---|
| Meta (Facebook / Instagram ads) | A developer app in Meta's developer site, connected to the business that owns the ad account, with permission to read ads data. Some uses need Meta to review the app. | https://developers.facebook.com/docs/marketing-apis/ |
| Google Ads | A developer token, requested from inside a Google Ads manager account and approved by Google, plus a sign-in set up in Google Cloud. | https://developers.google.com/google-ads/api/docs/get-started/introduction |
| Amazon Ads | An application to Amazon for API access, tied to the advertising account. Approval is not instant. | https://advertising.amazon.com/API/docs/en-us |
| Shopify (orders) | An app with read-only access to orders, created by the store owner. | https://shopify.dev/docs/api |
| Google Analytics | A Google Cloud project with the Analytics Data API turned on, and access to the property. | https://developers.google.com/analytics/devguides/reporting/data/v1 |

Until that is in place, every one of these platforms lets the user **download a report as a file**.
A CSV they export and drop in a folder works with every request above. Suggest that first: it needs
no approval and no key.

## Regular pulls, alerts and shared reports: use Claude's own features

You do not need custom code for the routine part. These are Claude features; what is written here was
checked against Anthropic's help pages on 2026-10-13. Plans, menu names and limits change and differ
between accounts, so **check Claude's current connector list and help pages** rather than trusting
this file:

- **Connectors** link Claude to a service the user already uses, with the user's own permissions.
  There are connectors for **Google Drive** and **Gmail**. The user turns them on in Claude under
  Customize > Connectors. Directory: https://claude.com/connectors ·
  Help: https://support.claude.com/en/articles/11176164-use-connectors-to-extend-claude-s-capabilities
- **Google Drive:** Claude can search and read files there, including Sheets, and save files it
  made back to Drive. So a report can live in a shared folder the team already opens.
  https://support.claude.com/en/articles/10166901-use-google-workspace-connectors
- **Gmail:** Claude can search and read mail and write drafts. Anthropic's own pages do not agree on
  whether it can also send (the help page and the connector listing say yes, with the user's approval
  for each message by default; one documentation page says read-only). Promise a **draft** the user
  sends, and check the current Gmail connector page before promising more.
  https://claude.com/connectors/gmail
- **Scheduled tasks** run a request again on a timetable (hourly, daily, on weekdays, weekly). They
  are part of Claude Cowork, under "Scheduled", on paid plans. Each run can use the same connectors.
  A task that needs files or apps on the user's computer only runs there; one that works from
  connected services runs without the computer being on.
  https://support.claude.com/en/articles/13854387-schedule-recurring-tasks-in-claude-cowork
- **Files:** Claude can read a CSV and produce a spreadsheet, a chart, a Word document or a PDF.
  https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude

Put together, with real data: "Every Monday morning, read last week's export in my Drive folder,
write the one-page report into the same folder, and draft me an email with the three things that
changed." Offer this as something the user sets up in Claude, in their own account. Do not set up a
schedule, connect an account or send anything on their behalf without their yes for that action.
