#!/usr/bin/env python
import os
import re
import requests
import argparse

api_url_base = "https://packagecloud.io"


# Make api call to package cloud
def api_call(session, url_request, method="get"):
    page = 1
    url = api_url_base + url_request

    # Use global session
    url_attr = getattr(session, method)(url)
    result = url_attr.json()

    # Check if there is multiple pages of data
    if 'Per-Page' in url_attr.headers and 'Total' in url_attr.headers:
        while page * int(url_attr.headers['Per-Page']) < int(url_attr.headers['Total']):
            page = page + 1
            url_next_page = "%s?page=%s" % (url, page)

            # get next page
            url_next_page_attr = getattr(session, method)(url_next_page)

            # append  data to result
            result = result + url_next_page_attr.json()

    return result


# Print packages to remove
def get_pkg_versions_to_destroy(session, packages, keep, sub_project="", version="", release=""):
    pkg_versions = {}
    print "=" * 80
    for package in packages:
        # look for specific package if sub_project is set
        if len(sub_project) > 0:
            if package["name"] == sub_project:
                print "[INFO]: Package: %s" % package["name"]
                versions = api_call(session, package["versions_url"])
                pkg_versions.update({package["name"]: search_for_version(versions, keep, version, release)})

            else:
                # continue with next package
                continue
        # if sub_project isn't set proceed with all packages
        else:
            print "[INFO]: Package: %s" % package["name"]
            versions = api_call(session, package["versions_url"])
            pkg_versions.update({package["name"]: search_for_version(versions, keep, version, release)})

    versions_to_destroy = []
    for pkg in pkg_versions.keys():
        print "* %s:" % pkg

        pkg_versions_to_sort = {}
        for version in pkg_versions[pkg]:
            pkg_versions_to_sort[version["created_at"]] = [
                "%s-%s" % (version["version"], version["release"]),
                version["destroy_url"]
            ]

        i = 1
        for v in sorted(pkg_versions_to_sort.keys(), reverse=True):
            if i > keep:
                url = pkg_versions_to_sort[v][1]
                print "%s %s" % (
                    os.path.dirname(url.replace("/api/v1/repos/", "")),
                    os.path.basename(url)
                )
                versions_to_destroy.append(url)
            i = i + 1
    print "=" * 80
    return versions_to_destroy


def search_for_version(versions, keep, version="", release=""):
    versions_result = []
    for v in versions:
        version_to_append = True
        # if version is set then look for a version
        if version:
            if not v['version'].find(version) == 0:
                version_to_append = False

        # basically the same for release
        if release:
            if not v['release'].find(release) == 0:
                version_to_append = False

        if version_to_append:
            versions_result.append(v)

    print "  Total %s versions found. Need to keep: %s" % (len(versions_result), keep)
    return versions_result


def destroy_packages(session, versions):
    for url in versions:
        print "Deleting: %s/%s" % (
            os.path.dirname(url.replace("/api/v1/repos/", "")),
            os.path.basename(url)
        )
        ret_val = api_call(session, url, "delete")
        if ret_val:
            print "ERROR: Received non-empty response from server: %s" % str(ret_val)


def gate_deletion():
    while True:
        user_input = raw_input("Would you like to delete the packages listed above? [y/N]: ")
        if not user_input or re.search(r"^[nN]", user_input):
            return False
        elif re.search(r"^[yY]", user_input):
            return True


def main():
    # Command line args
    parser = argparse.ArgumentParser(description='Command line parameters')
    parser.add_argument('--api_token',  dest="api_token",  help="api key to use to connect to packagecloud")
    parser.add_argument('--keep',       dest="keep",       type=int, metavar="N", help="keep the N most recent versions")
    parser.add_argument('--user',       dest="user",       help="username to use to connect to packagecloud")
    parser.add_argument('--repo',       dest="repo",       help="repository name where to search packages", action="append", default=[])
    parser.add_argument('--subproject', dest="subproject", nargs="?", help="subproject name to search for", default="")
    parser.add_argument('--version',    dest="version",    nargs="?", help="version to search for", default="")
    parser.add_argument('--release',    dest="release",    nargs="?", help="release to search for", default="")
    parser.add_argument('--yes',        dest="yes",        help="answer 'yes' to all prompts", action="store_true")

    args = parser.parse_args()

    session = requests.Session()
    session.auth = (args.api_token, "")

    # get all packages rpm packages for EL
    for repo in args.repo:
        api_url_request = "/api/v1/repos/{}/{}/packages/rpm/el.json".format(args.user, repo)
        versions = get_pkg_versions_to_destroy(session, api_call(session, api_url_request),
                                               args.keep, args.subproject, args.version, args.release)
        if not versions:
            print "No packages eligible for deletion."
        elif args.yes or gate_deletion():
            destroy_packages(session, versions)

    # close session
    session.close


if __name__ == "__main__":
    main()
