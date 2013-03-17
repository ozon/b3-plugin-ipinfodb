# -*- coding: UTF-8 -*-

# Copyright (c) 2012 Harry Gabriel <rootdesign@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import b3
import b3.clients
import b3.events
from threading import Thread
from b3.plugin import Plugin
try:
    import requests
except ImportError:
    print 'Need requests module. http://docs.python-requests.org/en/latest/user/install/#install'

__author__ = 'ozon'
__version__ = '0.1.0'


class IpinfodbPlugin(Plugin):
    _adminPlugin = None

    def onLoadConfig(self):
        # load API Key from config
        try:
            self._api_key = self.config.get('settings', 'api_key')
            if not self._api_key:
                raise ValueError('No API Key is set.')
        except ValueError, err:
            self.error(err)
            #self.disable() # dosnt work - TODO: handle missing API Key/Plugin disabling right
            #self.info('Plugin is disabled.')
            return False
        except Exception, err:
            self.debug(err)

        self.ipinfodb_api = IPinfo(api_key=self._api_key)

    def onStartup(self):
        # load the admin plugin
        self._adminPlugin = self.console.getPlugin('admin')

        # add attr to Client object
        if not hasattr(b3.clients.Client, 'countryName'):
            setattr(b3.clients.Client, 'countryName', None)
        if not hasattr(b3.clients.Client, 'countryCode'):
            setattr(b3.clients.Client, 'countryCode', None)

        # register event "Client Connect"
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)

        self.ipinfodb_cache = IpinfodbStorage(self)

    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.do_client_location_update(event.client)

    def _setClientLocation(self, client, countryCode, countryName):
        self.debug('Set countryName %s' % countryName.title())
        setattr(client, 'countryCode', countryCode)
        setattr(client, 'countryName', countryName.title())

    def callback_client_update(self, client, data):
        if data['statusCode'] == 'OK':
            countryName = str(data['countryName'])
            countryCode = str(data['countryCode'])
            # set client attr
            self._setClientLocation(client, countryCode, countryName)
            # save result to DB
            self.ipinfodb_cache.create(client)

    def do_client_location_update(self, client):
        self.debug('Start location update for %s' % client.name)
        _result = self.ipinfodb_cache.getCountry(cid=client.id)
        if _result and 'countryCode' in _result and 'countryName' in _result:
            self.debug('Found location infos in DB')
            self._setClientLocation(client, _result['countryCode'], _result['countryName'])
        else:
            self.debug('Update location infos from IPInfodb.com')
            if client.ip:
                Ipinfodb_query(self.ipinfodb_api, ip=client.ip, callback=self.callback_client_update,
                               callback_args=(client,)).start()
            else:
                self.error('No IP for %s found' % client.name)


class Ipinfodb_query(Thread):
    def __init__(self, ipinfo_api, name=None, ip=None, callback=None, callback_args=()):
        Thread.__init__(self, name=name, )
        self.__ipinfo_api = ipinfo_api
        self.__ip = ip
        self.__callback = callback
        self.__callback_args = callback_args

    def run(self):
        data = self.__ipinfo_api.getCountry(self.__ip)

        if self.__callback:
            self.__callback(*self.__callback_args, data=data)


class IPinfo(object):
    def __init__(self, api_key):
        self._api_key = api_key

    def _fetch_from_API(self, ip_addr=None, baseurl='http://api.ipinfodb.com/v3/ip-country/'):
        payload = {'timezone': False, 'format': 'json', 'key': self._api_key, 'ip': ip_addr}
        r = requests.get(baseurl, params=payload, timeout=30)
        if r.status_code == requests.codes.ok:
            return r.json()

    def getCountry(self, ip_addr=None):
        baseurl = 'http://api.ipinfodb.com/v3/ip-country/'
        return self._fetch_from_API(ip_addr, baseurl)

    def getCity(self, ip_addr=None):
        baseurl = 'http://api.ipinfodb.com/v3/ip-city/'
        return self._fetch_from_API(ip_addr, baseurl)


class IpinfodbStorage(object):

    def __init__(self, plugin):
        self.plugin = plugin
        self._table = 'ipinfo'

    def getCountry(self, cid):
        q = 'SELECT * from %s WHERE id = %s LIMIT 1' % (self._table, cid)
        cursor = self.plugin.console.storage.query(q)
        if cursor and not cursor.EOF:
            r = cursor.getRow()
            return r

    def create(self, client):
        data = {
            'id': client.id,
            'countryCode': client.countryCode,
            'countryName': client.countryName,
        }
        q = self._insertquery()
        try:
            cursor = self.plugin.console.storage.query(q, data)
            if cursor.rowcount > 0:
                self.plugin.debug("rowcount: %s, id:%s" % (cursor.rowcount, cursor.lastrowid))
            else:
                self.plugin.warning("inserting into %s failed" % self._table)
        except Exception, e:
            if e[0] == 1146:
                self.plugin.error("Could not save to database : %s" % e[1])
                self.plugin.info("Refer to this plugin readme file for instruction on how to create the required tables")
            else:
                raise e

    def _insertquery(self):
        return """INSERT INTO {table_name}
             (id, countryCode, countryName)
             VALUES (%(id)s, %(countryCode)s, %(countryName)s) """.format(table_name=self._table)

    def update(self):
        pass


if __name__ == '__main__':
    # create a fake console which emulates B3
    from b3.fake import fakeConsole, joe, superadmin, simon

    myplugin = IpinfodbPlugin(fakeConsole, 'conf/plugin_ipinfodb.ini')
    myplugin.onStartup()

    # make superadmin connect to the fake game server on slot 0
    superadmin.connects(cid=0)

    # add ip for our fake user
    simon.ip = '8.8.8.8' # google DNS ;)
    joe.ip = '8.8.8.8' # google DNS ;)
    joe.connects(cid=1)

    #simon.connects(cid=2)

    #print myplugin.getCountry()
