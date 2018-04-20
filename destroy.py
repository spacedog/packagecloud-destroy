#!/usr/bin/python
import sys
import requests
import yaml

api_url_base     = "https://packagecloud.io"


# Make api call to package cloud
def api_call(s, url_request, method = "get"):
    result = []
    page   = 1
    url    = api_url_base + url_request

    # Use global session
    r      = getattr(s,method)(url)
    result = r.json()

    # Check if there is multiple pages of data
    while (page * int(r.headers['Per-Page']) < int(r.headers['Total'])):
        page = page + 1
        url_next_page = "%s?page=%s" % (url, page)

        # get next page
        r = getattr(s,method)(url_next_page)

        # append  data to result
        result = result + r.json()

    return result

# Print packages to remove
def get_pkg_versions_to_destroy(s, packages, versions_to_keep):
    pkg_versions = {}
    versions     = {}
    for package in packages:
        # Proceed only if versions_count is greate then versions we would like to keep
        if package["versions_count"] > versions_to_keep:
            versions = api_call(s, package["versions_url"])
            pkg_versions.update({
                package["name"]: versions
            })

    return pkg_versions

def print_pkg_to_yank(pkg_versions, version_to_keep):

    for pkg in pkg_versions.keys():

        print "* %s:" % pkg

        pkg_versions_to_sort = {}
        for version in pkg_versions[pkg]:
            pkg_versions_to_sort[version["created_at"]] = [
                "%s-%s" % (version["version"], version["release"]),
                version["destroy_url"]
            ]

        i = 1
        for v in sorted(pkg_versions_to_sort.keys(), reverse = True):
            if i < version_to_keep:
                print "|-- %-2d %-25s create at %s" % (
                    i,
                    pkg_versions_to_sort[v][0],
                    v,
                )
            else:
                print "|-- %-2d %-25s create at %s (destroy url %s)" % (
                    i,
                    pkg_versions_to_sort[v][0],
                    v,
                    pkg_versions_to_sort[v][1],
                )
            i = i + 1




def main():

    # Read config file
    try:
        with open("config.yaml") as config_file:
            cfg = yaml.load(config_file)
    except IOError:
        print "[ERROR]: config.yaml file not found"
        sys.exit(1)

    # Configuraion check
    if not 'api_token' in cfg:
        print "[ERROR]: api_token must be defined"
        sys.exit(1)
    if not 'user' in cfg:
        print "[ERROR]: user must be defined"
        sys.exit(1)
    if not 'repository' in cfg:
        print "[ERROR]: repository must be defined"
        sys.exit(1)
    if not 'versions_to_keep' in cfg:
        cfg["versions_to_keep"] = 30

    s = requests.Session()
    s.auth = (cfg["api_token"], "")

    # get all packages rpm packages for EL
    if type(cfg["repository"]).__name__ == "str":
        api_url_request = "/api/v1/repos/{}/{}/packages/rpm/el.json".format(cfg["user"], cfg["repository"])
        versions = get_pkg_versions_to_destroy(s,api_call(s,api_url_request),cfg["versions_to_keep"])
        print_pkg_to_yank(versions, cfg["versions_to_keep"])
    elif type(cfg["repository"]).__name__ == "list":
        for repo in cfg["repository"]:
            print "[%s]" % repo
            api_url_request = "/api/v1/repos/{}/{}/packages/rpm/el.json".format(cfg["user"], repo)
            versions = get_pkg_versions_to_destroy(s,api_call(s,api_url_request), cfg["versions_to_keep"] )
            print_pkg_to_yank(versions, cfg["versions_to_keep"])
    else:
        print "[ERROR]: Unsupported type %s for repository. Use string or list" % type(cfg["repository"]).__name__
        s.close
        sys.exit(1)

    # close session
    s.close


if __name__ == "__main__":
    main()
