#!/usr/bin/env python

import logging
import requests

from prometheus_client import start_http_server, Gauge, Summary
from time import sleep

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

log = logging.getLogger()

sleep_time = 60 * 15

REQUEST_TIME = Summary(
    name="func_processing_seconds",
    documentation="Time spent processing functions",
    labelnames=["func"],
)


@REQUEST_TIME.labels(func="get_devices").time()
def get_devices():
    """A dummy function that takes some time."""
    return requests.get(
        "https://raw.githubusercontent.com/PixelBuildsROM/pixelbuilds_devices/main/devices.json"
    ).json()


@REQUEST_TIME.labels(func="get_releases").time()
def get_releases(device):
    releases_github = {}
    releases_gitea = {}

    response_github = requests.get(
        f"https://api.github.com/repos/PixelBuilds-Releases/{device}/releases"
    )

    if response_github.status_code == 200:
        releases_github = response_github.json()

    response_gitea = requests.get(
        f"https://git.pixelbuilds.org/api/v1/repos/releases/{device}/releases"
    )

    if response_gitea.status_code == 200:
        releases_gitea = response_gitea.json()

    return releases_github, releases_gitea


if __name__ == "__main__":
    log.info("Starting Prometheus server")
    start_http_server(9000)

    metric = Gauge(
        name="downloads",
        documentation="Total downloads for release",
        labelnames=["release", "codename", "source"],
        namespace="pixelbuilds",
    )

    _total = metric.labels(release=None, codename=None, source=None)
    _total_github = metric.labels(release=None, codename=None, source="github")
    _total_gitea = metric.labels(release=None, codename=None, source="gitea")

    while True:
        log.info("Getting metrics")

        _total.set(0)
        _total_github.set(0)
        _total_gitea.set(0)

        devices = [d["codename"] for d in get_devices()]

        for device in devices:
            releases_github, releases_gitea = get_releases(device)

            for release in releases_github:
                for asset in release["assets"]:
                    if not asset["name"].startswith("PixelBuilds_") and not asset[
                        "name"
                    ].endswith(".zip"):
                        continue

                    _total.inc(asset["download_count"])
                    _total_github.inc(asset["download_count"])

                    release_name = (
                        release["name"]
                        .replace(f"PixelBuilds_{device}-", "")
                        .replace("-release", "")
                    )

                    metric.labels(
                        release=release_name, codename=device, source="github"
                    ).set(asset["download_count"])

            for release in releases_gitea:
                for asset in release["assets"]:
                    if not asset["name"].startswith("PixelBuilds_") and not asset[
                        "name"
                    ].endswith(".zip"):
                        continue

                    _total.inc(asset["download_count"])
                    _total_gitea.inc(asset["download_count"])

                    release_name = (
                        release["name"]
                        .replace(f"PixelBuilds_{device}-", "")
                        .replace("-release", "")
                    )

                    metric.labels(
                        release=release_name, codename=device, source="gitea"
                    ).set(asset["download_count"])

        log.info(f"Done, going to sleep for {sleep_time}s")
        sleep(sleep_time)
