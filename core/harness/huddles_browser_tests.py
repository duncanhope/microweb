"""Interaction checks for the huddles family on Bootstrap 5 (BS5-13): huddles.html,
huddle.html with its Share and Delete modals, forms/huddle.html, and
peopleWidget.js.

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages). Pages are asked for with
?bs=5, or the bs cookie where a form's redirect must stay on Bootstrap 5.

The harness user's account holds real private messages, so:
- The only real huddle opened is the self-huddle manifest.HARNESS_HUDDLE_ID.
  The Messages list is opened only to check that it renders.
- Everything else runs on made-up huddles (ids from 99999013), answered from
  made-up fixtures in replay mode only: sharing a message, leaving one
  (lane 8: never leave a real huddle, and never the self-huddle), sending a
  new message, and Islington CC's signed-in Messages (lane 10), whose whoami
  is made up too, so no signed-in request reaches another Site.
- Lane 7 types into the Share modal's people widget on the self-huddle and
  never sends. The member search is the mentions check's recorded browser
  GET (conversations_browser_tests.MentionsTests).
- Lane 9 posts one reply in the self-huddle, live, once, recorded into
  fixtures/huddle-reply/ with

      HARNESS_MODE=record HARNESS_WRITE_HUDDLE=3310071 python manage.py test \\
          --tag browser core.harness.huddles_browser_tests.HuddleReplyTests

  and replayed from then on. The API lets nobody delete a huddle comment,
  so each recording leaves one comment in that huddle: record once.
"""
import copy
import json
import os
import shutil
import tempfile
import time
from urllib.parse import urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase
from core.harness.conversations_browser_tests import _fixture, _write
from core.harness.event_form_browser_tests import form_fields, site_posts
from core.harness.lists_browser_tests import OverlayRecording

LFGSS = manifest.LFGSS
ISLINGTON = 'forum.islington.cc'
LFGSS_API = 'https://lfgss.microcosm.app/api/v1'
ISLINGTON_API = 'https://islingtoncc.microcosm.app/api/v1'
SELF_HUDDLE = '/huddles/%d/' % manifest.HARNESS_HUDDLE_ID
REPLY_MARKER = 'BS5-13 harness check, please ignore'
# Made-up ids: nothing with these ids is ever asked of the API.
LEAVE_ID, STAY_ID, NEW_ID, FRIEND_ID, COMMENT_ID = 99999013, 99999014, 99999016, 99999015, 99999017


class HuddlesTestCase(BrowserTestCase):

    def wait_for_scripts(self, page):
        """comments.js and peopleWidget.js are modules: wait until they have wired the page."""
        page.wait_for_function('() => [...document.querySelectorAll("[data-mw-editor]")].every(e => e.mwEditor)'
                               ' && [...document.querySelectorAll("[data-mw-people]")].every(e => e.mwPeople)')

    def stub_setup(self):
        """Made-up API answers: replay mode only, on the signed-in recording."""
        if self._recorder.mode != recorder.REPLAY:
            self.skipTest('The made-up huddle recordings run in replay mode only: they must never reach the API.')
        whoami = self._recorder.load('GET %s/whoami auth' % LFGSS_API)
        if not whoami:
            self.skipTest('No signed-in recording. Run shoot --record with HARNESS_TOKEN.')
        self.me = json.loads(whoami['body'])['data']
        self.stub_dir = tempfile.mkdtemp(prefix='bs5-13-huddles-')
        self.addCleanup(shutil.rmtree, self.stub_dir, True)
        # Catch what the views send the API: in replay the recorder answers
        # everything, so nothing leaves this process.
        self.api_writes = []
        answer = self._recorder.send

        def spy(adapter, request, **kwargs):
            if request.method != 'GET':
                self.api_writes.append((request.method, request.url, request.body))
            return answer(adapter, request, **kwargs)
        self._recorder.send = spy
        self.addCleanup(self._recorder.__dict__.pop, 'send', None)

    def stub(self, name, records):
        for record in records:
            _write(os.path.join(self.stub_dir, name), record)
        return OverlayRecording(self._recorder, self.stub_dir, name)

    # Made-up data ------------------------------------------------------

    def person(self, profile_id=None, name=None):
        me = {k: self.me[k] for k in ('id', 'siteId', 'userId', 'profileName', 'visible', 'avatar')}
        if profile_id:
            me.update(id=profile_id, profileName=name, avatar='')
        me['meta'] = {'flags': {}, 'links': [{'rel': 'self', 'href': '/api/v1/profiles/%d' % me['id']}]}
        return me

    def huddle(self, huddle_id, title, comments=()):
        """A made-up huddle between the harness user and a made-up friend."""
        when = self.frozen.strftime('%Y-%m-%dT%H:%M:%SZ')
        return {
            'id': huddle_id, 'title': title, 'isConfidential': False,
            'participants': [self.person(), self.person(FRIEND_ID, 'harness-friend')],
            'totalComments': len(comments), 'lastCommentId': COMMENT_ID, 'lastCommentCreated': when,
            'lastCommentCreatedBy': self.person(),
            'comments': {'total': len(comments), 'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1,
                         'page': 1, 'links': [], 'type': '/api/v1/comments', 'items': list(comments)},
            'meta': {'created': when, 'createdBy': self.person(), 'flags': {'watched': False, 'unread': False},
                     'links': [{'rel': 'self', 'href': '/api/v1/huddles/%d' % huddle_id}],
                     'permissions': {'create': True, 'read': True, 'update': True, 'delete': True,
                                     'guest': False, 'owner': True, 'moderator': False, 'siteOwner': False}},
        }

    def huddle_list(self, *huddles):
        return {'huddles': {'total': len(huddles), 'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1,
                            'page': 1, 'links': [], 'type': '/api/v1/huddles', 'items': list(huddles)},
                'meta': {'links': [{'rel': 'self', 'href': '/api/v1/huddles'}], 'permissions': {}}}

    def comment(self, huddle_id, markdown):
        return {'id': COMMENT_ID, 'itemType': 'huddle', 'itemId': huddle_id, 'revisions': 1,
                'markdown': markdown, 'html': '<p>%s</p>\n' % markdown,
                'meta': {'created': self.frozen.strftime('%Y-%m-%dT%H:%M:%SZ'), 'createdBy': self.person(),
                         'flags': {}, 'links': [], 'permissions': {}}}


class Bs5HuddlesPagesTests(HuddlesTestCase):

    def test_every_huddles_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('huddles'):
            with self.subTest(page=p.label):
                page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in)
                self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'))
                # Messages, or the message's own subject, which also starts the page title.
                heading = page.locator('main h1').inner_text()
                self.assertTrue(heading == 'Messages' or page.title().startswith(heading + ' | '), heading)
                page.context.close()

    def test_nothing_overflows_on_phones_and_tablets(self):
        for p in manifest.pages_for('huddles'):
            for width in (375, 768):
                with self.subTest(page=p.label, width=width):
                    page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in, width=width)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    page.context.close()

    def test_the_self_huddle_has_its_controls(self):
        page = self.open_bs5(SELF_HUDDLE, signed_in=True)
        self.wait_for_scripts(page)
        self.assertEqual(page.locator('.mw-huddle-people img').count(), 1)
        self.assertTrue(page.get_by_role('button', name='Share Message').is_visible())
        self.assertTrue(page.get_by_role('button', name='Delete Message').is_visible())
        self.assertTrue(page.locator('[data-mw-subscribe]').is_visible())
        self.assertEqual(page.locator('[data-mw-subscribe]').get_attribute('data-update-type'), '4')
        self.assertTrue(page.locator('[data-mw-reply-default] textarea').is_visible())
        form = page.locator('[data-mw-reply-default] form')
        self.assertEqual(form.locator('input[name=itemType]').input_value(), 'huddle')
        self.assertEqual(form.locator('input[name=itemId]').input_value(), str(manifest.HARNESS_HUDDLE_ID))


# ---------------------------------------------------------------------------
# Lane 7: type a name into the people widget in the self-huddle's Share modal.
# Never sent.

class ShareWidgetTests(HuddlesTestCase):

    def test_the_widget_suggests_members_and_nothing_is_sent(self):
        page = self.open_bs5(SELF_HUDDLE, signed_in=True)
        self.wait_for_scripts(page)
        posts = site_posts(page)
        page.get_by_role('button', name='Share Message').click()
        modal = page.locator('#modal-huddle-invite')
        modal.wait_for(state='visible')
        share = modal.get_by_role('button', name='Share', exact=True)
        self.assertTrue(share.is_disabled())
        self.assertEqual([t.strip() for t in modal.locator('.mw-attendees li').all_inner_texts()], ['@duncs'])

        box = modal.get_by_role('combobox', name="Type in a user's name to share this message with them")
        box.press_sequentially('du', delay=30)
        options = modal.get_by_role('listbox', name='Members').get_by_role('option')
        options.first.wait_for()
        names = [o.inner_text().strip() for o in options.all()]
        self.assertTrue(names and all(n.lower().startswith('du') for n in names), names)
        # The people who can see it already are left out.
        self.assertNotIn('duncs', names)
        self.assertEqual(box.get_attribute('aria-expanded'), 'true')
        self.snap(page, 'BS5-13-check-a')

        # Enter chooses the first: a chip, its id, and Share enabled. Removing it disables Share again.
        box.press('Enter')
        chip = modal.locator('.mw-people-chip')
        self.assertEqual(chip.inner_text().strip(), names[0])
        ids = modal.locator('input[name=invite_profile_id]').input_value()
        self.assertRegex(ids, r'^\d+$')
        self.assertTrue(share.is_enabled())
        self.snap(page, 'BS5-13-check-a-chosen')
        chip.get_by_role('button', name='Remove %s' % names[0]).click()
        self.assertEqual(modal.locator('.mw-people-chip').count(), 0)
        self.assertEqual(modal.locator('input[name=invite_profile_id]').input_value(), '')
        self.assertTrue(share.is_disabled())

        # Escape closes the list but not the modal.
        box.press_sequentially('du', delay=30)
        options.first.wait_for()
        box.press('Escape')
        self.assertFalse(page.get_by_role('listbox', name='Members').is_visible())
        self.assertTrue(modal.is_visible())
        self.assertEqual(posts, [])


@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class ShareStubTests(HuddlesTestCase):
    """Share on a made-up huddle, answered from made-up fixtures: the ids
    reach huddles/views.py invite space separated, as it reads them."""

    def setUp(self):
        self.stub_setup()

    def test_share_posts_the_people_chosen(self):
        url = '%s/huddles/%d' % (LFGSS_API, LEAVE_ID)
        huddle = self.huddle(LEAVE_ID, 'Harness stub: share me')
        with self.stub('share-before', [_fixture('GET %s auth' % url, 200, huddle)]):
            page = self.open_bs5('/huddles/%d/' % LEAVE_ID, signed_in=True, by_cookie=True)
            self.wait_for_scripts(page)
        sent = site_posts(page)
        page.get_by_role('button', name='Share Message').click()
        modal = page.locator('#modal-huddle-invite')
        box = modal.get_by_role('combobox')
        chosen = []
        for _ in range(2):
            box.press_sequentially('du', delay=30)
            option = modal.get_by_role('option').first
            option.wait_for()
            chosen.append(option.inner_text().strip())
            box.press('Enter')
        self.assertEqual(modal.locator('.mw-people-chip').all_inner_texts(), chosen)
        ids = modal.locator('input[name=invite_profile_id]').input_value().split(' ')
        self.assertEqual(len(ids), 2)

        shared = copy.deepcopy(huddle)
        shared['participants'] += [dict(self.person(int(i), n)) for i, n in zip(ids, chosen)]
        with self.stub('share-after', [_fixture('POST %s/participants?method=PUT auth' % url, 200, shared),
                                       _fixture('GET %s auth' % url, 200, shared)]):
            self.submit(page, modal.get_by_role('button', name='Share', exact=True).click,
                        '/huddles/%d/invite/' % LEAVE_ID)
        self.assertEqual(urlsplit(sent[-1][0]).path, '/huddles/%d/invite/' % LEAVE_ID)
        self.assertIn('invite_profile_id=%s' % '+'.join(ids), sent[-1][1])
        self.assertEqual([(m, urlsplit(u).path) for m, u, _ in self.api_writes],
                         [('POST', '/api/v1/huddles/%d/participants' % LEAVE_ID)])
        self.assertEqual(json.loads(self.api_writes[0][2]), [{'id': int(i)} for i in ids])
        self.assertEqual(urlsplit(page.url).path, '/huddles/%d/' % LEAVE_ID)
        self.assertEqual(page.locator('.mw-huddle-people img').count(), 4)


# ---------------------------------------------------------------------------
# Lane 8: leave a huddle from the modal. Stubbed only: a made-up huddle.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class LeaveHuddleTests(HuddlesTestCase):

    def setUp(self):
        self.stub_setup()

    def test_leave_a_made_up_huddle(self):
        url = '%s/huddles/%d' % (LFGSS_API, LEAVE_ID)
        leave = self.huddle(LEAVE_ID, 'Harness stub: leave me')
        stay = self.huddle(STAY_ID, 'Harness stub: stays')
        with self.stub('listed', [_fixture('GET %s/huddles auth' % LFGSS_API, 200, self.huddle_list(leave, stay)),
                                  _fixture('GET %s auth' % url, 200, leave)]):
            page = self.open_bs5('/huddles/', signed_in=True, by_cookie=True)
            self.assertEqual(page.locator('.mw-rows > li').count(), 2)
            self.assertTrue(page.locator('#huddle%d' % LEAVE_ID).is_visible())
            page.goto('https://%s/huddles/%d/' % (LFGSS, LEAVE_ID), wait_until='load')
            self.wait_for_scripts(page)
        sent = site_posts(page)

        page.get_by_role('button', name='Delete Message').click()
        modal = page.locator('#modal-huddle-leave')
        modal.wait_for(state='visible')
        self.assertIn('You will no longer be able to view', modal.inner_text())
        self.snap(page, 'BS5-13-check-b-modal')

        with self.stub('left', [_fixture('GET %s auth' % url, 200, leave),
                                _fixture('DELETE %s?method=DELETE auth' % url, 200, None),
                                _fixture('GET %s/huddles auth' % LFGSS_API, 200, self.huddle_list(stay))]):
            self.submit(page, modal.get_by_role('button', name='Delete Message').click,
                        '/huddles/%d/leave/' % LEAVE_ID)
        self.assertEqual(urlsplit(sent[-1][0]).path, '/huddles/%d/leave/' % LEAVE_ID)
        self.assertEqual([(m, urlsplit(u).path) for m, u, _ in self.api_writes],
                         [('DELETE', '/api/v1/huddles/%d' % LEAVE_ID)])
        self.assertEqual(urlsplit(page.url).path, '/huddles/')
        self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'))
        self.assertEqual(page.locator('#huddle%d' % LEAVE_ID).count(), 0)
        self.assertTrue(page.locator('#huddle%d' % STAY_ID).is_visible())
        self.snap(page, 'BS5-13-check-b')


# ---------------------------------------------------------------------------
# The New message form, sent on made-up answers.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class NewMessageTests(HuddlesTestCase):

    def setUp(self):
        self.stub_setup()

    def test_send_a_message(self):
        path = '/huddles/create/?to=%d' % manifest.HARNESS_PROFILE_ID
        page = self.open_bs5(path, signed_in=True, by_cookie=True)
        self.wait_for_scripts(page)
        sent = site_posts(page)
        # ?to= chose the harness user, who can be removed.
        self.assertEqual(page.locator('.mw-people-chip').all_inner_texts(), ['duncs'])
        self.assertEqual(page.locator('input[name=invite]').input_value(), str(manifest.HARNESS_PROFILE_ID))

        # No subject: nothing is sent.
        page.get_by_role('button', name='Send Message').click()
        self.assertIn('is-invalid', page.get_by_label('What is the subject of the message?').get_attribute('class'))
        self.assertTrue(page.get_by_text('Please add a subject').is_visible())
        self.assertEqual(sent, [])

        page.get_by_label('What is the subject of the message?').fill('Harness stub: new message')
        invite = page.get_by_role('combobox', name='Who will be able to see and reply to this message?')
        invite.press_sequentially('du', delay=30)
        options = page.get_by_role('listbox', name='Members').get_by_role('option')
        options.first.wait_for()
        name = options.first.inner_text().strip()
        invite.press('Enter')
        self.assertEqual(page.locator('.mw-people-chip').all_inner_texts(), ['duncs', name])
        ids = page.locator('input[name=invite]').input_value().split(',')
        self.assertEqual(len(ids), 2)
        page.get_by_label('What is it you want to say?').fill('Posted from the harness')
        self.snap(page, 'BS5-13-new-message')

        huddle = self.huddle(NEW_ID, 'Harness stub: new message',
                             [self.comment(NEW_ID, 'Posted from the harness')])
        url = '%s/huddles/%d' % (LFGSS_API, NEW_ID)
        with self.stub('created', [_fixture('POST %s/huddles auth' % LFGSS_API, 200, huddle),
                                   _fixture('POST %s/participants?method=PUT auth' % url, 200, huddle),
                                   _fixture('POST %s/comments auth' % LFGSS_API, 200,
                                            self.comment(NEW_ID, 'Posted from the harness')),
                                   _fixture('GET %s auth' % url, 200, huddle)]):
            self.submit(page, page.get_by_role('button', name='Send Message').click, '/huddles/create/')

        fields = form_fields(sent[-1][1])
        self.assertEqual((fields['title'], fields['is_confidential'], fields['firstcomment']),
                         ('Harness stub: new message', '0', 'Posted from the harness'))
        self.assertEqual(fields['invite'], ','.join(ids))
        self.assertEqual([(m, urlsplit(u).path) for m, u, _ in self.api_writes], [
            ('POST', '/api/v1/huddles'), ('POST', '/api/v1/huddles/%d/participants' % NEW_ID),
            ('POST', '/api/v1/comments')])
        self.assertEqual(json.loads(self.api_writes[1][2]), [{'id': int(i)} for i in ids])
        self.assertEqual(urlsplit(page.url).path, '/huddles/%d/' % NEW_ID)
        self.assertEqual(page.locator('main h1').inner_text(), 'Harness stub: new message')


# ---------------------------------------------------------------------------
# Lane 9: reply in the self-huddle, live once, then replayed.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class HuddleReplyTests(HuddlesTestCase):

    def setUp(self):
        self.recording = os.path.join(self.fixtures_dir, 'huddle-reply')
        if self._recorder.mode == recorder.REPLAY:
            if not os.path.isdir(self.recording):
                self.skipTest('No huddle reply recording in %s. Record it once: HARNESS_MODE=record '
                              'HARNESS_WRITE_HUDDLE=%d python manage.py test --tag browser '
                              'core.harness.huddles_browser_tests.HuddleReplyTests'
                              % (self.recording, manifest.HARNESS_HUDDLE_ID))
        elif os.environ.get('HARNESS_WRITE_HUDDLE') != str(manifest.HARNESS_HUDDLE_ID):
            self.skipTest('Recording writes to the live huddle %d; set HARNESS_WRITE_HUDDLE=%d to allow it.'
                          % (manifest.HARNESS_HUDDLE_ID, manifest.HARNESS_HUDDLE_ID))

    def step(self, name):
        return OverlayRecording(self._recorder, self.fixtures_dir, os.path.join('huddle-reply', name))

    def test_reply_in_the_self_huddle(self):
        page = self.new_page(signed_in=True)
        page.context.add_cookies([{'name': 'bs', 'value': '5', 'url': 'https://%s/' % LFGSS}])
        sent = site_posts(page)

        with self.step('0-before'):
            page.goto('https://%s%s' % (LFGSS, SELF_HUDDLE), wait_until='load')
            self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'))
            # Only the harness user can see it: the one place a write is allowed.
            self.assertEqual(page.locator('.mw-huddle-people img').count(), 1)
            self.wait_for_scripts(page)
            before = page.evaluate('() => [...document.querySelectorAll(".mw-comments [id^=comment]")].map(e => e.id)')

        with self.step('1-posted'):
            box = page.locator('[data-mw-reply-default]')
            box.locator('textarea').fill('%s (%s).' % (REPLY_MARKER, time.strftime('%Y-%m-%d')))
            self.submit(page, box.get_by_role('button', name='Post reply').click, '/comments/create/')
            fields = form_fields(sent[-1][1])
            self.assertEqual((fields['itemType'], fields['itemId']), ('huddle', str(manifest.HARNESS_HUDDLE_ID)))
            fragment = urlsplit(page.url).fragment
            self.assertRegex(fragment, r'^comment\d+$')
            self.assertNotIn(fragment, before)
            self.assertEqual(urlsplit(page.url).path, SELF_HUDDLE)
            self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'))
            posted = page.locator('#' + fragment)
            self.assertIn(REPLY_MARKER, posted.inner_text())
            self.assertTrue(posted.get_by_role('button', name='Edit').is_visible())
            self.assertTrue(page.locator('[data-mw-reply-default] textarea').is_visible())
            posted.scroll_into_view_if_needed()
            self.snap(page, 'BS5-13-signed-in')


# ---------------------------------------------------------------------------
# Lane 10: Islington CC's branding around Messages, light and dark, signed in
# on made-up answers.

COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    title: rgb(document.querySelector('.mw-row-title a'), 'color'),
    link: rgb(document.querySelector('.mw-row-meta a'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class IslingtonBrandingTests(HuddlesTestCase):

    def setUp(self):
        self.stub_setup()

    def test_islington_messages_light_and_dark(self):
        me = dict(self.me, siteId=0)
        site_link = colors.parse_hex('#185945')
        surround = colors.parse_hex('#bfc3c5')
        huddles = self.huddle_list(self.huddle(LEAVE_ID, 'Harness stub: a message'),
                                   self.huddle(STAY_ID, 'Harness stub: another'))
        with self.stub('islington', [_fixture('GET %s/whoami auth' % ISLINGTON_API, 200, me),
                                     _fixture('GET %s/huddles auth' % ISLINGTON_API, 200, huddles)]):
            for mode in ('light', 'dark'):
                with self.subTest(mode=mode):
                    page = self.open_bs5('/huddles/', host=ISLINGTON, signed_in=True, color_mode=mode)
                    self.assertEqual(page.locator('.mw-rows > li').count(), 2)
                    facts = page.evaluate(COLOR_FACTS_JS)
                    self.assertEqual(facts['theme'], mode)
                    self.assertEqual(tuple(facts['surround']), surround, 'the Site surround')
                    self.assertEqual(facts['logo'], 89)
                    self.assertGreaterEqual(colors.contrast(facts['title'], facts['main']), 7)
                    if mode == 'light':
                        self.assertEqual(tuple(facts['link']), site_link)
                    else:
                        self.assertGreaterEqual(colors.contrast(facts['link'], facts['main']), colors.AA)
                    self.snap(page, 'BS5-13-branding-%s' % mode)
                    page.context.close()
        self.assertEqual(self.api_writes, [])
