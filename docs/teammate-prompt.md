# Starter prompt for a teammate

Use this when you hand someone a client folder (a zip with `branding/` and `email/` or `ads/`) and
they're starting from nothing. It assumes they use ChatGPT (Work, with a folder connected), Codex, or
Claude Code. Tell them: make a new empty folder on your computer, put the zip in it, open a chat
connected to that folder, and paste the prompt. If it gets too technical, screen-share.

---

Please git clone (or download) https://github.com/oosamarketing/open-marketing.git into the current
working folder, read its `AGENTS.md`, and do the First-run steps yourself (Python 3.11+,
`scripts/setup.sh`, and any brand font the kit names), then come back to me.

There's a zip in this folder with a client's files. Unzip it into `clients/<brand>` and explore it.
Start with its `HANDOFF.md`; it explains what's finished, how I'm expected to use it, and what's
still open with the client. Then read `.claude/skills/email-designer/SKILL.md` and the brand rules in
`clients/<brand>/branding/brand-assets/brand.md`.

Rebuild the finished email from its spec to confirm the tools work here, and compare the result to the
previews that came with it:

    python tools/graphic-designer/emails/build_email.py clients/<brand>/email/<campaign>/<campaign>.spec.json

Once it matches, walk me through the email in order, section by section: show me the picture of each
section, then tell me whether it's one of my editor's native blocks (which file, link and alt text) or a
custom HTML block, and paste that HTML here in the chat so I can copy it. I want to see the whole email
and the code at the same time so I know what I'm looking at. After that I'll ask for edits and new
campaigns, and I'll always expect: the total download size and a rich-or-light choice when it's heavy,
only real reviews, and the brand's rules followed.

---

The agent gets the rest from `AGENTS.md` and the skills. If the folder's `HANDOFF.md` names a licensed
font, the agent should only ask for it when it re-renders a graphic; shipped images already have it.
