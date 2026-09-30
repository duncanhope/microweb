"""The conversations and comments family on Bootstrap 5 (BS5-08): conversation.html,
comment.html, the comment and comment box includes, the comment and conversation
forms and the Formatting help modal, with their scripts and Sass partial."""
import json
import os
import re
from pathlib import Path

from django.conf import settings
from django.template import engines
from django.test import RequestFactory, SimpleTestCase

from core.api.resources import Comment, Conversation
from core.forms.forms import CommentForm, ConversationCreate, ConversationEdit
from core.tests.test_bs5_base import make_site, make_user
from core.views import build_pagination_links

REPO = Path(settings.PROJECT_ROOT).parent
DATA = Path(__file__).resolve().parent / 'data'
PARTIAL = REPO / 'core' / 'static' / 'themes' / '1' / 'scss' / '_conversations.scss'
SCRIPTS = REPO / 'core' / 'static' / 'js' / 'bs5'

# Every template the family owns in core/templates_bs5/.
FAMILY = [
    'conversation.html', 'comment.html', 'block_comments.html', 'block_comment_single.html',
    'forms/block_comment_box.html', 'forms/create_comment.html', 'forms/conversation.html',
    'modal_formatting_help.html', 'forms/content-moderation.html',
]
FAMILY_SCRIPTS = ['simpleEditor.js', 'comments.js', 'attachments.js', 'mentions.js']

# The lane 6 check: no hex colour and no rgb()/rgba() in the partial.
COLOUR_LITERAL = re.compile(r'#[0-9a-fA-F]{3,8}|rgba?\(')


class Bs5ConversationsTests(SimpleTestCase):

    def setUp(self):
        with open(DATA / 'conversation_with_paginated_comments.json') as f:
            data = json.load(f)['data']
        items = data['comments']['items']
        # A reply, and a comment with attachments.
        items[1]['inReplyTo'] = items[0]['id']
        items[1]['meta']['links'].append({'rel': 'inReplyToAuthor', 'href': '/api/v1/profiles/5', 'title': 'Frodo'})
        items[2]['attachments'] = 2
        self.content = Conversation.from_api_response(data)
        self.pagination = build_pagination_links(data['comments']['links'], self.content.comments)
        self.permissions(siteOwner=False, update=False, owner=False, moderator=False)

    def permissions(self, **values):
        for key, value in values.items():
            setattr(self.content.meta.permissions, key, value)

    def render(self, name, user=None, **extra):
        request = RequestFactory().get('/conversations/1/')
        context = {
            'site': make_site(), 'user': user, 'content': self.content, 'item_type': 'conversation',
            'pagination': self.pagination, 'attachments': {},
            'comment_form': CommentForm(initial={'itemId': 1, 'itemType': 'conversation'}),
        }
        context.update(extra)
        return engines['bs5'].get_template(name).render(context, request)

    def assert_bootstrap_5_only(self, html):
        self.assertNotIn('data-toggle=', html)
        self.assertNotIn('data-target=', html)
        self.assertNotIn('data-dismiss=', html)
        self.assertNotIn('sprite-', html)
        self.assertNotIn('$(', html)

    def test_every_family_template_is_served_from_the_bs5_tree(self):
        for name in FAMILY:
            with self.subTest(template=name):
                origin = engines['bs5'].get_template(name).origin.name
                self.assertEqual(os.path.dirname(os.path.relpath(origin, settings.BS5_TEMPLATE_DIR)),
                                 os.path.dirname(name))

    def test_every_family_template_renders_without_bootstrap_3_or_jquery(self):
        comment = self.content.comments.items[1]
        for name in FAMILY:
            for user in (None, make_user()):
                with self.subTest(template=name, member=bool(user)):
                    html = self.render(name, user=user, comment=comment, comments=[comment],
                                       form=ConversationCreate(), forloop={'counter': 1})
                    self.assert_bootstrap_5_only(html)

    def test_partial_has_no_colour_literals(self):
        source = PARTIAL.read_text()
        self.assertEqual(COLOUR_LITERAL.findall(source), [])
        self.assertIn('@import "conversations";', (PARTIAL.parent / 'site.scss').read_text())

    def test_scripts_are_modules_without_jquery(self):
        for name in FAMILY_SCRIPTS:
            with self.subTest(script=name):
                source = (SCRIPTS / name).read_text()
                code = re.sub(r'(?m)^\s*//.*$', '', source)
                self.assertIsNone(re.search(r'\$\(|\$\.|jQuery', code))
                self.assertRegex(source, r'(?m)^(import|export) ')

    # conversation.html ------------------------------------------------------

    def test_guest_conversation(self):
        html = self.render('conversation.html')
        self.assertEqual(html.count('<li id="comment'), 25)
        self.assertIn('<h1 class="mw-item-title" itemprop="name"><a id="title" href="/conversations/1/">Generated</a></h1>', html)
        # Post a reply opens the sign-in modal; the reply box asks guests to sign in.
        self.assertIn('data-bs-toggle="modal" data-bs-target="#modal-signin">', html)
        self.assertIn('>Sign in to post a reply</button>', html)
        self.assertNotIn('<textarea', html)
        self.assertNotIn('data-mw-reply ', html)
        self.assertNotIn('comments.js', html)
        self.assertNotIn('formatting-help-modal', html)
        self.assertNotIn('data-mw-subscribe', html)
        self.assertIn('placeholder="Search conversation" aria-label="Search this conversation"', html)

    def test_member_conversation(self):
        html = self.render('conversation.html', user=make_user())
        self.assertIn('<script type="module" src="/static/js/bs5/comments.js">', html)
        self.assertEqual(html.count('id="formatting-help-modal"'), 1)
        self.assertIn('<a id="post-a-reply-handle" href="#reply"', html)
        self.assertNotIn('edit-conversation', html)
        # The reply box: a form posting a new comment to this conversation.
        reply = html.split('data-mw-reply-default')[1]
        self.assertIn('<form action="/comments/create/" method="POST" enctype="multipart/form-data" novalidate>', reply)
        self.assertIn('<input type="hidden" name="itemId" value="1">', reply)
        self.assertIn('<input type="hidden" name="itemType" value="conversation">', reply)
        self.assertIn('<input type="hidden" name="inReplyTo" value="0">', reply)
        self.assertRegex(reply, r'<textarea class="form-control mw-editor-input" placeholder="Enter your text here..."\s+'
                                r'aria-label="Your comment" name="markdown" maxlength="50000" required>')
        self.assertIn('<input type="file" name="attachments" multiple', reply)
        self.assertEqual(reply.count('data-mw-format='), 7)
        # The Follow control and Controls.
        self.assertIn('data-mw-subscribe data-url="/watchers/" data-item-type="conversation" data-item-id="1"', html)
        self.assertIn('>Ignore</button>', html)
        # Reply on each comment, with what comments.js needs.
        self.assertIn('data-mw-reply data-action="/comments/create/" data-ref="2" aria-expanded="false">', html)

    def test_member_who_may_edit(self):
        self.permissions(update=True)
        html = self.render('conversation.html', user=make_user())
        self.assertIn('id="edit-conversation" href="/conversations/1/edit/"', html)

    def test_closed_conversation_has_no_reply_box(self):
        self.content.meta.flags['open'] = False
        html = self.render('conversation.html', user=make_user())
        self.assertNotIn('data-mw-reply-default', html)
        self.assertNotIn('data-action="/comments/create/"', html, 'no Reply on a closed conversation')

    def test_pagination_top_and_bottom(self):
        html = self.render('conversation.html')
        self.assertEqual(html.count('name="paginationByOffset"'), 2)
        self.assertIn('<div class="mw-list-footer">', html)

    # block_comment_single.html -------------------------------------------------

    def comment_html(self, index, user=None, **extra):
        comment = self.content.comments.items[index]
        return self.render('block_comment_single.html', user=user, comment=comment,
                           forloop={'counter': index + 1}, **extra)

    def test_comment_for_a_guest(self):
        html = self.comment_html(1)
        self.assertIn('<li id="comment2" class="mw-comment"', html)
        self.assertIn('<strong itemprop="name">Frodo</strong>', html)
        self.assertIn('class="mw-prose mw-comment-body" itemprop="text"', html)
        self.assertIn('<a href="/comments/2/" itemprop="discussionUrl">#2</a>', html)
        # In reply to.
        self.assertIn('<a href="/comments/1/incontext/" itemprop="url">in reply to</a> <a href="/profiles/5/">@Frodo</a>', html)
        self.assertIn('bi-arrow-right', html)
        self.assertNotIn('mw-comment-actions', html)

    def test_comment_actions(self):
        html = self.comment_html(0, user=make_user())
        self.assertIn('<button type="button" class="btn btn-link mw-comment-reply" data-mw-reply', html)
        self.assertNotIn('>Delete</button>', html)
        self.assertNotIn('data-comment-id', html)

        # Your own comment: Edit, and no Reply.
        own = make_user()
        own.id = 5
        html = self.comment_html(0, user=own)
        self.assertNotIn('mw-comment-reply', html)
        self.assertIn('data-mw-reply data-action="/comments/1/edit/" data-source="/comments/1/" data-comment-id="1" '
                      'data-num-attachments="0"', html)

        # Site owners delete.
        self.permissions(siteOwner=True)
        html = self.comment_html(0, user=make_user())
        self.assertIn('<form action="/comments/1/delete/" method="POST">', html)
        self.assertIn('<button type="submit" class="btn btn-link">Delete</button>', html)

    def test_single_comment_permalink(self):
        html = self.comment_html(0, hide_permalink=True)
        self.assertIn('role="img" aria-label="Link to this comment"', html)

    def test_attachments(self):
        files = {'total': 7, 'items': [
            {'file_ext': 'png', 'file_name': 'a.png', 'meta': {'links': [{'href': '/api/v1/files/a'}]}},
            {'file_ext': 'pdf', 'file_name': 'b.pdf', 'meta': {'links': [{'href': '/api/v1/files/b'}]}},
        ]}
        html = self.comment_html(2, attachments={'3': files})
        self.assertIn('<strong>7 Attachments</strong>', html)
        self.assertIn('<ul class="list-unstyled mw-attachment-thumbs">', html)
        # Other files first, then images.
        self.assertLess(html.index('b.pdf'), html.index('a.png'))
        self.assertIn('<img src="https://lfgss.microcosm.app/api/v1/files/a" alt="a.png" title="a.png">', html)
        self.assertNotIn('style=', html)

    # The comment box -------------------------------------------------------------

    def test_component_box_has_no_form(self):
        html = engines['bs5'].from_string('{% load commentBox %}{% commentBox as_component=True name="firstcomment" %}') \
            .render({'user': make_user(), 'site': make_site()})
        self.assertNotIn('<form', html)
        self.assertIn('id="mw-editor-firstcomment" name="firstcomment" maxlength="5000"', html)
        self.assertNotIn(' required', html)
        self.assertIn('data-mw-attachments', html)
        self.assertNotIn('Post reply', html)

        html = engines['bs5'].from_string('{% load commentBox %}{% commentBox as_component=True no_attachments=True %}') \
            .render({'user': make_user(), 'site': make_site()})
        self.assertNotIn('mw-editor-footer', html)

    def test_guest_box(self):
        html = self.render('forms/block_comment_box.html')
        self.assertIn('<fieldset class="mw-editor-toolbar" role="toolbar" aria-label="Formatting" disabled>', html)
        self.assertIn('onclick="authSignin();">Sign in to post a reply</button>', html)

    # comment.html and forms/create_comment.html -----------------------------------------

    def single_comment(self):
        with open(DATA / 'conversation_with_paginated_comments.json') as f:
            data = json.load(f)['data']['comments']['items'][0]
        data['meta']['links'].append({'rel': 'up', 'href': '/api/v1/conversations/1', 'title': 'Generated'})
        data['meta']['links'].append({'rel': 'commentPage', 'href': '/api/v1/conversations/1?offset=0'})
        return Comment.from_api_response(data)

    def test_single_comment_page(self):
        comment = self.single_comment()
        html = self.render('comment.html', content=comment)
        self.assertIn('<a href="/conversations/1/">Generated</a></h1>', html)
        self.assertIn('You are reading a single comment by <a href="/profiles/5/">@Frodo</a>', html)
        self.assertIn('<ul class="list-unstyled mw-comments mw-comments-highlighted">', html)
        self.assertNotIn('<template', html)

        html = self.render('comment.html', content=comment, user=make_user())
        self.assertIn('data-mw-comments data-mw-open-highlighted', html)
        self.assertIn('<template data-mw-reply-template>', html)
        self.assertIn('/static/js/bs5/comments.js', html)
        self.assertEqual(html.count('id="formatting-help-modal"'), 1)

    def test_create_comment_fallback_page(self):
        html = self.render('forms/create_comment.html', content=self.single_comment(), user=make_user(),
                           error='Sorry, one of your files was over 5MB. Please try again.')
        self.assertIn('<div class="alert alert-warning mw-alert">Sorry, one of your files was over 5MB.', html)
        # A comment that failed to validate leaves no comment in the context; the page still renders.
        html = self.render('forms/create_comment.html', content='', user=make_user(), form=CommentForm({}))
        self.assertIn('bs5.min.css', html)
        self.assertNotIn('<li id="comment', html)

    # forms/conversation.html -------------------------------------------------------------

    def test_post_a_conversation_form(self):
        html = self.render('forms/conversation.html', user=make_user(), form=ConversationCreate())
        self.assertIn('<form action="" method="POST" id="conversationForm" class="mw-item-form" '
                      'enctype="multipart/form-data" novalidate data-mw-validate>', html)
        self.assertIn('maxlength="150" required value="">', html)
        self.assertIn('<div class="invalid-feedback">Please add a subject</div>', html)
        self.assertIn('<label class="form-label" for="mw-editor-firstcomment">What is it you want to say?</label>', html)
        self.assertIn('>Post conversation</button>', html)
        self.assertIn('/static/js/bs5/comments.js', html)
        self.assertNotIn('editReason', html)

    def test_edit_conversation_form_with_errors(self):
        form = ConversationEdit({'title': '', 'id': 1, 'microcosmId': 1})
        form.is_valid()
        html = self.render('forms/conversation.html', user=make_user(), form=form, state_edit=True)
        self.assertIn('class="form-control is-invalid" id="title"', html)
        self.assertIn('class="form-control is-invalid" id="editReason"', html)
        self.assertIn('>Edit conversation</button>', html)
        self.assertNotIn('firstcomment', html)

    def test_formatting_help_modal(self):
        html = self.render('modal_formatting_help.html')
        self.assertIn('<div id="formatting-help-modal" class="modal fade" tabindex="-1" aria-labelledby="formatting-help-title"', html)
        self.assertIn('data-bs-dismiss="modal" aria-label="Close"', html)
