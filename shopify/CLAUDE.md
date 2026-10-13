# CLAUDE.md — working on a Shopify store with an AI agent

For a store owner (or whoever looks after the store) and the agent helping them. Two ways in:

1. **Shopify's own theme CLI**: the agent works on the theme's files on your computer and you preview
   the result on your real store before anyone else sees it.
2. **Claude in the browser**: the agent works in the Shopify admin the way a person would, for the
   jobs that live in settings rather than in files.

The point: you can build or reshape a theme with AI instead of paying for a premium one, and the
on-page SEO work that usually waits for a free afternoon can be done with you watching.

There is no code in this folder. Commands below were checked against Shopify's documentation on
2026-10-13; if one fails, read `shopify theme <command> --help` and https://shopify.dev/docs/api/shopify-cli/theme
before trying anything else.

## What is worth asking for

- **New sections and blocks** for the theme editor: a comparison table, a size guide, a row of
  collections with photos, a banner with a countdown, a product page block that shows the other
  colours as photos.
- **New templates**: a different product page for one kind of product, a landing page for a campaign,
  a collection page with its own layout.
- **Your brand, applied**: colours, fonts and spacing changed across the theme's settings so it stops
  looking like the free theme it started as.
- **Small interactive touches**: a sticky add-to-cart bar, a gallery that behaves better on a phone,
  a section that opens and closes.
- **Speed clean-up from a speed report**: give the agent the report and ask what the theme can fix
  (image sizes, things loading before they are needed, leftovers from apps you removed) and what
  belongs to an app and is not the theme's to fix.
- **Search labels and structured data**: page titles and descriptions, image descriptions, and the
  product information search engines read from the page.

What it will not do well without you: taste. Say what you like, show a site you admire, and look at
every preview. Expect a few rounds.

## The safe way to work on a theme

The rule that matters: **the live theme is never the one being edited.** Work happens on a copy;
the owner looks at a preview; only then is anything published.

Needs Node.js 22.12 or newer and Git. Install the CLI once:

```bash
npm install -g @shopify/cli@latest
```

The first command that touches the store asks you to log in. Use the store owner's account, or a
staff or collaborator account that has the **Themes** permission. The person logs in; the agent
never types a password.

1. **See what is there.**
   ```bash
   shopify theme list --store your-store
   ```
2. **Back up first.** Make a copy of the live theme in the store (it asks which theme), and keep it
   untouched.
   ```bash
   shopify theme duplicate
   ```
3. **Pull the theme into a folder** (it asks which theme when you do not name one). Keep that folder
   under Git, so every change can be undone.
   ```bash
   shopify theme pull --store your-store
   ```
4. **Preview while you work.** This uploads your folder as a hidden development theme and gives you a
   local address plus a preview link, with your real products in it. The development theme is
   temporary: Shopify deletes it after seven days without use, and when you log out of the CLI.
   ```bash
   shopify theme dev --store your-store
   ```
5. **Check the code** for mistakes Shopify's own linter knows about.
   ```bash
   shopify theme check
   ```
6. **Put the result in the store as an unpublished theme.** It sits in the theme library next to the
   live one, with a preview link you can send to someone.
   ```bash
   shopify theme push --unpublished --theme "Spring refresh"
   ```
7. **Publish, when the owner says so.** The command asks for confirmation. The theme that was live
   stays in the theme library, so it can be published again.
   ```bash
   shopify theme publish
   ```

A store on the Basic, Grow or Advanced plan holds up to 20 themes (Plus: 100), so old copies have to
be removed now and then; development themes do not count.

## Claude in the browser

Some work is not in theme files: the search title and description of each product, collection and
page, image descriptions, redirects when a web address changes, navigation, what an app shows. Claude
can do this in the Shopify admin through the browser: it reads the page, clicks, types and fills in
forms, and you see every step. With Claude in Chrome it works in your own browser where you are
already signed in. See https://claude.com/claude-in-chrome and
https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely (paid plans; features and
limits change, so check those pages).

Good browser jobs: "go through these twenty products and propose a search title and description for
each, show me the list, then save the ones I approve", "find images with no description and write
one from what the picture shows", "show me what my product page tells search engines today, and what is
missing".

Keep it safe: Anthropic says plainly that an agent in a browser can be misled by text hidden in a
page, and advises against using it around passwords, payments and other people's personal data. So
keep it on the theme, product, collection, page and navigation screens. Not orders, customers,
payments, billing or staff settings. A staff account with only the permissions the job needs is
better than the owner's.

## Rules for the agent

- **Never push to, develop on, or publish over the live theme.** Do not use `--live`, `--allow-live`
  or `--publish`. Publishing is the owner's step, each time, said in the moment.
- **Never delete a theme**, and never remove the backup copy.
- **Never type or store a password, a Theme Access password or a token.** Log-ins are the user's.
- **Read before writing.** Look at how the theme already names and builds things and follow it. Leave
  app blocks and app code alone unless the user asks, and do not touch checkout.
- **One change at a time**, each with a preview link, each a Git commit.
- **Look at your own work first**: at phone width and desktop width, on a product with long names and
  one with few photos. Then ask the user to open the preview **on a real phone**; an emulated one
  misses things.
- **Copy and claims come from the store.** Do not invent a review, a certification, a price or a
  delivery promise for a banner or a search description.
- **In the admin, propose before saving.** Show the list of changes; save what was approved; say what
  you changed and where.
- **Say what you could not check.** A speed score, a search ranking and a rich result are not yours
  to promise.

## Before you start: who else works on this store?

If a developer or an agency built the theme, tell them. They may have changes that are not in the
store yet, and a copy made today will not have them. If you are the helper and not the owner, the
owner decides what gets published and when.

## Things to type

- "List the themes in my store, make a backup copy of the live one, and pull it into a folder. Do
  not change the live theme."
- "Add a section to the home page that shows three collections with a photo each, in my brand
  colours. Show me a preview link."
- "Here is my speed report. Tell me what the theme can fix and what is an app's doing, then fix the
  theme part on the copy."
- "Look at my product page on a phone and tell me the three things you would change first."
- "Propose a search title and description for my ten best sellers. Show me the list before saving."
