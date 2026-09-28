# Microweb Domain Glossary

This project is the server-rendered Django web client for the Microcosm forum platform. It has no database — all state lives behind the Microcosm REST API. The migration is from Python 2.7 / Django 1.5 (`main` branch) to Python 3.14 / Django 6.0 (`py3-dj6` branch), modernisation only — no new features.

## Terms

**Site** — A single forum community (the tenant). Each Site has its own subdomain or custom domain (CNAME), branding (logo, colours, theme), and an owning Profile. One customer = one Site.

**Microcosm** — A category within a Site. Contains Items (Conversations, Events, Polls). Microcosms can nest via `parentId`, but the browser URL structure is flat (`/microcosms/{id}/`) — hierarchy is shown via breadcrumbs only.

**Conversation** — A discussion thread within a Microcosm. A commentable item.

**Event** — A real-world meetup or calendar occurrence within a Microcosm. Like a Conversation but with a when (date/time), where (geocoded location), and an attendee list with RSVP. A commentable item.

**Poll** — A votable item type. Defined in the API and declared in microweb's resource type lists, but microweb has no views for it currently.

**Comment** — A user-posted message attached to a commentable item (Conversation, Event, Poll, or Huddle). Supports attachments, edit history (revisions), and an `inContext` URL that resolves to the correct page offset within the parent item.

**Huddle** — A private message thread. Multi-party (has a participant list). Commentable like a Conversation but visible only to participants.

**User** — A platform-wide identity. One person has one User across all Sites.

**Profile** — A User's presence on a specific Site. Carries site-local attributes (avatar, bio, permissions). A User has one Profile per Site they participate in.

**Role** — A named permission group scoped to a single Microcosm. Profiles are assigned to Roles to grant or restrict access.

**RoleCriteria** — Rules that auto-assign Profiles to a Role based on matching conditions.

**Watcher** — A Profile's subscription to a specific item (Conversation, Event, or Microcosm). Controls whether the item appears in the "following" feed (`/updates`) and whether email/SMS notifications are sent for new activity.

**Update** — A feed entry generated when a watched item has new activity. The Updates list is the output of the Watcher mechanism — "here's what happened on things you follow."

**Ignored** — A per-Profile mute. Ignoring a Profile hides their posts within existing Conversations. Ignoring a Conversation (or other item) hides it from the feed entirely.

**Trending** — The 25 "hottest" items on the Site, ranked by an activity score using Newton's Law of Cooling: recent comment count as temperature, decayed exponentially by time since last comment, penalised by overall item age.

**Today** — A "what's new since your last visit" view. Displays recently active items (Conversations, Events, Profiles, Huddles) via the Search API with a recency filter.

**Redirect** — Legacy URL resolution for forums imported onto custom domains. When a CNAME request doesn't match any native route, the API is consulted for a mapping from the old platform's URL to the corresponding Microcosm resource. Issues a 301 if found.

**Legal** — Site-configurable policy documents (terms of service, privacy policy, acceptable use, etc.).

**Attachment** — A file uploaded to a Comment or other resource.

## Presentation

**Color mode** — A viewer-facing palette the whole page renders in, such as light or dark. Chosen by the viewer or their system, not by the Site. Custom modes beyond light and dark (for example high contrast) are further Color modes. _Avoid_: theme, colour scheme.

**Site branding** — A Site's own visual identity: logo, favicon, link colour, background colour, and background image with its position. The same in every Color mode; only the link colour may be adjusted so it stays readable. _Avoid_: site style, theme.

**Site theme** — The stylesheet set a Site is assigned by its `themeId`. Distinct from Color mode and from Site branding. _Avoid_: using "theme" alone.
