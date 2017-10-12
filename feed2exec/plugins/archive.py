import logging
import os.path
import requests
from feed2exec.utils import slug


DEFAULT_ARCHIVE_DIR = '/run/user/1000/'


def output(*args, feed=None, item=None, **kwargs):
    # make a safe path from the item name
    path = slug(item.get('title', 'no-name'))
    # take the archive dir from the user or use the default
    archive_dir = ' '.join(args) if args else DEFAULT_ARCHIVE_DIR
    # put the file in the archive directory
    path = os.path.join(archive_dir, path)
    # only operate on items that actually have a link
    if item.get('link'):
        # tell the user what's going on, if verbose
        # otherwise, we try to stay silent if all goes well
        logging.info('saving feed item %s to %s from %s',
                     item.get('title'), path, item.get('link'))
        # fetch the URL in memory
        result = requests.get(item.get('link'))
        if result.status_code != requests.codes.ok:
            logging.warning('failed to fetch link %s: %s',
                            item.get('link'), result.status_code)
            # make sure we retry next time
            return False
        # open the file
        with open(path, 'w') as archive:
            # write the response
            archive.write(result.text)
        return True
    else:
        logging.info('no link for feed item %s, not archiving',
                     item.get('title'))
        # still consider the item processed, as there's nothing to archive
        return True
