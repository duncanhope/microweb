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
# The forum whose Mark everything read the lists checks click as the harness
# user (BS5-07): lfgss Social, quiet and without subforums. Never click it on
# another forum or on the home page, which would mark the whole Site read.
HARNESS_MARK_READ_MICROCOSM_ID = 558


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
    Page('huddles', LFGSS, '/huddles/', 'huddles', 'messages list', signed_in=True, rows=LIST_ROWS),
    Page('huddles', LFGSS, '/huddles/%d/' % HARNESS_HUDDLE_ID, 'huddle-self', 'the harness user\'s huddle with itself', signed_in=True),
    Page('profiles', LFGSS, '/profiles/%d/edit/' % HARNESS_PROFILE_ID, 'profile-edit', 'profile edit form', signed_in=True),
    Page('activity', LFGSS, '/updates/', 'updates', 'following, signed in', signed_in=True, rows=LIST_ROWS),
    Page('forum-lists', LFGSS, '/', 'home-signedin', 'home signed in: NEW badges, Actions', signed_in=True,
         rows=LIST_ROWS),
    Page('forum-lists', LFGSS, '/microcosms/%d/' % HARNESS_MARK_READ_MICROCOSM_ID, 'microcosm-signedin',
         'a forum signed in: NEW badges, Follow, Controls', signed_in=True, rows=LIST_ROWS),
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
