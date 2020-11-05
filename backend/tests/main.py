import gi
import os
import sys
import json
import tempfile

gi.require_version("OSTree", "1.0")

from gi.repository import OSTree, Gio
from fastapi.testclient import TestClient
from lxml import etree

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

workspace = None
client = None


def get_expected_json_result(test_name):
    path = os.path.join("tests", "results", f"{test_name}.json")
    with open(path) as result:
        return json.load(result)


def get_expected_xml_result(test_name):
    path = os.path.join("tests", "results", f"{test_name}.xml")
    with open(path) as result:
        return etree.fromstring(result.read().encode("utf-8"))


def setup_module():
    global workspace, client

    workspace = tempfile.TemporaryDirectory()

    installation_path = os.path.join(workspace.name, "flatpak")
    repo_path = os.path.join(installation_path, "repo")

    os.mkdir(installation_path)
    os.environ["FLATPAK_USER_DIR"] = installation_path

    file = Gio.File.new_for_path(repo_path)
    repo = OSTree.Repo.new(file)
    repo.create(OSTree.RepoMode.BARE, None)

    from app import config

    config.settings.ostree_repo = repo_path
    config.settings.appstream_repos = "tests/appstream"

    from app import main

    with TestClient(main.app) as client_:
        client = client_


def teardown_module():
    workspace.cleanup()


def test_update():
    response = client.post("/v1/apps/update")
    assert response.status_code == 200


def test_apps():
    response = client.get("/v1/apps")
    assert response.status_code == 200
    assert response.json() == get_expected_json_result("test_apps")


def test_apps_by_category():
    response = client.get("/v1/apps/category/Game")
    assert response.status_code == 200
    assert response.json() == get_expected_json_result("test_apps_by_category")


def test_apps_by_appid():
    response = client.get("/v1/apps/org.sugarlabs.Maze")
    assert response.status_code == 200
    assert response.json() == get_expected_json_result("test_apps_by_appid")


def test_appstream_by_appid():
    response = client.get("/v1/appstream/org.sugarlabs.Maze")
    assert response.status_code == 200
    assert response.json() == get_expected_json_result("test_appstream_by_appid")


def test_search_query_by_appid():
    response = client.get("/v1/apps/search/org.sugarlabs.Maze")
    assert response.status_code == 200
    assert response.json() == get_expected_json_result("test_search_query_by_appid")


def test_collection_by_recently_updated():
    response = client.get("/v1/apps/collection/recently-updated/1")
    assert response.status_code == 200
    assert response.json() == get_expected_json_result(
        "test_collection_by_recently_updated"
    )


def test_feed_by_recently_updated():
    response = client.get("/v1/feed/recently-updated")
    assert response.status_code == 200

    feed = etree.fromstring(response.text.encode("utf-8"))
    expected = get_expected_xml_result("test_feed_by_recently_updated")

    # Remove runtime-generated dates
    for component in [feed, expected]:
        channel = component.find("channel")
        date = channel.find("lastBuildDate")
        channel.remove(date)

    assert etree.tostring(feed) == etree.tostring(expected)


def test_feed_by_new():
    response = client.get("/v1/feed/new")
    assert response.status_code == 200

    feed = etree.fromstring(response.text.encode("utf-8"))
    expected = get_expected_xml_result("test_feed_by_new")

    # Remove runtime-generated dates
    for component in [feed, expected]:
        channel = component.find("channel")
        date = channel.find("lastBuildDate")
        channel.remove(date)

    assert etree.tostring(feed) == etree.tostring(expected)


def test_status():
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == get_expected_json_result("test_status")