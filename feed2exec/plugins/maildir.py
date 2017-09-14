from __future__ import division, absolute_import
from __future__ import print_function


from collections import defaultdict
import calendar
import datetime
import getpass
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import mailbox
import os.path
import socket
import time

import feed2exec
import feed2exec.utils as utils
from feed2exec.plugins.html2text import filter as html2text_filter


boundary = None


def make_message(feed, entry, to_addr=None, cls=email.message.Message):
    """generate a message from the feed

    .. todo:: figure out a way to render multi-element Atom feeds.
    .. todo:: should be moved to utils?"""
    params = defaultdict(str)
    params.update(entry)
    cs = email.charset.Charset('utf-8')
    cs.header_encoding = email.charset.QP
    cs.body_encoding = email.charset.QP
    msg = MIMEMultipart('alternative', boundary)
    html_parts = []
    for content in params.get('content', []):
        if not content.value:
            continue
        if content.type == 'application/xhtml+xml':
            content.type = 'text/html'
        basetype, subtype = content.type.split('/', 1)
        if basetype != 'text':
            logging.warning('unhandled mime type %s, skipped', content.type)
            continue
        html = MIMEText(content.value.encode('utf-8'),
                        _subtype=subtype, _charset=cs)
        html.replace_header('Content-Transfer-Encoding', 'quoted-printable')
        if subtype == 'html':
            html_parts.append(content.value)
        msg.attach(html)

    if not msg.get_payload() and params.get('summary'):
        # no content found, fallback on summary
        content = params.get('summary')
        # stupid heuristic to guess if content is HTML, because
        # feedparser sure won't tell
        subtype = 'html' if '<' in content else 'plain'
        part = MIMEText(content.encode('utf-8'),
                        _subtype=subtype, _charset=cs)
        if subtype == 'plain':
            msg = part
        else:
            html_parts.append(params.get('summary'))
            msg.attach(part)
    for content in html_parts:
        # plain text version available
        params['content_plain'] = html2text_filter.parse(content)
        body = u'''{link}

{content_plain}'''.format(**params)
        text = MIMEText(body.encode('utf-8'),
                        _subtype='plain', _charset=cs)
        text.replace_header('Content-Transfer-Encoding', 'quoted-printable')
        msg.attach(text)
    payload = msg.get_payload()
    if len(payload) == 1:
        msg = payload.pop()
    msg = cls(msg)

    # feedparser always returns UTC times and obliterates original
    # TZ information. it does do the conversion correctly,
    # however, so just assume UTC.
    #
    # also, default on the feed updated date
    orig = timestamp = datetime.datetime.utcnow().timestamp()
    timestamp = entry.get('updated_parsed') or orig
    if isinstance(timestamp, (datetime.datetime,
                              datetime.date,
                              datetime.time)):
        try:
            timestamp = timestamp.timestamp()
        except AttributeError:
            # py2, less precision
            timestamp = int(timestamp.strftime('%s'))
    elif isinstance(timestamp, (time.struct_time, tuple)):
        timestamp = calendar.timegm(timestamp)
    msg['Date'] = email.utils.formatdate(timeval=timestamp,
                                         localtime=False)
    msg['To'] = to_addr or "%s@%s" % (getpass.getuser(), socket.getfqdn())
    params = {'name': feed.get('name'),
              'email': msg['To']}
    if 'author_detail' in entry:
        params.update(entry['author_detail'])
    elif 'author_detail' in feed:
        params.update(feed['author_detail'])
    msg['From'] = '{name} <{email}>'.format(**params)
    msg['Subject'] = entry.get('title', feed.get('title', u''))
    # workaround feedparser bug:
    # https://github.com/kurtmckee/feedparser/issues/112
    msg['Message-ID'] = utils.slug(entry.get('id', entry.get('title')))
    msg['User-Agent'] = "%s (%s)" % (feed2exec.__prog__,
                                     feed2exec.__version__)
    msg['Precedence'] = 'list'
    msg['Auto-Submitted'] = 'auto-generated'
    if entry.get('link'):
        msg['Archive-At'] = entry.get('link')
    return msg, timestamp


class output(object):
    """
    The maildir plugin will save a feed item into a Maildir folder.

    The configuration is a little clunky, but it should be safe
    against hostile feeds.

    :param str to_addr: the email to use as "to" (defaults to
                        USER@localdomain)

    :param dict feed: the feed

    :param dict item: the updated item
    """

    def __init__(self, to_addr=None, feed=None, entry=None, lock=None,
                 *args, **kwargs):
        prefix = os.path.expanduser(feed.get('mailbox', '~/Maildir'))
        msg, timestamp = make_message(feed=feed,
                                      entry=entry,
                                      to_addr=to_addr,
                                      cls=mailbox.MaildirMessage)
        msg.set_date(timestamp)
        utils.make_dirs_helper(prefix)
        folder = os.path.basename(os.path.abspath(utils.slug(feed.get('name'))))  # noqa
        # allow user to override our folder
        folder = feed.get('folder', folder)
        path = os.path.join(prefix, folder)
        logging.debug('established folder path %s', path)
        if lock:
            lock.acquire()
        maildir = mailbox.Maildir(path, create=True)
        self.key = maildir.add(msg)
        maildir.flush()
        if lock:
            lock.release()
        guid = entry.get('guid', entry.get('link', '???'))
        logging.info('saved entry %s to %s',
                     guid, os.path.join(path, 'new', self.key))
