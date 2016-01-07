import urllib.parse
import requests
from enum import Enum
from .api import ApiError

class OAuthScopes:

    class Linodes(Enum):
        view = 0
        create = 1
        modify = 2
        delete = 3

        def __repr__(self):
            return "linodes:{}".format(self.name)

    class Zones(Enum):
        view = 0
        create = 1
        modify = 2
        delete = 3

        def __repr__(self):
            return "zones:{}".format(self.name)

    class StackScripts(Enum):
        view = 0
        create = 1
        modify = 2
        delete = 3

        def __repr__(self):
            return "stackscripts:{}".format(self.name)

    _scope_families = {
        'linodes': Linodes,
        'zones': Zones,
        'stackscripts': StackScripts,
    }

    def parse(scopes):
        ret = []

        # special all-scope case
        if scopes == '*':
            return [ getattr(OAuthScopes._scope_families[s], 'delete')
                    for s in OAuthScopes._scope_families ]

        for scope in scopes.split(','):
            resource = access = None
            if ':' in scope:
                resource, access = scope.split(':')
            else:
                resource = scope
                access = '*'

            parsed_scope = OAuthScopes._get_parsed_scope(resource, access)
            if parsed_scope:
                ret.append(parsed_scope)

        return ret

    def _get_parsed_scope(resource, access):
        resource = resource.lower()
        access = access.lower()
        if resource in OAuthScopes._scope_families:
            if access == '*':
                access = 'delete'
            if hasattr(OAuthScopes._scope_families[resource], access):
                return getattr(OAuthScopes._scope_families[resource], access)

        return None

    def serialize(scopes):
        ret = ''
        if not type(scopes) is list:
            scopes = [ scopes ]
        for scope in scopes:
            ret += "{},".format(repr(scope))
        if ret:
            ret = ret[:-1]
        return ret

class LinodeLoginClient:
    def __init__(self, client_id, client_secret,
            base_url="https://login.linode.com"):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret

    def _login_uri(self, path):
        return "{}{}".format(self.base_url, path)

    def generate_login_url(self, scopes=None, redirect_uri=None):
        url = self.base_url + "/oauth/authorize"
        split = list(urllib.parse.urlparse(url))
        params = {
            "client_id": self.client_id,
        }
        if scopes:
            params["scopes"] = OAuthScopes.serialize(scopes)
        if redirect_uri:
            params["redirect_uri"] = redirect_uri
        split[4] = urllib.parse.urlencode(params)
        return urllib.parse.urlunparse(split)

    def finish_oauth(self, code):
        r = requests.post(self._login_uri("/oauth/token"), data={
                "code": code,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            })
        if r.status_code != 200:
            raise ApiError("OAuth token exchange failed", r)
        token = r.json()["access_token"]
        scopes = OAuthScopes.parse(r.json()["scopes"])
        return token, scopes