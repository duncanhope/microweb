"""Reference pages the harness shoots, grouped by template family.

Seeded from the 21 Bootstrap 3 "before" pages (research/before-screenshots
capture.mjs) plus signed-in pages for the one harness user (duncs, profile
54446 on lfgss). Each family PR adds its pages here and its interaction
checks to a `*browser_tests.py` module.
"""
from dataclasses import dataclass

# List rows, counted above the fold at 1280 px. Family PRs that change the
# list markup add their Bootstrap 5 selector here, comma separated.
LIST_ROWS = 'ul.list-collection > li, ul.list-profiles > li, ul.mw-rows > li'

HARNESS_PROFILE_ID = 54446
# The harness user's huddle with only itself. Never shoot another huddle:
# the account holds real private messages.
HARNESS_HUDDLE_ID = 3310071
# A comment with a parent and a reply, for the single comment page (BS5-08).
SINGLE_COMMENT_ID = 16297820
# The conversation the comment checks post, edit and delete in, answered from
# a made-up recording: nothing reaches the API (BS5-08).
STUB_WRITE_CONVERSATION_ID = 141600
# The forum whose Mark everything read the lists checks click as the harness
# user (BS5-07): lfgss Social, quiet and without subforums. Never click it on
# another forum or on the home page, which would mark the whole Site read.
HARNESS_MARK_READ_MICROCOSM_ID = 558
# lfgss's "Test event - do not attend" (BS5-11). The RSVP check answers from a
# made-up recording built on it: nothing is written (operator's decision).
RSVP_EVENT_ID = 9667
# lfgss's forum of mostly events, where the event form checks post (BS5-12),
# answered from made-up fixtures: nothing is written (operator's decision).
EVENT_FORUM_ID = 573


@dataclass(frozen=True)
class Page:
    family: str
    host: str
    path: str
    label: str
    covers: str
    # 'modal-signin' opens the sign-in modal and shoots the viewport.
    action: str = ''
    # Needs HARNESS_TOKEN; skipped when it is unset.
    signed_in: bool = False
    # Selector for list rows; empty for pages that are not lists.
    rows: str = ''

    @property
    def url(self):
        return 'https://%s%s' % (self.host, self.path)


LFGSS = 'www.lfgss.com'

PAGES = [
    Page('forum-lists', LFGSS, '/', 'home', 'microcosm list, pinned rows, metabar', rows=LIST_ROWS),
    Page('forum-lists', LFGSS, '/microcosms/509/', 'microcosm', 'a microcosm listing', rows=LIST_ROWS),
    Page('forum-lists', LFGSS, '/microcosms/508/', 'microcosm-mixed',
         'subforums, events and conversations in one listing', rows=LIST_ROWS),
    Page('conversations', LFGSS, '/conversations/141600/', 'conv-quotes-embeds', 'nested blockquote, iframes, inline image'),
    Page('conversations', LFGSS, '/conversations/357218/?offset=250', 'conv-code', 'pre > code, inline code (prettify)'),
    Page('conversations', LFGSS, '/conversations/392730/', 'conv-pre-iframes', 'pre blocks, many iframes'),
    Page('events', LFGSS, '/events/4488/', 'event', 'event header, map, attendees'),
    Page('profiles', LFGSS, '/profiles/47714/', 'profile', 'a profile page'),
    Page('profiles', LFGSS, '/profiles/?top=true', 'profiles', 'people list', rows=LIST_ROWS),
    Page('activity', LFGSS, '/today/', 'today', 'today view', rows=LIST_ROWS),
    Page('activity', LFGSS, '/updates/', 'updates-guest', 'following, as a guest'),
    Page('activity', LFGSS, '/search/?q=bike&defaults=true', 'search', 'search results', rows=LIST_ROWS),
    Page('legal', LFGSS, '/about/terms/', 'legal', 'legal tables and ol[type]'),
    Page('base', LFGSS, '/conversations/141600/', 'modal-signin', 'sign-in modal (opened by Post a reply)', action='modal-signin'),
    Page('forum-lists', 'forum.espruino.com', '/', 'espruino-home', 'background image (center), link #4898AC', rows=LIST_ROWS),
    Page('conversations', 'forum.espruino.com', '/conversations/402253/', 'espruino-conv', 'conversation under a background image'),
    Page('forum-lists', 'csgrupetto.microcosm.app', '/', 'csgrupetto-home', 'background image (cover), subdomain-only', rows=LIST_ROWS),
    Page('conversations', 'csgrupetto.microcosm.app', '/conversations/299873/', 'csgrupetto-conv', 'conversation'),
    Page('forum-lists', 'forum.islington.cc', '/', 'islington-home', 'link #185945 on surround #bfc3c5', rows=LIST_ROWS),
    Page('conversations', 'forum.islington.cc', '/conversations/373697/', 'islington-conv', 'conversation'),
    Page('forum-lists', 'outliers.microcosm.app', '/', 'outliers-home', 'dark surround #171919, link #280fc2', rows=LIST_ROWS),
    Page('conversations', 'outliers.microcosm.app', '/conversations/313928/', 'outliers-conv', 'conversation on a dark surround'),
    # Signed in as the harness user.
    Page('conversations', LFGSS, '/conversations/141600/', 'conv-signedin', 'conversation with the reply box', signed_in=True),
    # The rest of the family (BS5-08). Only GETs: the forms render, nothing is posted.
    Page('conversations', LFGSS, '/comments/%d/' % SINGLE_COMMENT_ID, 'comment-single',
         'a single comment with its parent and reply'),
    Page('conversations', LFGSS, '/comments/%d/' % SINGLE_COMMENT_ID, 'comment-signedin',
         'a single comment signed in: its Reply box opens on load', signed_in=True),
    Page('conversations', LFGSS, '/microcosms/%d/create/conversation/' % HARNESS_MARK_READ_MICROCOSM_ID,
         'conv-create', 'the Post a conversation form', signed_in=True),
    Page('conversations', LFGSS, '/conversations/141600/edit/', 'conv-edit', 'the Edit conversation form',
         signed_in=True),
    Page('huddles', LFGSS, '/huddles/', 'huddles', 'messages list', signed_in=True, rows=LIST_ROWS),
    Page('huddles', LFGSS, '/huddles/%d/' % HARNESS_HUDDLE_ID, 'huddle-self', 'the harness user\'s huddle with itself', signed_in=True),
    Page('profiles', LFGSS, '/profiles/%d/edit/' % HARNESS_PROFILE_ID, 'profile-edit', 'profile edit form', signed_in=True),
    Page('activity', LFGSS, '/updates/', 'updates', 'following, signed in', signed_in=True, rows=LIST_ROWS),
    Page('forum-lists', LFGSS, '/', 'home-signedin', 'home signed in: NEW badges, Actions', signed_in=True,
         rows=LIST_ROWS),
    Page('forum-lists', LFGSS, '/microcosms/%d/' % HARNESS_MARK_READ_MICROCOSM_ID, 'microcosm-signedin',
         'a forum signed in: NEW badges, Follow, Controls', signed_in=True, rows=LIST_ROWS),
    # The rest of the profiles family (BS5-09). Only GETs: the forms render, nothing is posted.
    Page('profiles', LFGSS, '/profiles/%d/' % HARNESS_PROFILE_ID, 'profile-own',
         'the harness user\'s own profile: Edit your Profile, View Ignored', signed_in=True),
    Page('profiles', LFGSS, '/profiles/47714/', 'profile-signedin',
         'someone else\'s profile signed in: Send Message, Follow, Ignore', signed_in=True),
    Page('profiles', LFGSS, '/profiles/?top=true', 'profiles-signedin',
         'people list signed in: send message, Follow the People page', signed_in=True, rows=LIST_ROWS),
    Page('profiles', LFGSS, '/updates/settings/', 'update-settings', 'the notification settings form',
         signed_in=True),
    Page('profiles', LFGSS, '/ignored/', 'ignored', 'the harness user\'s ignored items', signed_in=True,
         rows=LIST_ROWS),
    Page('profiles', 'csgrupetto.microcosm.app', '/profiles/?top=true', 'csgrupetto-profiles',
         'people list under a background image (cover)', rows=LIST_ROWS),
    # The rest of the activity family (BS5-10). Search always carries
    # defaults=true or inTitle: a bare ?q= on a common word is a 500 from the
    # API ("Too many results"). The watchers page has no URL (updates/urls.py),
    # so it is rendered by the unit tests only.
    Page('activity', LFGSS, '/trending/', 'trending', 'the 25 hottest items', rows=LIST_ROWS),
    Page('activity', LFGSS, '/today/', 'today-signedin', 'today signed in: the Following filter, messages',
         signed_in=True, rows=LIST_ROWS),
    Page('activity', LFGSS, '/search/?type=event&eventAfter=0&sort=oldest', 'search-events',
         'event search: Popular Searches, event filters, the no-results state'),
    Page('activity', LFGSS, '/search/?q=bike&defaults=true', 'search-signedin',
         'search results signed in: the Messages and Following filters', signed_in=True, rows=LIST_ROWS),
    Page('activity', 'forum.islington.cc', '/today/', 'islington-today',
         'Today on a quiet Site: link #185945 on surround #bfc3c5'),
    Page('activity', 'forum.islington.cc', '/search/?q=ride&defaults=true', 'islington-search',
         'search results under Islington CC branding', rows=LIST_ROWS),
    # The rest of the events family (BS5-11). Only GETs: the RSVP check answers
    # its write from made-up fixtures (core/harness/events_browser_tests.py).
    Page('events', LFGSS, '/events/4488/?offset=25', 'event-later', 'a later comment page: the small event header'),
    Page('events', LFGSS, '/events/10110/', 'event-limit', 'an RSVP limit: the places bar, a map, nobody going'),
    Page('events', LFGSS, '/events/%d/' % RSVP_EVENT_ID, 'event-no-place',
         'the test event: no map, the small header, three going'),
    Page('events', LFGSS, '/microcosms/573/', 'event-list', 'an event list: a forum of mostly events', rows=LIST_ROWS),
    Page('events', LFGSS, '/events/4488/', 'event-signedin', 'an event signed in: reply box, Follow, Controls',
         signed_in=True),
    Page('events', LFGSS, '/events/%d/' % RSVP_EVENT_ID, 'event-rsvp-signedin',
         'the test event signed in: the base of the made-up RSVP', signed_in=True),
    Page('events', 'forum.espruino.com', '/events/613/', 'espruino-event',
         'a three-day event with a map under a background image, link #4898AC'),
    # The event form (BS5-12). Only GETs: the harness user has no event of its
    # own, and the edit form renders any event it can read. Posting either form
    # is answered from made-up fixtures (core/harness/event_form_browser_tests.py).
    Page('event_form', LFGSS, '/microcosms/%d/create/event/' % EVENT_FORUM_ID, 'event-create',
         'the Post an event form: dates, time zone, map, RSVP limit, invites, first comment', signed_in=True),
    Page('event_form', LFGSS, '/events/4488/edit/', 'event-edit',
         'the Edit event form: a place on the map and 26 people with an RSVP', signed_in=True),
    # The Bootstrap 5 base (BS5-05). Until a family migrates, these render on
    # Bootstrap 3 on both sides; a local scratch copy of legal.html in
    # core/templates_bs5/ puts the new base under them. The browser checks in
    # core/harness/base_browser_tests.py bring their own page.
    Page('base', LFGSS, '/about/terms/', 'base-guest', 'the base as a guest: header, navbar, footer, drawers'),
    Page('base', LFGSS, '/about/terms/', 'base-member', 'the base signed in: account box, messages badge', signed_in=True),
    Page('base', 'forum.espruino.com', '/about/terms/', 'base-espruino', 'the base under a background image, link #4898AC'),
    # Site branding under each Color mode (BS5-06).
    Page('base', 'forum.winslowwheelers.co.uk', '/about/terms/', 'base-wwcc',
         'wwcc: link #21201b, adjusted to AA in dark; surround #2c7ede'),
    Page('base', 'lesperitdelbikepacking.microcosm.app', '/about/terms/', 'base-lesperit',
         'link #51a9ff exact in light, on a black surround; its home is 403 for guests'),
    Page('base', 'outliers.microcosm.app', '/about/terms/', 'base-outliers',
         'the base on a dark surround #171919, link #280fc2'),
]

# URLs the interaction checks visit beyond PAGES. `shoot --record` fetches
# them too, so `test --tag browser` replays from the same recording.
CHECK_URLS = [
    'https://%s/microcosms/509/?offset=50' % LFGSS,
    # The people list filtered by Online now, as filters.js asks for it (BS5-09).
    'https://%s/profiles/?online=true&top=true' % LFGSS,
    # Search filters as js/bs5/search.js asks for them (BS5-10): conversations
    # only, then the same with the navbar's new words kept on the search page.
    'https://%s/search/?q=bike&type=conversation&inTitle=true&sort=date' % LFGSS,
    'https://%s/search/?q=wheel&inTitle=true&sort=date' % LFGSS,
]

FAMILIES = sorted({p.family for p in PAGES})
# Other names for a family: the plan calls forum-lists "lists" (BS5-07).
ALIASES = {'lists': 'forum-lists'}


def pages_for(family):
    if family == 'all':
        return list(PAGES)
    family = ALIASES.get(family, family)
    pages = [p for p in PAGES if p.family == family]
    if not pages:
        raise ValueError('Unknown family %r. Known: all, %s' % (family, ', '.join(FAMILIES + sorted(ALIASES))))
    return pages


def site_hosts():
    return sorted({p.host for p in PAGES})
