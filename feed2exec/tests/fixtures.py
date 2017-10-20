import pytest

from feed2exec.feeds import (SqliteStorage, ConfFeedStorage,
                             FeedStorageBase)
import feed2exec.plugins.maildir


@pytest.fixture(scope='session')
def test_db(tmpdir_factory):
    path = tmpdir_factory.mktemp('feed2exec').join('feed2exec.db')
    SqliteStorage.path = str(path)
    return path


@pytest.fixture(scope='session')
def conf_path(tmpdir_factory):
    path = tmpdir_factory.mktemp('feed2exec').join('feed2exex.ini')
    ConfFeedStorage.path = str(path)
    return path


@pytest.fixture(autouse=True)
def static_boundary(monkeypatch):
    monkeypatch.setattr(feed2exec.email, 'boundary',
                        '===============testboundary==')


@pytest.fixture()
@pytest.mark.usefixtures('betamax_session')
def betamax(betamax_session):
    assert betamax_session
    FeedStorageBase.sessionConfig(betamax_session)
    FeedStorageBase._session = betamax_session
    return betamax_session
