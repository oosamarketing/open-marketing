---
name: blogpost
description: Plan, write and check a blog post or article for a brand's own site, with no tool to install — decide whether the post belongs on this site at all, aim the page at one keyword, include a real photo, give an honest read of whether it sounds like the owner, and after publishing check the live page (title, description, headings, alt text, structured data, that it can be indexed). Use this whenever the user asks for a blog post, an article, a guide or "content" for their site, wants an existing post improved, asks which keyword to target, or asks whether a post reads as AI-written.
---

# A blog post worth publishing

There is no code in this skill. It is a way of working, in this order. Google's guidance below was
checked against Google Search Central on 2026-10-13; read the linked page when a detail matters.

## 1. Does this post belong on this brand's site?

Decide this before a word is written. Google's own test for content is whether it was made to help
people or made to pull in search visits, and it describes what it looks for as **E-E-A-T:
experience, expertise, authoritativeness and trust**, with trust the one that matters most. Google
also says E-E-A-T is not a ranking factor in itself; it is a description of content that deserves to
rank. [Creating helpful, reliable, people-first content](https://developers.google.com/search/docs/fundamentals/creating-helpful-content)

Ask, and write the answers down:

- **Experience:** has this brand actually done, made, sold or used the thing the post is about? What
  can it say that someone who has not could not?
- **Expertise:** who at the brand knows this, and will their name be on it?
- **Authority:** is this a subject people would expect this brand to speak on? A drinkware brand on
  keeping drinks cold: yes. The same brand on tax law: no.
- **Trust:** can every fact in it be checked, and is it clear who wrote it and how?

Google frames the same thing as three questions: **who** made it, **how** it was made, and **why**.
If the honest answer to "why" is "to rank for a search", stop and tell the user. The post that
belongs is the one the brand would still want its customers to read if search engines did not exist.

## 2. One keyword per page

A house rule, not Google's: **each post aims at one search, and each search has one page on the
site.** Google publishes no rule about how many keywords a page should have; it says its systems
understand what a page is about without exact phrases, that the keywords meta tag is ignored, and
that packing a page with keywords is spam. The rule is here for discipline: one clear subject per
page, and no two pages of the same site competing for the same search.

- Pick the phrase a customer would really type. Ask the user what customers ask them.
- Check the site first: if a page already answers it, improve that page instead of adding one.
- Use the phrase where a reader expects it: the title, the main heading, early in the text. Then
  write normally. Do not repeat it to hit a count; there is no count.

## 3. Write it from what the brand knows

- Get the raw material from the owner: what they have seen, a customer's question, numbers they can
  stand behind, a mistake they made. That is the experience no one else has.
- **Every fact is checked before it is published.** Google's guidance on AI-written content says the
  same: a model predicts words, it does not look facts up. Claims, prices, results and quotes come
  from the brand's site, its files or the user. Never invent one.
- Put a real person's name on it, with a line about who they are. Do not invent an author.
  [Using generative AI content](https://developers.google.com/search/docs/fundamentals/using-gen-ai-content)

## 4. A photo

Every post gets at least one picture that earns its place: the product in use, the process, the
person, the result. A real photo from the brand beats a stock one. Ask for it rather than generate
it; a generated image is labelled as an illustration, never passed off as a photograph of something
real. Give it alt text that says what it shows, and make it the picture that appears when the post
is shared.

## 5. Does it sound like a person? Use an AI checker honestly

Suggest running the draft through an AI-writing checker, and be straight about what the result is
worth. These checkers are unreliable in both directions: OpenAI withdrew its own for low accuracy
and says that in its experience detectors do not work, sometimes labelling human writing as AI.
[OpenAI's classifier note](https://openai.com/index/new-ai-classifier-for-indicating-ai-written-text/) ·
[OpenAI on detectors](https://help.openai.com/en/articles/8313351-how-can-educators-respond-to-students-presenting-ai-generated-content-as-their-own)

So a score is **a prompt to re-read, not a pass or a fail**:

- A high score means: read it aloud. Where does it sound like nobody in particular? Rewrite those
  parts in the owner's words, with their examples.
- A low score proves nothing about quality, accuracy or whether the post should exist.
- Do not edit a draft to beat a checker. Google does not judge a page by whether a machine helped
  write it; it judges whether the page helps the reader. Rewrite for the reader.

## 6. After it is published, check the live page

Publishing is the user's step, or yours only after they have seen the final version and said yes.
The user signs in to their site themselves; never type, ask for or store a password.

Then open the public page and check what a visitor and a search engine actually get. The `seo` skill
in this toolkit has the detail and the tools; the list for a post:

- **Title and description** are there, specific to this post, and written for a person.
- **Headings**: one main heading that says what the post is; the rest help someone scan.
- **Images** have alt text; the share picture is the right one.
- **Structured data**: Article markup is optional and has no required fields; where the site adds it,
  the headline, image, date and author should match what is on the page. Test the address in the
  Rich Results Test (https://search.google.com/test/rich-results).
  [Article markup](https://developers.google.com/search/docs/appearance/structured-data/article)
- **It can be indexed**: no `noindex` on the page, not blocked in `robots.txt`, and the canonical
  address is the post's own. If the user has Search Console, its URL Inspection tool tests the live
  page. [Block indexing](https://developers.google.com/search/docs/crawling-indexing/block-indexing) ·
  [URL Inspection](https://support.google.com/webmasters/answer/9012289)
- **It is linked** from somewhere a reader would look: the blog index, a related product or post.

Tell the user what you checked, what you fixed and what you could not check. Do not promise a
ranking, or when the post will appear in search.

## The caution that goes with all of this

Write useful posts, not posts made to rank. Google's spam policies define scaled content abuse as
pages "generated for the primary purpose of manipulating search rankings and not helping users",
however they are produced, and the first example Google gives is using generative AI to turn out
many pages that add nothing. A site caught by it can rank lower or drop out of search.
[Spam policies](https://developers.google.com/search/docs/essentials/spam-policies)

So: one good post, not twenty. If the user asks for a batch of posts on a list of keywords, say what
this section says, and offer to do the one the brand has the most to say about.

## Things a user can ask

- "I want to write about how to clean a steel bottle. Does that belong on our site, and what should
  the page be aimed at?"
- "Here are my notes and three photos. Draft the post in my voice and tell me which facts you need
  me to confirm."
- "Read this draft and tell me where it sounds like nobody wrote it."
- "The post is live. Check the page and tell me what is missing."
