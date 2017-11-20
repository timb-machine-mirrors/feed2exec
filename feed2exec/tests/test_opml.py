from glob import glob
import os.path

import pytest

from feed2exec.feeds import (FeedManager)
from feed2exec.tests.fixtures import (test_db, conf_path)  # noqa
import feed2exec.utils as utils

testdir = utils.find_test_file()


@pytest.mark.parametrize("opmlpath", glob(os.path.join(testdir, '*.opml')))  # noqa
def test_import(test_db, conf_path, opmlpath):
    with open(utils.find_test_file(opmlpath), 'rb') as opmlfile, \
         open(utils.find_test_file(opmlpath[:-4] + 'ini')) as expected:
        FeedManager().opml_import(opmlfile)
        assert conf_path.check()
        assert expected.read() == conf_path.read()
    conf_path.remove()
