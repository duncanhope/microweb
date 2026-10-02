"""Interaction checks for the forum admin family on Bootstrap 5 (BS5-14):
memberships.html, forms/memberships.html with membership_form.js,
forms/microcosm.html, forms/moderation_item.html, and the Follow control
(forms/subscribe.html) and moderation control (forms/metabar-moderation.html)
it shares with the other families.

Run with `python manage.py test --tag browser` after one `shoot --record`
(with HARNESS_TOKEN set, for the signed-in pages).

What reaches the API:
- Nothing, from the pages, the forum form, the membership group form
  (lane 7) or moderation (lane 9): every save is answered from made-up
  fixtures, in replay mode only. The harness user is no admin on lfgss, so
  the made-up answers also make it one. Lane 7 runs on a made-up forum and
  group (ids from 99999140); moderation on the conversation the comment
  checks use, made up to be the harness user's to moderate.
- FollowTests (lane 8) follows one conversation the harness user does not
  follow and stops following it again, the one write the operator allowed.
  It is recorded once into fixtures/follow/ with

      HARNESS_MODE=record HARNESS_WRITE_FOLLOW=141600 python manage.py test \\
          --tag browser core.harness.admin_browser_tests.FollowTests

  and replayed from then on. The check fails unless the conversation ends
  not followed, as it began.
- Islington CC (lane 10) is shot as a guest: a signed-in request to another
  Site makes the harness user a profile there.
"""
import copy
import json
import os
import shutil
import tempfile
from urllib.parse import parse_qs, urlsplit

from django.test import override_settings

from core import colors
from core.harness import manifest, recorder
from core.harness.browser_tests import BrowserTestCase
from core.harness.conversations_browser_tests import _fixture, _write
from core.harness.event_form_browser_tests import form_fields, site_posts
from core.harness.lists_browser_tests import OverlayRecording
from core.harness.profiles_browser_tests import PNG

LFGSS = manifest.LFGSS
ISLINGTON = 'forum.islington.cc'
LFGSS_API = 'https://lfgss.microcosm.app/api/v1'
FORUM_ID = manifest.ADMIN_FORUM_ID
CONVERSATION_ID = manifest.STUB_WRITE_CONVERSATION_ID
# Made-up ids: nothing with these ids is ever asked of the API.
STUB_FORUM, STUB_GROUP, STUB_CRITERION = 99999140, 99999141, 99999142
# The conversation lane 8 follows and stops following: one the harness user
# does not follow.
FOLLOW_CONVERSATION_ID = 141600
ADMIN = {'siteOwner': True, 'moderator': True, 'owner': False, 'update': True, 'delete': True}
PAGE = {'limit': 25, 'offset': 0, 'maxOffset': 0, 'totalPages': 1, 'page': 1, 'links': []}


class AdminTestCase(BrowserTestCase):

    def assert_on_bs5(self, page):
        self.assertTrue(page.evaluate('!!document.querySelector("link[href*=\'bs5.min.css\']")'), 'not Bootstrap 5')

    def stub_setup(self):
        """Made-up API answers: replay mode only, on the signed-in recording."""
        if self._recorder.mode != recorder.REPLAY:
            self.skipTest('The made-up admin recordings run in replay mode only: they must never reach the API.')
        whoami = self._recorder.load('GET %s/whoami auth' % LFGSS_API)
        if not whoami:
            self.skipTest('No signed-in recording. Run shoot --record with HARNESS_TOKEN.')
        self.me = json.loads(whoami['body'])['data']
        self.stub_dir = tempfile.mkdtemp(prefix='bs5-14-admin-')
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

    def recorded(self, key):
        record = self._recorder.load(key)
        if record is None:
            self.skipTest('No recording of %s. Run shoot --record with HARNESS_TOKEN.' % key)
        return json.loads(record['body'])['data']

    def writes(self):
        return [(m, urlsplit(u).path) for m, u, _ in self.api_writes]


class Bs5AdminPagesTests(AdminTestCase):

    def test_every_admin_page_renders_on_bootstrap_5(self):
        for p in manifest.pages_for('admin'):
            with self.subTest(page=p.label):
                page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in)
                self.assert_on_bs5(page)
                self.assertTrue(page.locator('main h1').is_visible())
                page.context.close()

    def test_nothing_overflows_on_phones_and_tablets(self):
        for p in manifest.pages_for('admin'):
            for width in (375, 768):
                with self.subTest(page=p.label, width=width):
                    page = self.open_bs5(p.path, host=p.host, signed_in=p.signed_in, width=width)
                    self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'), width)
                    page.context.close()

    def test_membership_groups(self):
        page = self.open_bs5('/microcosms/%d/memberships/' % FORUM_ID)
        rows = page.locator('.mw-rows > li')
        self.assertGreater(rows.count(), 1)
        # The Site's groups, inherited, and none the guest may edit.
        self.assertEqual(page.get_by_text('Inherited Group').count(), rows.count())
        self.assertEqual(page.get_by_role('link', name='Edit Group').count(), 0)
        self.assertGreater(page.locator('.mw-can').count(), 0)
        self.assertGreater(page.locator('.mw-cannot').count(), 0)
        self.assertEqual(page.locator('.mw-breadcrumb a').last.inner_text(), 'Membership Groups')


# ---------------------------------------------------------------------------
# The membership group form: its answers and criteria, in the browser only.

class MembershipFormTests(AdminTestCase):

    def open_form(self):
        page = self.open_bs5('/microcosms/%d/memberships/create/' % FORUM_ID, signed_in=True)
        page.wait_for_function('() => document.querySelector("[data-mw-membership-form]").dataset.mwReady === ""'
                               ' && document.querySelector("[data-mw-people]").mwPeople')
        return page

    def answers(self, page):
        return page.evaluate('''() => Object.fromEntries([...document.querySelectorAll(".mw-toggle input:checked")]
            .map(i => [i.name, i.value]))''')

    def test_answers_keep_each_other_consistent(self):
        page = self.open_form()
        sent = site_posts(page)
        self.assertEqual(set(self.answers(page).values()), {'0'})
        page.locator('label[for=is_moderator-1]').click()
        answers = self.answers(page)
        self.assertEqual({k: answers[k] for k in ('can_read', 'can_create', 'can_edit_others', 'can_delete_others',
                                                    'can_close_own', 'can_open_own')},
                         dict.fromkeys(('can_read', 'can_create', 'can_edit_others', 'can_delete_others',
                                        'can_close_own', 'can_open_own'), '1'))
        # Guests cannot moderate or post.
        page.locator('label[for=include_unregistered-1]').click()
        answers = self.answers(page)
        self.assertEqual((answers['is_moderator'], answers['can_create'], answers['can_read']), ('0', '0', '1'))
        # Banned reads nothing.
        page.locator('label[for=is_banned-1]').click()
        self.assertEqual(self.answers(page)['can_read'], '0')
        # Nothing is sent without a name.
        page.get_by_role('button', name='Create group').click()
        self.assertIn('is-invalid', page.locator('#name').get_attribute('class'))
        self.assertTrue(page.get_by_text('The membership group must have a name.').is_visible())
        self.assertEqual(sent, [])

    def test_criteria_offer_the_comparisons_each_value_allows(self):
        page = self.open_form()
        box = page.locator('[data-mw-criteria]')
        box.get_by_role('button', name='Add criteria for users to join this group').click()
        condition = box.get_by_label('Condition')
        comparison = box.get_by_label('Comparison')
        value = box.get_by_label('Value')
        enabled = '(s) => [...s.options].filter(o => !o.disabled).map(o => o.value)'

        self.assertEqual(comparison.evaluate(enabled), ['eq', 'neq', 'substr', 'nsubstr'])
        condition.select_option('commentCount')
        self.assertEqual(comparison.input_value(), 'gt')
        self.assertEqual(comparison.evaluate(enabled), ['gt', 'ge', 'eq', 'le', 'lt', 'neq'])
        self.assertEqual(value.get_attribute('type'), 'number')
        # No value: an error, nothing added.
        box.get_by_role('button', name='Add', exact=True).click()
        self.assertIn('is-invalid', value.get_attribute('class'))
        value.fill('1000')
        box.get_by_role('button', name='Add', exact=True).click()

        condition.select_option('created')
        self.assertEqual((comparison.input_value(), value.get_attribute('type')), ('le', 'date'))
        value.fill('2014-02-14')
        box.locator('label[for=criteria-or]').click()
        box.get_by_role('button', name='Add', exact=True).click()

        # A custom attribute is asked for by name; true or false is a yes/no value.
        page.once('dialog', lambda dialog: dialog.accept('is_member'))
        condition.select_option(label='Custom Attribute')
        self.assertEqual(condition.input_value(), 'is_member')
        value.fill('true')
        self.assertEqual(comparison.evaluate(enabled), ['eq', 'neq'])
        box.locator('label[for=criteria-and]').click()
        box.get_by_role('button', name='Add', exact=True).click()

        items = [t.strip() for t in box.locator('[data-mw-criteria-items] > li').all_inner_texts()]
        self.assertEqual(items, ['commentCount is greater than 1000 Remove', 'or',
                                 'created is less than or equal to 2014-02-14 Remove',
                                 'and is_member equals true Remove'])
        box.get_by_role('button', name='Remove created is less than or equal to 2014-02-14').click()
        self.assertEqual(box.locator('[data-mw-criteria-items] > li').count(), 2)
        self.snap(page, 'BS5-14-criteria')


# ---------------------------------------------------------------------------
# Lane 7: add a criterion to a made-up membership group and save it.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class MembershipSaveTests(AdminTestCase):

    def setUp(self):
        self.stub_setup()
        forum = self.recorded('GET %s/microcosms/%d auth' % (LFGSS_API, FORUM_ID))
        forum = copy.deepcopy(forum)
        forum.update(id=STUB_FORUM, title='Harness stub: a forum')
        forum['meta']['permissions'].update(ADMIN)
        forum['meta']['links'] = [{'rel': 'self', 'href': '/api/v1/microcosms/%d' % STUB_FORUM}]
        self.forum = forum
        self.forum_url = '%s/microcosms/%d' % (LFGSS_API, STUB_FORUM)
        self.group_url = '%s/roles/%d' % (self.forum_url, STUB_GROUP)

    def group(self, **flags):
        group = {'id': STUB_GROUP, 'microcosmId': STUB_FORUM, 'title': 'Harness stub: riders', 'moderator': False,
                 'banned': False, 'includeGuests': False, 'includeUsers': False, 'create': True, 'read': True,
                 'update': False, 'delete': False, 'closeOwn': False, 'openOwn': False, 'readOthers': True}
        group.update(flags)
        return group

    def criteria(self, *rows):
        return {'criteria': dict(PAGE, total=len(rows), type='/api/v1/criteria', items=list(rows)), 'meta': {'links': []}}

    def people(self, *people):
        return {'profiles': dict(PAGE, total=len(people), type='/api/v1/profiles', items=list(people)),
                'meta': {'links': []}}

    def person(self):
        return {k: self.me[k] for k in ('id', 'siteId', 'userId', 'profileName', 'visible', 'avatar')}

    def edit_page(self, criteria):
        return [_fixture('GET %s auth' % self.forum_url, 200, self.forum),
                _fixture('GET %s auth' % self.group_url, 200, self.group()),
                _fixture('GET %s/criteria auth' % self.group_url, 200, self.criteria(*criteria)),
                _fixture('GET %s/profiles?limit=250 auth' % self.group_url, 200, self.people(self.person()))]

    def test_add_a_criterion_and_save(self):
        path = '/microcosms/%d/memberships/%d/edit/' % (STUB_FORUM, STUB_GROUP)
        existing = {'id': 1, 'orGroup': 0, 'profileColumn': 'commentCount', 'predicate': 'gt', 'value': 100}
        with self.stub('before', self.edit_page([existing])):
            page = self.open_bs5(path, signed_in=True, by_cookie=True)
            page.wait_for_function('() => document.querySelector("[data-mw-membership-form]").dataset.mwReady === ""'
                                   ' && document.querySelector("[data-mw-people]").mwPeople')
        box = page.locator('[data-mw-criteria]')
        self.assertEqual([t.strip() for t in box.locator('[data-mw-criteria-items] > li').all_inner_texts()],
                         ['commentCount is greater than 100 Remove'])
        self.assertEqual(page.locator('.mw-people-chip').all_inner_texts(), [self.me['profileName']])
        self.assertEqual(page.locator('input[name=can_read]:checked').input_value(), '1')

        # Add: or an email containing a made-up domain.
        box.get_by_role('button', name='Add criteria', exact=True).click()
        box.locator('label[for=criteria-or]').click()
        box.get_by_label('Condition').select_option('email')
        box.get_by_label('Comparison').select_option('substr')
        box.get_by_label('Value').fill('@example.com')
        box.get_by_role('button', name='Add', exact=True).click()
        self.snap(page, 'BS5-14-check-a-added')

        added = {'id': STUB_CRITERION, 'orGroup': 1, 'profileColumn': 'email', 'predicate': 'substr',
                 'value': '@example.com'}
        groups = {'roles': dict(PAGE, total=1, type='/api/v1/roles', items=[self.group()]),
                  'meta': {'links': [], 'permissions': {}}}
        with self.stub('saved', [
            _fixture('PUT %s auth' % self.group_url, 302, self.group()),
            _fixture('DELETE %s/criteria auth' % self.group_url, 200, None),
            _fixture('POST %s/criteria auth' % self.group_url, 200, dict(existing, id=1)),
            _fixture('DELETE %s/profiles auth' % self.group_url, 200, None),
            _fixture('PUT %s/profiles auth' % self.group_url, 200, None),
            _fixture('GET %s auth' % self.forum_url, 200, self.forum),
            _fixture('GET %s/roles auth' % self.forum_url, 200, groups),
        ]):
            with page.expect_request(lambda r: r.method == 'POST' and urlsplit(r.url).path.endswith('/api/')) as req:
                page.get_by_role('button', name='Save group').click()
            page.wait_for_url(lambda url: urlsplit(url).path == '/microcosms/%d/memberships/' % STUB_FORUM)
            page.wait_for_load_state('load')
        body = json.loads(req.value.post_data)
        self.assertEqual(urlsplit(req.value.url).path, '/microcosms/%d/memberships/api/' % STUB_FORUM)
        self.assertEqual(body['role']['id'], STUB_GROUP)
        self.assertEqual((body['role']['read'], body['role']['create'], body['role']['moderator']), (True, True, False))
        self.assertEqual(body['criteria'], [
            {'orGroup': 0, 'profileColumn': 'commentCount', 'predicate': 'gt', 'value': 100},
            {'orGroup': 1, 'profileColumn': 'email', 'predicate': 'substr', 'value': '@example.com'}])
        self.assertEqual(body['profiles'], [str(self.me['id'])])
        self.assertEqual(self.writes(), [
            ('PUT', '/api/v1/microcosms/%d/roles/%d' % (STUB_FORUM, STUB_GROUP)),
            ('DELETE', '/api/v1/microcosms/%d/roles/%d/criteria' % (STUB_FORUM, STUB_GROUP)),
            ('POST', '/api/v1/microcosms/%d/roles/%d/criteria' % (STUB_FORUM, STUB_GROUP)),
            ('POST', '/api/v1/microcosms/%d/roles/%d/criteria' % (STUB_FORUM, STUB_GROUP)),
            ('DELETE', '/api/v1/microcosms/%d/roles/%d/profiles' % (STUB_FORUM, STUB_GROUP)),
            ('PUT', '/api/v1/microcosms/%d/roles/%d/profiles' % (STUB_FORUM, STUB_GROUP))])
        self.assertEqual(json.loads(self.api_writes[3][2])['profileColumn'], 'email')
        self.assert_on_bs5(page)
        self.assertEqual(page.locator('.mw-rows > li').count(), 1)

        # It reloads intact.
        with self.stub('after', self.edit_page([existing, added])):
            page.goto('https://%s%s' % (LFGSS, path), wait_until='load')
            page.wait_for_function('() => document.querySelector("[data-mw-membership-form]").dataset.mwReady === ""')
        self.assertEqual([t.strip() for t in box.locator('[data-mw-criteria-items] > li').all_inner_texts()],
                         ['commentCount is greater than 100 Remove', 'or', 'email contains @example.com Remove'])
        box.scroll_into_view_if_needed()
        self.snap(page, 'BS5-14-check-a')

    def test_delete_a_group(self):
        path = '/microcosms/%d/memberships/%d/edit/' % (STUB_FORUM, STUB_GROUP)
        with self.stub('before', self.edit_page([])):
            page = self.open_bs5(path, signed_in=True, by_cookie=True)
            page.wait_for_function('() => document.querySelector("[data-mw-membership-form]").dataset.mwReady === ""')
        groups = {'roles': dict(PAGE, total=0, type='/api/v1/roles', items=[]), 'meta': {'links': [], 'permissions': {}}}
        page.once('dialog', lambda dialog: dialog.accept())
        with self.stub('deleted', [_fixture('DELETE %s auth' % self.group_url, 200, None),
                                   _fixture('GET %s auth' % self.forum_url, 200, self.forum),
                                   _fixture('GET %s/roles auth' % self.forum_url, 200, groups)]):
            with page.expect_request(lambda r: r.method == 'POST') as req:
                page.get_by_role('button', name='Delete membership group').click()
            page.wait_for_url(lambda url: urlsplit(url).path == '/microcosms/%d/memberships/' % STUB_FORUM)
            page.wait_for_load_state('load')
        self.assertEqual(json.loads(req.value.post_data), {'deleteRole': STUB_GROUP})
        self.assertEqual(self.writes(), [('DELETE', '/api/v1/microcosms/%d/roles/%d' % (STUB_FORUM, STUB_GROUP))])
        self.assertEqual(page.locator('.mw-rows > li').count(), 0)

    def test_a_failed_save_lets_people_try_again(self):
        page = self.open_bs5('/microcosms/%d/memberships/create/' % FORUM_ID, signed_in=True)
        page.wait_for_function('() => document.querySelector("[data-mw-membership-form]").dataset.mwReady === ""')
        page.route('**/memberships/api/', lambda route: route.fulfill(status=400, body=''))
        page.get_by_label('Please enter a name for the group:').fill('Harness stub: never saved')
        page.get_by_role('button', name='Create group').click()
        alert = page.get_by_role('alert')
        alert.wait_for()
        self.assertIn('could not be saved', alert.inner_text())
        self.assertTrue(page.get_by_role('button', name='Create group').is_enabled())
        self.assertEqual(self.api_writes, [])


# ---------------------------------------------------------------------------
# The forum form: checked before it is sent, and saved on made-up answers.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class ForumFormTests(AdminTestCase):

    def setUp(self):
        self.stub_setup()

    def test_edit_a_forum(self):
        path = '/microcosms/%d/edit/' % FORUM_ID
        page = self.open_bs5(path, signed_in=True, by_cookie=True)
        sent = site_posts(page)
        self.assertEqual(page.locator('main h1').inner_text(), 'Edit a forum')
        self.assertEqual(page.get_by_label('What is the name of the forum?').input_value(), 'Social')
        # The logo box shows a chosen image before anything is saved.
        page.locator('#input_logo').set_input_files([{'name': 'logo.png', 'mimeType': 'image/png', 'buffer': PNG}])
        self.assertTrue(page.locator('.mw-logo-drop img').get_attribute('src').startswith('blob:'))
        page.locator('#input_logo').set_input_files([])
        # No reason: nothing is sent.
        page.get_by_role('button', name='Save forum').click()
        self.assertIn('is-invalid', page.locator('#editReason').get_attribute('class'))
        self.assertTrue(page.get_by_text('Please give a reason for editing.').is_visible())
        self.assertEqual(sent, [])
        self.snap(page, 'BS5-14-forum-edit')

        page.locator('#editReason').fill('Harness check')
        forum = self.recorded('GET %s/microcosms/%d auth' % (LFGSS_API, FORUM_ID))
        with self.stub('forum-saved', [_fixture('POST %s/microcosms/%d?method=PUT auth' % (LFGSS_API, FORUM_ID),
                                                200, forum)]):
            self.submit(page, page.get_by_role('button', name='Save forum').click, '/microcosms/%d/' % FORUM_ID)
        fields = form_fields(sent[-1][1])
        self.assertEqual((fields['title'], fields['editReason'], fields['id']), ('Social', 'Harness check', str(FORUM_ID)))
        self.assertEqual(self.writes(), [('POST', '/api/v1/microcosms/%d' % FORUM_ID)])
        self.assert_on_bs5(page)

    def test_create_a_forum_checks_its_name(self):
        page = self.open_bs5('/microcosms/create/', signed_in=True)
        sent = site_posts(page)
        page.get_by_role('button', name='Save forum').click()
        self.assertIn('is-invalid', page.get_by_label('What is the name of the forum?').get_attribute('class'))
        self.assertIn('is-invalid', page.get_by_label('What is the forum about?').get_attribute('class'))
        self.assertEqual(sent, [])


# ---------------------------------------------------------------------------
# Lane 8: follow a conversation, then stop following it. Live once, replayed.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class FollowTests(AdminTestCase):

    PATH = '/conversations/%d/' % FOLLOW_CONVERSATION_ID

    def setUp(self):
        self.recording = os.path.join(self.fixtures_dir, 'follow')
        if self._recorder.mode == recorder.REPLAY:
            if not os.path.isdir(self.recording):
                self.skipTest('No follow recording in %s. Record it once: HARNESS_MODE=record '
                              'HARNESS_WRITE_FOLLOW=%d python manage.py test --tag browser '
                              'core.harness.admin_browser_tests.FollowTests' % (self.recording, FOLLOW_CONVERSATION_ID))
        elif os.environ.get('HARNESS_WRITE_FOLLOW') != str(FOLLOW_CONVERSATION_ID):
            self.skipTest('Recording follows conversation %d as the harness user; set HARNESS_WRITE_FOLLOW=%d to '
                          'allow it.' % (FOLLOW_CONVERSATION_ID, FOLLOW_CONVERSATION_ID))

    def step(self, name):
        return OverlayRecording(self._recorder, self.fixtures_dir, os.path.join('follow', name))

    def control(self, page):
        return page.locator('#mw-metabar [data-mw-subscribe]')

    def state(self, page):
        control = self.control(page)
        return control.get_attribute('data-state'), control.locator('input[name=emailme]').is_visible()

    def load(self, page):
        page.goto('https://%s%s' % (LFGSS, self.PATH), wait_until='load')
        self.assert_on_bs5(page)
        page.wait_for_function('() => window.bootstrap')

    def toggle(self, page, button, state):
        with page.expect_response(lambda r: urlsplit(r.url).path == '/watchers/' and r.request.method == 'POST') as sent:
            self.control(page).get_by_role('button', name=button).click()
        self.assertEqual(sent.value.status, 200)
        page.wait_for_function('(s) => document.querySelector("#mw-metabar [data-mw-subscribe]").dataset.state === s',
                               arg=state)
        return parse_qs(sent.value.request.post_data)

    def test_follow_and_unfollow(self):
        page = self.new_page(signed_in=True)
        page.context.add_cookies([{'name': 'bs', 'value': '5', 'url': 'https://%s/' % LFGSS}])

        with self.step('0-before'):
            self.load(page)
            self.assertEqual(self.state(page), ('off', False), 'the harness user already follows the lane 8 conversation')

        with self.step('1-followed'):
            posted = self.toggle(page, 'Follow', 'on')
            self.assertEqual((posted['itemType'], posted['itemId']), (['conversation'], [str(FOLLOW_CONVERSATION_ID)]))
            self.assertNotIn('delete', posted)
            # The email checkbox comes with the follow.
            self.assertEqual(self.state(page), ('on', True))
            self.load(page)
            self.assertEqual(self.state(page), ('on', True), 'not followed after a reload')
            self.control(page).scroll_into_view_if_needed()
            self.snap(page, 'BS5-14-check-b')

        with self.step('2-unfollowed'):
            posted = self.toggle(page, 'unfollow', 'off')
            self.assertEqual(posted['delete'], ['true'])
            self.assertEqual(self.state(page), ('off', False))

        # A fresh load: the conversation is not followed, as before.
        with self.step('3-verified'):
            self.load(page)
            self.assertEqual(self.state(page), ('off', False), 'still followed: put it back by hand')


# ---------------------------------------------------------------------------
# Lane 9: the moderation controls, with made-up permissions. Never sent.

@override_settings(SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO', 'https'))
class ModerationTests(AdminTestCase):

    def setUp(self):
        self.stub_setup()
        url = '%s/conversations/%d' % (LFGSS_API, CONVERSATION_ID)
        conversation = copy.deepcopy(self.recorded('GET %s auth' % url))
        conversation['meta']['permissions'].update(ADMIN)
        conversation['microcosmId'] = FORUM_ID
        self.conversation = conversation
        self.conversation_url = url

    def open_conversation(self):
        with self.stub('moderator', [_fixture('GET %s auth' % self.conversation_url, 200, self.conversation)]):
            page = self.open_bs5('/conversations/%d/' % CONVERSATION_ID, signed_in=True, by_cookie=True)
        return page

    def choose(self, page, action, expected_path):
        control = page.locator('#mw-metabar form.mw-moderation')
        control.get_by_label('Moderation action').select_option(action)
        # Move lists the Site's forums as a tree, indented by level.
        tree = [{'id': FORUM_ID, 'title': 'Social', 'level': 1, 'href': '/api/v1/microcosms/%d' % FORUM_ID},
                {'id': STUB_FORUM, 'parentId': FORUM_ID, 'title': 'Harness stub: a subforum', 'level': 2,
                 'href': '/api/v1/microcosms/%d' % STUB_FORUM}]
        with self.stub('confirm-' + action, [_fixture('GET %s auth' % self.conversation_url, 200, self.conversation),
                                             _fixture('GET %s/microcosms/tree auth' % LFGSS_API, 200, tree)]):
            with page.expect_navigation(url=lambda url: urlsplit(url).path == expected_path, wait_until='load'):
                control.get_by_role('button', name='Go').click()

    def test_the_controls_render_for_a_moderator(self):
        page = self.open_conversation()
        control = page.locator('#mw-metabar form.mw-moderation')
        self.assertTrue(control.is_visible())
        options = control.get_by_label('Moderation action').evaluate('(s) => [...s.options].map(o => o.value)')
        self.assertEqual(options, ['pin', 'close', 'move', 'delete'])
        control.scroll_into_view_if_needed()
        self.snap(page, 'BS5-14-signed-in')
        self.assertEqual(self.api_writes, [])

    def test_move_a_conversation(self):
        page = self.open_conversation()
        self.choose(page, 'move', '/moderate/')
        self.assert_on_bs5(page)
        self.assertEqual(page.locator('main h1').inner_text().strip(), 'Move %s to:' % self.conversation['title'])
        page.get_by_label('The forum to move it to').select_option(str(FORUM_ID))
        self.snap(page, 'BS5-14-move')
        with self.stub('moved', [_fixture('POST %s?method=PUT auth' % self.conversation_url, 200, self.conversation)]):
            self.submit(page, page.get_by_role('button', name='Go').click, '/microcosms/%d/' % FORUM_ID)
        self.assertEqual(self.writes(), [('POST', '/api/v1/conversations/%d' % CONVERSATION_ID)])
        moved = json.loads(self.api_writes[0][2])
        self.assertEqual((moved['microcosmId'], moved['meta']['editReason']), (FORUM_ID, 'Moderator moved item'))

    def test_close_a_conversation(self):
        page = self.open_conversation()
        self.choose(page, 'close', '/moderate/')
        self.assertIn('Do you wish to close', page.locator('main h1').inner_text())
        with self.stub('closed', [_fixture('PATCH %s auth' % self.conversation_url, 200, None)]):
            self.submit(page, page.get_by_role('button', name='Close').click, '/microcosms/%d/' % FORUM_ID)
        self.assertEqual(self.writes(), [('PATCH', '/api/v1/conversations/%d' % CONVERSATION_ID)])
        self.assertEqual(json.loads(self.api_writes[0][2]),
                         [{'op': 'replace', 'path': '/meta/flags/open', 'value': False}])


# ---------------------------------------------------------------------------
# Lane 10: Islington CC's branding around its membership groups, as a guest.

COLOR_FACTS_JS = """() => {
  const rgb = (el, prop) => getComputedStyle(el)[prop].match(/\\d+/g).slice(0, 3).map(Number);
  return {
    theme: document.documentElement.dataset.bsTheme,
    surround: rgb(document.body, 'backgroundColor'),
    main: rgb(document.querySelector('main'), 'backgroundColor'),
    title: rgb(document.querySelector('main h1'), 'color'),
    link: rgb(document.querySelector('.mw-breadcrumb a'), 'color'),
    can: rgb(document.querySelector('.mw-can'), 'color'),
    cannot: rgb(document.querySelector('.mw-cannot'), 'color'),
    logo: document.querySelector('.mw-logo img').getBoundingClientRect().height,
  };
}"""


class IslingtonBrandingTests(AdminTestCase):

    def test_islington_membership_groups_light_and_dark(self):
        site_link = colors.parse_hex('#185945')
        surround = colors.parse_hex('#bfc3c5')
        for mode in ('light', 'dark'):
            with self.subTest(mode=mode):
                page = self.open_bs5('/microcosms/%d/memberships/' % manifest.ISLINGTON_FORUM_ID, host=ISLINGTON,
                                     color_mode=mode)
                self.assertGreater(page.locator('.mw-rows > li').count(), 1)
                facts = page.evaluate(COLOR_FACTS_JS)
                self.assertEqual(facts['theme'], mode)
                self.assertEqual(tuple(facts['surround']), surround, 'the Site surround')
                self.assertEqual(facts['logo'], 89)
                self.assertGreaterEqual(colors.contrast(facts['title'], facts['main']), 7)
                if mode == 'light':
                    self.assertEqual(tuple(facts['link']), site_link)
                else:
                    self.assertGreaterEqual(colors.contrast(facts['link'], facts['main']), colors.AA)
                # Can and cannot stay readable in both modes.
                for colour in (facts['can'], facts['cannot']):
                    self.assertGreaterEqual(colors.contrast(colour, facts['main']), 3.5)
                self.snap(page, 'BS5-14-branding-%s' % mode)
                page.context.close()
