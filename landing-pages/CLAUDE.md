# CLAUDE.md — a landing page, designed and built with an AI agent

For someone who needs one page for one offer (a product launch, a sign-up, a campaign an ad points
at) and the agent helping them. The suggestion: **design the page first in Claude Design, then have
Claude build it with Next.js.**

**What this guide leaves out: putting the page online.** Hosting, a domain, where a form's entries
go, analytics and cookie notices are a further step, and not a small one. This guide ends with a
finished page running on your own computer. Say so to the user at the start, so nobody expects a
link they can send to customers at the end.

There is no code in this folder. Product details below were checked against Anthropic's and
Next.js's own documentation on 2026-10-13; both change, so check the linked pages.

## Step 1: design it in Claude Design

Claude Design is Anthropic's tool for making designs, interactive prototypes and one-pagers by
talking to Claude. You start it from a Claude conversation by asking for a design. When the design
is right, it can be handed to Claude Code, which carries on from the design itself rather than from
a screenshot of it. It draws on the same usage limits as the rest of your Claude plan, and it has no
version history yet, so keep a copy of a version you like.
[Get started with Claude Design](https://support.claude.com/en/articles/14604416-get-started-with-claude-design) ·
[Product page](https://claude.com/product/design)

Design first because it is the cheap place to change your mind. Settle these before any code:

- **The offer, in one sentence.** What someone gets and why now.
- **The one action.** Buy, book, sign up or ask: one of them. Every section either leads to it or
  goes.
- **The proof you really have.** Photos, a real review, a number you can stand behind.
- **Your brand.** Colours, fonts, logo, the way you talk. If there is a brand kit, hand it over.

## Step 2: have Claude build it with Next.js

Next.js is a widely used way to build websites that load fast. Why it suits a landing page: it sizes
and lazy-loads images for each device, loads fonts without the page jumping, and has a set place for
the page's title, description and the picture shown when the link is shared.
[Next.js docs](https://nextjs.org/docs)

It needs Node.js 20.9 or newer. The agent runs these; you watch the result in your browser:

```bash
npx create-next-app@latest my-landing-page
```

```bash
npm run dev
```

The page is then at `http://localhost:3000`, on your computer only. Before calling it finished, the
agent makes the real build and runs that, because the development version is slower and more
forgiving than the real thing:

```bash
npm run build
```

```bash
npm run start
```

## How to judge the result

Four things, in this order. Look at each on your own phone-sized window and at full width.

1. **A clear offer.** Within the first screen, without scrolling, a stranger can say what this is
   and who it is for. Read the headline to someone outside the business.
2. **One action.** One button, repeated, always saying the same thing. No menu of other places to
   go. If there is a form, it asks for as little as you can live with.
3. **Fast.** The first screen appears at once and nothing jumps as it loads. Photos are the usual
   cause when it does not; they should go through Next.js's image component at the size shown.
4. **Works on a phone.** Text readable without zooming, buttons a thumb can hit, nothing wider than
   the screen, the action reachable without hunting.

## Rules for the agent

- **Say at the start that this ends at a page on the user's computer.** Do not deploy it, sign up
  for a hosting service, connect a domain or push the code anywhere. If the user asks, say that is
  the part this guide leaves out and that it needs someone who has done it before.
- **A form that goes nowhere is labelled as one.** Build the form's look and its checks; say plainly
  that entries are not being sent or stored until the page is put online and connected. Never show a
  "thanks, we got it" for a submission that went nowhere.
- **Copy, claims and proof come from the user.** No invented reviews, customer logos, counts,
  awards, prices or deadlines, and no "as seen in". A placeholder is visibly a placeholder.
- **Pictures are the user's**, or clearly marked stand-ins until theirs arrive.
- **Follow the design.** Colours, fonts and spacing come from the design and the brand, not from
  defaults. Where the design could not be followed, say where and why.
- **Look at your own work first**, at phone width and desktop width, on the real build, before
  showing it. Then show screenshots of both.
- **Set the page's title, description and share picture.** A landing page is shared as a link.
- **Keep the project in the user's own folder** and tell them where it is. Install nothing beyond
  what `create-next-app` sets up without saying what and why.
- **Never ask for or type a password or a key.**

## Things to type

- "Design a landing page for our new 32 oz bottle: one offer, one button. Here is our brand kit."
- "The design is approved. Build it with Next.js and show me how it looks on a phone and on a
  laptop."
- "Read the page as a stranger would and tell me what is unclear in the first screen."
- "Make the real build and tell me what is slowing the first screen down."
