"""Interaction checks for the conversations and comments family on Bootstrap 5 (BS5-08).

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages). Every page is asked for
with ?bs=5, so it renders from core/templates_bs5/.

What reaches the API:
- Nothing is written by the conversation checks. Posting, editing and
  deleting a comment in conversation manifest.STUB_WRITE_CONVERSATION_ID is
  answered from a recording this module makes up from the base recording
  (CommentLifecycleTests), so it runs in replay mode only.
- HuddleCommentTests posts, edits and deletes one comment in the harness
  user's huddle with itself (manifest.HARNESS_HUDDLE_ID), the only place the
  operator allowed a write. It is recorded once into fixtures/huddle-comment/
  with

      HARNESS_MODE=record HARNESS_WRITE_HUDDLE=3310071 python manage.py test \\
          --tag browser core.harness.conversations_browser_tests.HuddleCommentTests

  and replayed from then on. The API does not let anyone delete a huddle
  comment, so each recording leaves one comment in that huddle: record once.
- The mentions check asks the Site's API for profiles from the browser.
  Record that once with HARNESS_MODE=record (a GET) and it replays from the HAR.
"""
import copy
import json
import os
import shutil
import tempfile
import time
from urllib.parse import parse_qs, urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase
from core.harness.lists_browser_tests import OverlayRecording

LFGSS = manifest.LFGSS
ISLINGTON = 'forum.islington.cc'
CONVERSATION = '/conversations/141600/'
LFGSS_API = 'https://lfgss.microcosm.app/api/v1'
COMMENT_BODY = '.mw-comments > .mw-comment .mw-comment-body'
REPLY_BOX = '[data-mw-reply-default] textarea'


class ConversationsTestCase(BrowserTestCase):
    """Family pages open with BrowserTestCase.open_bs5."""

    def assert_on_bs5(self, page):
        self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'), 'not the Bootstrap 5 base')

    def wait_for_scripts(self, page):
        """comments.js and simpleEditor.js are modules: wait until they have wired the boxes."""
        page.wait_for_function('() => [...document.querySelectorAll("[data-mw-editor]")].every(e => e.mwEditor)')


class Bs5ConversationPagesTests(ConversationsTestCase):

    def test_every_conversations_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('conversations'):
            with self.subTest(page=p.label):
                page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in)
                self.assert_on_bs5(page)
                self.assertTrue(page.locator('.mw-comment, .mw-item-form').first.is_visible())
                page.context.close()


class QuoteReplyTests(ConversationsTestCase):
    """Lane 7: select comment text, then Post a reply or Reply quotes it."""

    def select(self, page, index):
        body = page.locator(COMMENT_BODY).nth(index).locator('p').first
        body.select_text()
        return page.evaluate('() => getSelection().toString().trim()')

    def test_post_a_reply_quotes_the_selection(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        text = self.select(page, 0)
        self.assertTrue(text)
        page.locator('#post-a-reply-handle').click()
        box = page.locator(REPLY_BOX)
        self.assertEqual(box.input_value(), '> %s\n\n' % text)
        self.assertTrue(box.evaluate('el => el === document.activeElement'))
        self.assertTrue(page.url.endswith('#reply'))
        self.assertTrue(page.locator('[data-mw-reply-default]').evaluate(
            'el => el.getBoundingClientRect().top < innerHeight'), 'the reply box is scrolled into view')
        self.snap(page, 'BS5-08-check-a')

        # A second quote goes after what is there, never over it.
        second = self.select(page, 1)
        page.locator('#post-a-reply-handle').click()
        self.assertEqual(box.input_value(), '> %s\n\n> %s\n\n' % (text, second))

    def test_reply_opens_a_box_under_the_comment_with_the_quote(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        comment = page.locator('.mw-comments > .mw-comment').nth(2)
        text = self.select(page, 2)
        reply = comment.get_by_role('button', name='Reply', exact=True)
        reply.click()
        box = comment.locator('.mw-comment-box')
        textarea = box.locator('textarea')
        self.assertEqual(textarea.input_value(), '> %s\n\n' % text)
        self.assertTrue(textarea.evaluate('el => el === document.activeElement'))
        self.assertEqual(reply.get_attribute('aria-expanded'), 'true')
        form = box.locator('form')
        self.assertEqual(form.get_attribute('action'), '/comments/create/')
        comment_id = comment.get_attribute('id').removeprefix('comment')
        self.assertEqual(form.locator('input[name=inReplyTo]').input_value(), comment_id)
        self.assertEqual(form.locator('input[name=itemType]').input_value(), 'conversation')
        self.assertEqual(form.locator('input[name=itemId]').input_value(), '141600')
        self.assertFalse(page.locator('[data-mw-reply-default]').is_visible(), 'the foot reply box stays while a reply is open')
        self.snap(page, 'BS5-08-check-a-reply')

        # Another comment's Reply moves the one box there; Cancel closes it.
        other = page.locator('.mw-comments > .mw-comment').nth(4)
        page.evaluate('() => getSelection().removeAllRanges()')
        other.get_by_role('button', name='Reply', exact=True).click()
        self.assertEqual(page.locator('.mw-comment-box').count(), 1)
        self.assertEqual(other.locator('.mw-comment-box textarea').input_value(), '')
        self.assertEqual(reply.get_attribute('aria-expanded'), 'false')
        other.get_by_role('button', name='Cancel').click()
        self.assertEqual(page.locator('.mw-comment-box').count(), 0)
        self.assertTrue(page.locator('[data-mw-reply-default]').is_visible())

        # Clicking Reply again closes its box.
        reply.click()
        self.assertEqual(page.locator('.mw-comment-box').count(), 1)
        reply.click()
        self.assertEqual(page.locator('.mw-comment-box').count(), 0)

    def test_phone_post_a_reply_closes_the_drawer(self):
        page = self.open_bs5(CONVERSATION, signed_in=True, width=375)
        self.wait_for_scripts(page)
        text = self.select(page, 0)
        page.locator('#mw-metabar-btn').click()
        page.locator('#mw-metabar.show').wait_for()
        page.locator('#post-a-reply-handle').click()
        page.locator('#mw-metabar:not(.show)').wait_for(state='attached')
        page.wait_for_function('() => document.activeElement.matches("[data-mw-reply-default] textarea")')
        self.assertEqual(page.locator(REPLY_BOX).input_value(), '> %s\n\n' % text)


class MentionsTests(ConversationsTestCase):
    """Lane 8: @ and two letters list up to five members; arrows move; Enter inserts."""

    def test_mentions_listbox(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        box = page.locator(REPLY_BOX)
        self.assertEqual(box.get_attribute('aria-autocomplete'), 'list')
        listbox_id = box.get_attribute('aria-controls')
        listbox = page.locator('#' + listbox_id)
        self.assertEqual(listbox.get_attribute('role'), 'listbox')

        requests = []
        page.on('request', lambda r: requests.append(r.url) if '/api/v1/profiles' in r.url else None)
        box.click()
        box.press_sequentially('Hello @du', delay=30)
        options = listbox.get_by_role('option')
        options.first.wait_for()
        count = options.count()
        self.assertTrue(1 <= count <= 5, count)
        names = [o.inner_text().strip() for o in options.all()]
        self.assertTrue(all(n.lower().startswith('@du') for n in names), names)
        self.assertEqual(requests[-1], LFGSS_API + '/profiles?disableBoiler&top=true&limit=5&q=du')
        self.assertTrue(listbox.is_visible())
        self.assertEqual(box.get_attribute('aria-activedescendant'), options.nth(0).get_attribute('id'))
        self.assertEqual(page.get_by_role('status').filter(has_text='suggestion').count(), 1)

        if count > 1:
            box.press('ArrowDown')
            self.assertEqual(box.get_attribute('aria-activedescendant'), options.nth(1).get_attribute('id'))
            self.assertEqual(options.nth(1).get_attribute('aria-selected'), 'true')
            self.snap(page, 'BS5-08-check-b')
            box.press('ArrowUp')
        else:
            self.snap(page, 'BS5-08-check-b')
        self.assertEqual(box.get_attribute('aria-activedescendant'), options.nth(0).get_attribute('id'))
        box.press('ArrowUp')  # wraps to the last
        last = count - 1
        self.assertEqual(box.get_attribute('aria-activedescendant'), options.nth(last).get_attribute('id'))
        box.press('Enter')
        self.assertEqual(box.input_value(), 'Hello %s ' % names[last])
        self.assertFalse(listbox.is_visible())
        self.assertIsNone(box.get_attribute('aria-activedescendant'))

        # Escape closes without inserting; the text stays as typed.
        box.press_sequentially('@du', delay=30)
        options.first.wait_for()
        box.press('Escape')
        self.assertFalse(listbox.is_visible())
        self.assertEqual(box.input_value(), 'Hello %s @du' % names[last])
        # An address is not a mention.
        box.fill('mail me at someone@du')
        box.press('End')
        page.wait_for_timeout(400)
        self.assertFalse(listbox.is_visible())

    def test_a_failed_search_does_not_cancel_the_next(self):
        """A search that fails while the next one waits out its debounce
        leaves that one to run."""
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        box = page.locator(REPLY_BOX)
        listbox = page.locator('#' + box.get_attribute('aria-controls'))
        hold_search(page, 'd')
        box.click()
        box.press_sequentially('Hello @d', delay=30)
        page.wait_for_function('() => window.mwFailSearch')
        # Type "u", and fail the search for "d" while the one for "du" waits.
        page.evaluate('''() => {
          document.execCommand('insertText', false, 'u');
          window.mwFailSearch();
        }''')
        options = listbox.get_by_role('option')
        options.first.wait_for(timeout=5000)
        self.assertEqual(page.evaluate('window.mwSearches'), ['d', 'du'])
        names = [o.inner_text().strip() for o in options.all()]
        self.assertTrue(all(n.lower().startswith('@du') for n in names), names)
        self.assertEqual(box.get_attribute('aria-activedescendant'), options.nth(0).get_attribute('id'))


def hold_search(page, term):
    """Make the page's member search for term wait until the check calls
    window.mwFailSearch(), then fail with a 500. Other searches go through,
    and window.mwSearches lists every term searched for."""
    page.evaluate('''(held) => {
      const fetch = window.fetch;
      window.mwSearches = [];
      window.fetch = (url, options) => {
        const term = new URL(url, location.href).searchParams.get('q');
        if (!String(url).includes('/api/v1/profiles')) return fetch(url, options);
        window.mwSearches.push(term);
        if (term !== held) return fetch(url, options);
        return new Promise((resolve) => {
          window.mwFailSearch = () => resolve(new Response('{}', { status: 500 }));
        });
      };
    }''', term)


class EditorTests(ConversationsTestCase):
    """The formatting toolbar, Preview, the help modal, the check before posting and attachments."""

    def test_toolbar_and_shortcuts(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        box = page.locator(REPLY_BOX)
        toolbar = page.locator('[data-mw-reply-default] .mw-editor-toolbar')

        def run(start_text, select, button=None, key=None):
            box.fill(start_text)
            box.evaluate('(el, [s, e]) => el.setSelectionRange(s, e)', select)
            if button:
                toolbar.get_by_role('button', name=button).click()
            else:
                box.press(key)
            return box.input_value(), box.evaluate('el => [el.selectionStart, el.selectionEnd]')

        self.assertEqual(run('make this bold', [5, 9], 'Bold'), ('make **this** bold', [7, 11]))
        self.assertEqual(run('make **this** bold', [7, 11], 'Bold'), ('make this bold', [5, 9]))
        self.assertEqual(run('lean', [0, 4], key='Control+i'), ('*lean*', [1, 5]))
        self.assertEqual(run('', [0, 0], 'Bold'), ('**strong text**', [2, 13]))
        self.assertEqual(run('one\ntwo', [0, 7], 'Quote'), ('> one\n> two', [0, 11]))
        self.assertEqual(run('> one\n> two', [0, 11], 'Quote')[0], 'one\ntwo')
        self.assertEqual(run('Intro\none\ntwo', [6, 13], 'List')[0], 'Intro\n\n1. one\n2. two')
        self.assertEqual(run('x = 1', [0, 5], 'Code')[0], '```\nx = 1\n```')
        page.once('dialog', lambda d: d.accept('https://example.com/'))
        self.assertEqual(run('see here', [4, 8], 'Link')[0], 'see [here](https://example.com/)')
        page.once('dialog', lambda d: d.accept('https://example.com/a.png'))
        self.assertEqual(run('', [0, 0], key='Control+g')[0], '![](https://example.com/a.png)')
        page.once('dialog', lambda d: d.dismiss())
        self.assertEqual(run('unchanged', [0, 9], 'Link')[0], 'unchanged')

        # Undo is the browser's own.
        box.fill('word')
        box.evaluate('el => el.setSelectionRange(0, 4)')
        toolbar.get_by_role('button', name='Bold').click()
        box.press('Control+z')
        self.assertEqual(box.input_value(), 'word')

    def test_preview_and_help(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        box = page.locator(REPLY_BOX)
        box.fill('**Loud** and <img src="/static/img/avatar.gif" onerror="window.pwned=1"> [a](javascript:alert(1))')
        preview = page.locator('[data-mw-reply-default] [data-mw-preview]')
        preview.click()
        body = page.locator('[data-mw-reply-default] [data-mw-preview-body]')
        body.locator('strong').wait_for()
        self.assertEqual(body.locator('strong').inner_text(), 'Loud')
        self.assertEqual(preview.get_attribute('aria-pressed'), 'true')
        self.assertFalse(box.is_visible())
        self.assertIsNone(page.evaluate('window.pwned'))
        self.assertIsNone(body.locator('img').get_attribute('onerror'))
        self.assertFalse((body.locator('a').get_attribute('href') or '').lower().startswith('javascript:'))
        self.snap(page, 'conversations-preview')
        preview.click()
        self.assertTrue(box.is_visible())
        self.assertEqual(preview.get_attribute('aria-pressed'), 'false')

        page.get_by_role('button', name='Formatting help').click()
        modal = page.locator('#formatting-help-modal')
        page.locator('#formatting-help-modal.show').wait_for()
        self.assertTrue(modal.get_by_role('heading', name='Formatting Help').is_visible())
        self.snap(page, 'conversations-help')
        page.keyboard.press('Escape')
        page.locator('#formatting-help-modal').wait_for(state='hidden')

    def test_empty_reply_is_not_posted(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        posts = []
        page.on('request', lambda r: posts.append(r.url) if r.method == 'POST' else None)
        box = page.locator(REPLY_BOX)
        box.fill('   ')
        page.locator('[data-mw-reply-default]').get_by_role('button', name='Post reply').click()
        self.assertIn('is-invalid', box.get_attribute('class'))
        self.assertTrue(page.locator('[data-mw-reply-default] .invalid-feedback').is_visible())
        self.assertTrue(box.evaluate('el => el === document.activeElement'))
        box.press('Control+Enter')
        page.wait_for_timeout(300)
        self.assertEqual(posts, [])
        box.fill('Now there is text')
        self.assertNotIn('is-invalid', box.get_attribute('class'))

    def test_attachments(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        reply = page.locator('[data-mw-reply-default]')
        field = reply.locator('input[type=file]')
        png = bytes.fromhex('89504e470d0a1a0a0000000d4948445200000001000000010806000000'
                            '1f15c4890000000d49444154789c6360f8cfc0f01f0005000201e5270ade0000000049454e44ae426082')
        field.set_input_files([
            {'name': 'notes.txt', 'mimeType': 'text/plain', 'buffer': b'notes'},
            {'name': 'dot.png', 'mimeType': 'image/png', 'buffer': png},
        ])
        gallery = reply.locator('[data-mw-gallery] > li')
        self.assertEqual(gallery.count(), 2)
        self.assertEqual(gallery.nth(0).get_attribute('class'), 'mw-attachment-image')
        self.assertEqual(gallery.nth(1).inner_text().strip(), 'notes.txt')
        # Picking again adds to the list.
        field.set_input_files([{'name': 'more.txt', 'mimeType': 'text/plain', 'buffer': b'more'}])
        self.assertEqual(field.evaluate('el => [...el.files].map(f => f.name)'), ['notes.txt', 'dot.png', 'more.txt'])
        self.assertEqual(gallery.count(), 3)
        self.snap(page, 'conversations-attachments')

        page.once('dialog', lambda d: d.accept())
        reply.get_by_role('button', name='Remove dot.png').click()
        self.assertEqual(field.evaluate('el => [...el.files].map(f => f.name)'), ['notes.txt', 'more.txt'])
        page.once('dialog', lambda d: d.dismiss())
        reply.get_by_role('button', name='Remove notes.txt').click()
        self.assertEqual(gallery.count(), 2)

        reply.get_by_role('button', name='Cancel').click()
        self.assertEqual(gallery.count(), 0)
        self.assertEqual(field.evaluate('el => el.files.length'), 0)


class GuestAndFormTests(ConversationsTestCase):

    def test_guest_post_a_reply_opens_the_signin_modal(self):
        page = self.open_bs5(CONVERSATION)
        self.assertEqual(page.locator('[data-mw-reply-default] textarea').count(), 0)
        self.assertTrue(page.get_by_role('button', name='Sign in to post a reply').is_visible())
        self.assertTrue(page.locator('.mw-editor-toolbar button').first.is_disabled())
        self.assertEqual(page.locator('[data-mw-reply]').count(), 0, 'guests get no Reply or Edit')
        page.locator('#mw-metabar').get_by_role('button', name='Post a reply').click()
        page.locator('#modal-signin.show').wait_for()
        self.snap(page, 'conversations-guest-post')

    def test_post_a_conversation_form_checks_the_title(self):
        page = self.open_bs5('/microcosms/%d/create/conversation/' % manifest.HARNESS_MARK_READ_MICROCOSM_ID,
                         signed_in=True)
        self.wait_for_scripts(page)
        posts = []
        page.on('request', lambda r: posts.append(r.url) if r.method == 'POST' else None)
        title = page.get_by_label('What is the subject of the conversation?')
        first = page.get_by_label('What is it you want to say?')
        self.assertEqual(first.get_attribute('name'), 'firstcomment')
        page.get_by_role('button', name='Post conversation').click()
        self.assertIn('is-invalid', title.get_attribute('class'))
        self.assertTrue(page.get_by_text('Please add a subject').is_visible())
        self.assertEqual(posts, [])
        # The first comment's box works like the reply box.
        first.fill('bold')
        first.evaluate('el => el.setSelectionRange(0, 4)')
        page.get_by_role('button', name='Bold').click()
        self.assertEqual(first.input_value(), '**bold**')
        self.snap(page, 'conversations-create-form')

    def test_edit_conversation_form_asks_for_a_reason(self):
        page = self.open_bs5('/conversations/141600/edit/', signed_in=True)
        page.wait_for_function('() => document.querySelector("form[data-mw-validate]")')
        title = page.get_by_label('What is the subject of the conversation?')
        self.assertEqual(title.input_value(), 'Youtube Posting')
        posts = []
        page.on('request', lambda r: posts.append(r.url) if r.method == 'POST' else None)
        # simpleEditor.js is a module; wait for it to wire the form.
        page.wait_for_timeout(300)
        page.get_by_role('button', name='Edit conversation').click()
        self.assertIn('is-invalid', page.get_by_label('Reason for editing').get_attribute('class'))
        self.assertEqual(posts, [])


# Colour facts on a conversation: the surround, the content and links.
COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    body: rgb(document.querySelector('.mw-comment-body'), 'color'),
    link: rgb(document.querySelector('.mw-comment-permalink a'), 'color'),
    metabarLink: rgb(document.querySelector('#mw-metabar .mw-module-author a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class IslingtonBrandingTests(ConversationsTestCase):
    """Lane 10: Site branding holds on a conversation in light and dark."""

    def test_islington_conversation_light_and_dark(self):
        site_link = colors.parse_hex('#185945')
        surround = colors.parse_hex('#bfc3c5')
        for mode in ('light', 'dark'):
            with self.subTest(mode=mode):
                page = self.open_bs5('/conversations/373697/', host=ISLINGTON, color_mode=mode)
                facts = page.evaluate(COLOR_FACTS_JS)
                self.assertEqual(facts['theme'], mode)
                self.assertEqual(tuple(facts['surround']), surround, 'the Site surround')
                self.assertEqual(facts['logo'], 89)
                self.assertGreaterEqual(colors.contrast(facts['body'], facts['main']), 7)
                if mode == 'light':
                    self.assertEqual(tuple(facts['link']), site_link)
                    self.assertEqual(tuple(facts['metabarLink']), site_link)
                else:
                    metabar = colors.dark_panel(surround)
                    for name in ('link', 'metabarLink'):
                        self.assertGreaterEqual(colors.contrast(facts[name], facts['main']), colors.AA, name)
                        self.assertGreaterEqual(colors.contrast(facts[name], metabar), colors.AA, name)
                self.snap(page, 'BS5-08-branding-%s' % mode)
                page.context.close()


# ---------------------------------------------------------------------------
# Lane 9: post, edit and delete a comment.

def _fixture(key, status, data, error=None):
    return {'key': key, 'session': 'made-up', 'status': status, 'reason': 'OK', 'headers': {'content-type': 'application/json'},
            'encoding': 'utf-8', 'body': json.dumps({'context': '', 'status': status, 'data': data, 'error': error})}


def _write(folder, record):
    os.makedirs(os.path.join(folder, 'api'), exist_ok=True)
    with open(os.path.join(folder, 'api', recorder.fixture_name(record['key'])), 'w', encoding='utf-8') as f:
        json.dump(record, f)


# The harness forwards https pages to an http server with X-Forwarded-Proto;
# trusting it lets a real form POST pass Django's CSRF origin check.
@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class CommentLifecycleTests(ConversationsTestCase):
    """Post, edit and delete a comment on a conversation, with every API answer
    made up from the base recording: nothing is written anywhere."""

    COMMENT_ID = 99999001
    CONVERSATION_ID = manifest.STUB_WRITE_CONVERSATION_ID

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.stub_dir = tempfile.mkdtemp(prefix='bs5-08-stub-')
        cls.stub_fixtures = os.path.join(cls.stub_dir, 'fixtures')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.stub_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        if self._recorder.mode != recorder.REPLAY:
            self.skipTest('The made-up comment recording runs in replay mode only: it must never reach the API.')
        base = self._recorder.load('GET %s/conversations/%d auth' % (LFGSS_API, self.CONVERSATION_ID))
        if base is None:
            self.skipTest('No signed-in recording of conversation %d. Run shoot --record with HARNESS_TOKEN.'
                          % self.CONVERSATION_ID)
        self.conversation = json.loads(base['body'])['data']
        whoami = json.loads(self._recorder.load('GET %s/whoami auth' % LFGSS_API)['body'])['data']
        self.author = {k: whoami[k] for k in ('id', 'siteId', 'userId', 'profileName', 'visible', 'avatar')}
        self.author['meta'] = {'flags': {}, 'links': []}
        self.make_steps()

    def comment(self, markdown):
        url = '/api/v1/comments/%d' % self.COMMENT_ID
        return {
            'id': self.COMMENT_ID, 'itemType': 'conversation', 'itemId': self.CONVERSATION_ID, 'revisions': 1,
            'markdown': markdown, 'html': '<p>%s</p>\n' % markdown,
            'meta': {
                'created': '2026-09-29T12:00:00Z', 'createdBy': self.author, 'flags': {'deleted': False},
                'links': [{'rel': 'self', 'href': url},
                          {'rel': 'commentPage', 'href': '/api/v1/conversations/%d?offset=0' % self.CONVERSATION_ID},
                          {'rel': 'up', 'href': '/api/v1/conversations/%d' % self.CONVERSATION_ID,
                           'title': self.conversation['title']}],
                'permissions': {'create': True, 'read': True, 'update': True, 'delete': True, 'guest': False,
                                'moderator': False, 'owner': True, 'siteOwner': False},
            },
        }

    def with_comment(self, markdown):
        data = copy.deepcopy(self.conversation)
        data['comments']['items'].append(self.comment(markdown))
        data['comments']['total'] += 1
        return data

    def make_steps(self):
        conversation_key = 'GET %s/conversations/%d auth' % (LFGSS_API, self.CONVERSATION_ID)
        comment_url = '%s/comments/%d' % (LFGSS_API, self.COMMENT_ID)
        posted, edited = 'Posted from the harness', 'Edited from the harness'
        steps = {
            'posted': [_fixture('POST %s/comments auth' % LFGSS_API, 200, self.comment(posted)),
                       _fixture(conversation_key, 200, self.with_comment(posted))],
            'edited': [_fixture('GET %s auth' % comment_url, 200, self.comment(posted)),
                       _fixture('POST %s?method=PUT auth' % comment_url, 200, self.comment(edited)),
                       _fixture(conversation_key, 200, self.with_comment(edited))],
            'deleted': [_fixture('GET %s auth' % comment_url, 200, self.comment(edited)),
                        _fixture('DELETE %s?method=DELETE auth' % comment_url, 200, None)],
        }
        for name, records in steps.items():
            for record in records:
                _write(os.path.join(self.stub_fixtures, name), record)

    def overlay(self, name):
        return OverlayRecording(self._recorder, self.stub_fixtures, name)

    def test_post_edit_and_delete_a_comment(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        self.wait_for_scripts(page)
        sent = []
        page.on('request', lambda r: sent.append((r.url, r.post_data)) if r.method == 'POST' else None)
        anchor = '#comment%d' % self.COMMENT_ID

        # Post.
        with self.overlay('posted'):
            page.locator(REPLY_BOX).fill('Posted from the harness')
            self.submit(page, page.locator('[data-mw-reply-default]').get_by_role('button', name='Post reply').click,
                        '/comments/create/')
            url, body = sent[-1]
            self.assertEqual(urlsplit(url).path, '/comments/create/')
            self.assertIn('name="itemId"\r\n\r\n%d' % self.CONVERSATION_ID, body)
            self.assertIn('name="itemType"\r\n\r\nconversation', body)
            self.assertIn('name="markdown"\r\n\r\nPosted from the harness', body)
            self.assertTrue(page.url.endswith(anchor), page.url)
            posted = page.locator(anchor)
            self.assertEqual(posted.locator('.mw-comment-body').inner_text().strip(), 'Posted from the harness')
            self.assertTrue(posted.get_by_role('button', name='Edit').is_visible())
            self.assertEqual(posted.get_by_role('button', name='Reply').count(), 0, 'no Reply to your own comment')
            self.snap(page, 'BS5-08-signed-in')

        # Edit: the box under the comment loads its Markdown, then saves it.
        with self.overlay('edited'):
            self.wait_for_scripts(page)
            posted = page.locator(anchor)
            posted.get_by_role('button', name='Edit').click()
            textarea = posted.locator('.mw-comment-box textarea')
            page.wait_for_function('(s) => document.querySelector(s).value', arg=anchor + ' .mw-comment-box textarea')
            self.assertEqual(textarea.input_value(), 'Posted from the harness')
            form = posted.locator('.mw-comment-box form')
            self.assertEqual(form.get_attribute('action'), '/comments/%d/edit/' % self.COMMENT_ID)
            self.assertEqual(form.locator('input[name=id]').input_value(), str(self.COMMENT_ID))
            self.snap(page, 'BS5-08-signed-in-edit')
            textarea.fill('Edited from the harness')
            self.submit(page, posted.get_by_role('button', name='Save changes').click,
                        '/comments/%d/edit/' % self.COMMENT_ID)
            url, body = sent[-1]
            self.assertEqual(urlsplit(url).path, '/comments/%d/edit/' % self.COMMENT_ID)
            self.assertIn('name="markdown"\r\n\r\nEdited from the harness', body)
            self.assertEqual(page.locator(anchor + ' .mw-comment-body').inner_text().strip(), 'Edited from the harness')

        # Delete.
        with self.overlay('deleted'):
            self.submit(page, page.locator(anchor).get_by_role('button', name='Delete').click,
                        '/comments/%d/delete/' % self.COMMENT_ID)
            self.assertEqual(urlsplit(sent[-1][0]).path, '/comments/%d/delete/' % self.COMMENT_ID)
            self.assertEqual(urlsplit(page.url).path, CONVERSATION)
            self.assertEqual(page.locator(anchor).count(), 0)

    def test_an_invalid_comment_shows_the_fallback_page_and_writes_nothing(self):
        page = self.open_bs5(CONVERSATION, signed_in=True)
        # Posted from the page, so it goes through the harness routing like a form would.
        status, html = page.evaluate('''async (itemId) => {
          const form = document.querySelector('[data-mw-reply-default] form');
          const body = new FormData(form);
          body.set('markdown', '');
          const response = await fetch('/comments/create/?bs=5', { method: 'POST', body });
          return [response.status, await response.text()];
        }''', str(self.CONVERSATION_ID))
        self.assertEqual(status, 200)
        self.assertIn('bs5.min.css', html)
        self.assertIn('class="alert alert-warning mw-alert"', html)


# The huddle checks answer every write from their own recording, made once.
HUDDLE = '/huddles/%d/' % manifest.HARNESS_HUDDLE_ID
HUDDLE_MARKER = 'BS5-08 harness check, please ignore'


@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class HuddleCommentTests(ConversationsTestCase):
    """Lane 9, live once: post, edit and delete a comment in the harness user's
    huddle with itself, the one place the operator allowed a write.

    The comment is posted from the huddle page's reply box, which is this
    family's comment box on Bootstrap 5 since BS5-13 (it was the Bootstrap 3
    box when this was recorded; the recording only holds API answers). Edit
    runs from the single comment page, comment.html, whose Edit box is the
    same comment box.

    The API refuses to delete a huddle comment, even for its author, so a
    recording leaves its comment behind in the huddle. Record it only once.
    """

    def setUp(self):
        self.recording = os.path.join(self.fixtures_dir, 'huddle-comment')
        if self._recorder.mode == recorder.REPLAY:
            if not os.path.isdir(self.recording):
                self.skipTest('No huddle comment recording in %s. Record it once: HARNESS_MODE=record '
                              'HARNESS_WRITE_HUDDLE=%d python manage.py test --tag browser '
                              'core.harness.conversations_browser_tests.HuddleCommentTests'
                              % (self.recording, manifest.HARNESS_HUDDLE_ID))
        elif os.environ.get('HARNESS_WRITE_HUDDLE') != str(manifest.HARNESS_HUDDLE_ID):
            self.skipTest('Recording writes to the live huddle %d; set HARNESS_WRITE_HUDDLE=%d to allow it.'
                          % (manifest.HARNESS_HUDDLE_ID, manifest.HARNESS_HUDDLE_ID))

    def step(self, name):
        return OverlayRecording(self._recorder, self.fixtures_dir, os.path.join('huddle-comment', name))

    def huddle_comments(self, page):
        return page.evaluate('() => [...document.querySelectorAll("[id^=comment]")].map(e => e.id)')

    def test_post_edit_and_delete_in_the_self_huddle(self):
        page = self.new_page(signed_in=True)
        page.context.add_cookies([{'name': 'bs', 'value': '5', 'url': 'https://%s/' % LFGSS}])
        sent = []
        page.on('request', lambda r: sent.append((r.url, r.post_data)) if r.method == 'POST' else None)
        stamp = time.strftime('%Y-%m-%d %H:%M')

        with self.step('0-before'):
            page.goto('https://%s%s' % (LFGSS, HUDDLE), wait_until='load')
            self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'))
            self.wait_for_scripts(page)
            self.before = self.huddle_comments(page)

        # Post, from the huddle's reply box.
        with self.step('1-posted'):
            form = page.locator('[data-mw-reply-default] form')
            self.assertEqual(form.locator('input[name=itemType]').input_value(), 'huddle')
            self.assertEqual(form.locator('input[name=itemId]').input_value(), str(manifest.HARNESS_HUDDLE_ID))
            form.locator('textarea').fill('%s (%s).' % (HUDDLE_MARKER, stamp))
            self.submit(page, form.get_by_role('button', name='Post reply').click, '/comments/create/')
            self.assertEqual(urlsplit(sent[-1][0]).path, '/comments/create/')
            fragment = urlsplit(page.url).fragment
            self.assertRegex(fragment, r'^comment\d+$')
            self.comment_id = int(fragment.removeprefix('comment'))
            self.assertNotIn(fragment, self.before)
            self.assertIn(HUDDLE_MARKER, page.locator('#' + fragment).inner_text())
            self.snap(page, 'BS5-08-huddle-posted')

        comment_page = 'https://%s/comments/%d/' % (LFGSS, self.comment_id)

        # Edit, from the Bootstrap 5 single comment page: its Edit box opens on load.
        with self.step('2-edited'):
            page.goto(comment_page, wait_until='load')
            self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'))
            box = page.locator('.mw-comments-highlighted .mw-comment-box')
            textarea = box.locator('textarea')
            page.wait_for_function('() => document.querySelector(".mw-comment-box textarea")?.value')
            self.assertIn(HUDDLE_MARKER, textarea.input_value())
            self.assertEqual(box.locator('form').get_attribute('action'), '/comments/%d/edit/' % self.comment_id)
            self.snap(page, 'BS5-08-huddle-edit')
            textarea.fill('%s (%s), edited.' % (HUDDLE_MARKER, stamp))
            self.submit(page, box.get_by_role('button', name='Save changes').click,
                        '/comments/%d/edit/' % self.comment_id)
            self.assertEqual(urlsplit(sent[-1][0]).path, '/comments/%d/edit/' % self.comment_id)
            self.assertEqual(urlsplit(page.url).path, HUDDLE)
            self.assertIn('edited.', page.locator('#comment%d' % self.comment_id).inner_text())

        # Delete: the API gives nobody, not even the author, delete permission
        # on a huddle comment (it answers a DELETE with 403), so the Bootstrap
        # 5 single comment page rightly offers no Delete, as Bootstrap 3 does.
        with self.step('3-deleted'):
            page.goto(comment_page, wait_until='load')
            self.wait_for_scripts(page)
            highlighted = page.locator('.mw-comments-highlighted')
            self.assertTrue(highlighted.get_by_role('button', name='Edit').is_visible())
            self.assertEqual(highlighted.get_by_role('button', name='Delete').count(), 0)
            self.snap(page, 'BS5-08-huddle-no-delete')
