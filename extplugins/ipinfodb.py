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
from b3.querybuilder import QueryBuilder
from b3.storage import Storage
from b3.storage.database import DatabaseStorage
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

        # register event "Client Auth"
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)


    def onEvent(self, event):
        if event.type == b3.events.EVT_CLIENT_AUTH:
            self.do_client_location_update(event.client)

    #def _setClientLocation(self, client, countryCode, countryName):
    #    self.debug('Set countryName %s' % countryName.title())
    #    setattr(client, 'countryCode', countryCode)
    #    setattr(client, 'countryName', countryName.title())

    def callback_client_update(self, client, data):
        """callback that set country code to client"""
        if data['statusCode'] == 'OK':
            client.country = str(data['countryCode'])
            client.save()

    def do_client_location_update(self, client):
        if len(client.country) >= 2:
            self.debug('Found country code: %s in DB' % client.country)
            #self._setClientLocation(client, _result['countryCode'], _result['countryName'])
        else:
            self.debug('No country code for %s. Try to update from IPInfodb.com' % client.name)
            if client.ip:
                Ipinfodb_query(self.ipinfodb_api, ip=client.ip, callback=self.callback_client_update,
                               callback_args=(client,)).start()
            else:
                self.error('No IP for %s found' % client.name)

# thread for ipinfodb querys
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

# tiny dirty api
class IPinfo(object):
    # todo: requests are cool stuff - du we need it realy?
    def __init__(self, api_key):
        self._api_key = api_key
        self._requests_session = requests.session()

    def _fetch_from_API(self, ip_addr=None, baseurl='http://api.ipinfodb.com/v3/ip-country/'):
        payload = {'timezone': False, 'format': 'json', 'key': self._api_key, 'ip': ip_addr}
        r = self._requests_session.get(baseurl, params=payload, timeout=30)
        if r.status_code == requests.codes.ok:
            return r.json()

    def getCountry(self, ip_addr=None):
        baseurl = 'http://api.ipinfodb.com/v3/ip-country/'
        return self._fetch_from_API(ip_addr, baseurl)

    def getCity(self, ip_addr=None):
        baseurl = 'http://api.ipinfodb.com/v3/ip-city/'
        return self._fetch_from_API(ip_addr, baseurl)

###########################################
# monkey and patches? lets break the world
###########################################

# add country prperty to client
class IpiClient(b3.clients.Client):
    console = None
    country = ''

    def __init__(self, console, **kwargs):
        self.console = console
        #self.country = country
        #self._country = ''
        self.message_history = [] # this allows unittests to check if a message was sent to the client
        b3.clients.Client.__init__(self, **kwargs)

    b3.clients.Client._country = ''
    def _set_country(self, v):
        self._country = v

    def _get_country(self):
        return self._country

    b3.clients.Client.country = property(_get_country, _set_country)


# add country field to DB
class IpinfodbDatabaseStorage(b3.storage.database.DatabaseStorage):
    console = None

    def __init__(self, console, **kwargs):
        self.console = console
        b3.storage.database.DatabaseStorage.__init__(self, **kwargs)

    def _setClient(self, client):
        """
        id int(11)   PRI NULL auto_increment 
        ip varchar(16) YES   NULL   
        greeting varchar(128) YES   NULL   
        connections int(11) YES   NULL   
        time_edit int(11) YES   NULL   
        guid varchar(32)   MUL     
        pbid varchar(32) YES   NULL   
        name varchar(32) YES   NULL   
        time_add int(11) YES   NULL   
        auto_login int(11) YES   NULL   
        mask_level int(11) YES   NULL   
        group_bits int(11)
        country varchar(3) YES NULL
        """

        self.console.debug('Storage: Ipinfodb plugin patched setClient %s' % client)

        fields = (
            'ip',
            'greeting',
            'connections',
            'time_edit',
            'guid',
            'pbid',
            'name',
            'time_add',
            'auto_login',
            'mask_level',
            'group_bits',
            'login',
            'password',
            'country'
        )
    
        if client.id > 0:
            data = { 'id' : client.id }
        else:
            data = {}

        for f in fields:
            if hasattr(client, self.getVar(f)):
                data[f] = getattr(client, self.getVar(f))


        self.console.debug('Storage: Ipinfodb plugin patched  setClient data %s' % data)
        if client.id > 0:
            self.query(QueryBuilder(self.db).UpdateQuery(data, 'clients', { 'id' : client.id }))
        else:
            cursor = self.query(QueryBuilder(self.db).InsertQuery(data, 'clients'))
            if cursor:
                client.id = cursor.lastrowid
            else:
                client.id = None

        return client.id

    b3.storage.database.DatabaseStorage.setClient = _setClient



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

    simon.connects(cid=2)

    #print myplugin.getCountry()
