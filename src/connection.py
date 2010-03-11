#!/usr/bin/python
#
# A proxy interface to initiate and interact communication with Unified Entitlement Platform server such as candlepin.
#
# Copyright (c) 2010 Red Hat, Inc.
#
# Authors: Pradeep Kilambi <pkilambi@redhat.com>
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.
#

import sys
import httplib
import simplejson as json
import base64

class RestlibException(Exception):
    pass

class Restlib(object):
    """
     A wrapper around httplib to make rest calls easier
    """
    def __init__(self, host, port, apihandler):
        self.host = host
        self.port = port
        self.apihandler = apihandler
        self.headers = {"Content-type":"application/json",
                        "Accept": "application/json"}

    def _request(self, request_type, method, info=None):
        handler = self.apihandler + method
        conn = httplib.HTTPConnection(self.host, self.port)
        conn.request(request_type, handler, body=json.dumps(info), \
                     headers=self.headers)
        response = conn.getresponse()
        self.validateResponse(response)
        rinfo = response.read()
        if not len(rinfo):
            return None
        return json.loads(rinfo)

    def validateResponse(self, response):
        if str(response.status) not in ["200", "204"]:
            raise RestlibException(response.reason)

    def request_get(self, method):
        return self._request("GET", method)

    def request_post(self, method, params=""):
        return self._request("POST", method, params)

    def request_head(self, method):
        return self._request("HEAD", method)

    def request_put(self, method, params=""):
        return self._request("PUT", method, params)

    def request_delete(self, method):
        return self._request("DELETE", method)

class UEPConnection:
    """
    Proxy for Unified Entitlement Platform.
    """

    def __init__(self, host='localhost', port=8080, handler="/candlepin"):
        self.host = host
        self.port = port
        self.handler = handler
        self.conn = None
        # initialize connection
        self.setUp()

    def setUp(self):
        self.conn = Restlib(self.host, self.port, self.handler)

    def shutDown(self):
        self.conn.close()

    def __authenticate(self, username, password):
        encoded = base64.encodestring(':'.join((username,password)))
        basic = 'Basic %s' % encoded[:-1]
        self.conn.headers['Authorization'] = basic
        return self.conn.headers

    def ping(self):
        return self.conn.request_get("/status/")

    def registered(self):
        needToRegister=0
        if not os.access("/etc/pki/consumer/cert.pem", os.F_OK):
            needToRegister = 1
        return needToRegister

    def registerConsumer(self, username, password, info={}):
        self.__authenticate(username, password)
        return self.conn.request_post('/consumers/', info)

    def unregisterConsumer(self, username, password, consumerId):
        self.__authenticate(username, password)
        method = '/consumers/%s' % consumerId
        return self.conn.request_delete(method)

    def syncCertificates(self, consumerId):
        """
        Sync all applicable certificates for a given consumer\
        @param consumerId: consumer uuid
        @return: A list of entitlement certificates
        """
        method = '/consumers/%s/certificates' % consumerId
        return self.conn.request_get(method)

    def SyncCertificatesBySerial(self, consumerId, serialNumbers):
        """
        Sync certificates for a given set of serial numbers
        @param consumerId: consumer uuid
        @param serialNumbers: list of serial numbers eg: ['SERIAL002', 'SERIAL001']
        @return: A list of entitlement certificates
        """
        serialNumbers = ','.join(serialNumbers)
        method = '/consumers/%s/certificates?serials=%s' % (consumerId, serialNumbers)
        return self.conn.request_get(method)

    def getCertificateSerials(self, consumerId):
        """
        Get serial numbers for certs for a given consumer
        @param consumerId: consumer uuid
        @return: A set of serial numbers
        """
        method = '/consumers/%s/certificates/serials' % consumerId
        return self.conn.request_get(method)

    def bindByRegNumber(self, consumerId, regnum=None):
        method = "/consumers/%s/entitlements?token=%s" % (consumerId, regnum)
        return self.conn.request_post(method)

    def bindByEntitlementPool(self, consumerId, poolId=None):
        method = "/consumers/%s/entitlements?pool=%s" % (consumerId, poolId)
        return self.conn.request_post(method)

    def bindByProduct(self, consumerId, product=None):
        method = "/consumers/%s/entitlements?product=%s" % (consumerId, product)
        return self.conn.request_post(method)

    def unBindBySerialNumbers(self, consumerId, serialNumbers):
        method = "/entitlement/consumer/%s/%s" % (consumerId, ','.join(serialNumbers))
        return self.conn.request_post(method)

    def unbindAll(self, consumerId):
        method = "/entitlement/consumer/%s" % consumerId
        return self.conn.request_post(method)

    def getPoolsList(self, consumerId):
        method = "/pools?consumer=%s" % consumerId
        return self.conn.request_get(method)

    def getEntitlementList(self, consumerId):
        method = "/consumers/%s/entitlements" % consumerId
        return self.conn.request_get(method)

    def getEntitlementById(self, consumerId, entId):
        method = "/consumers/%s/entitlements/%s" % (consumerId, entId)
        return self.conn.request_get(method)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        uep = UEPConnection(sys.argv[1])
    else:
        uep = UEPConnection()
    # create a consumer
    print "Ping Server", uep.ping()
    stype = {'label':'system'}
    product = {"id":"1","label":"RHEL AP","name":"rhel"}
    facts = {"metadata": {
                "entry":[{"key":"arch","value":"i386"},
                         {"key":"cpu", "value": "Intel" },
                         {"key":"cores", "value":4}]
                }
            }
    params = {
        "type":stype,
        "name":'admin',
        "facts":facts,
    }
    try:
        consumer = uep.registerConsumer('admin', 'password', info=params)
        print "Created a consumer ", consumer
        # sync certs
        #print "Initiate cert synchronization for uuid"
        print uep.syncCertificates(consumer['uuid']) 
        print uep.getCertificateSerials(consumer['uuid'])
        print uep.SyncCertificatesBySerial(consumer['uuid'], ['SERIAL001','SERIAL001'])
        # bind consumer to regNumber
        #uep.bindByRegNumber(consumer['uuid'],"1234-5334-4e23-2432-4345") 
        # bind consumer by poolId
        #uep.bindByEntitlementPool(consumer['uuid'], "1001")
        # bind consumer By Product
        print uep.bindByProduct(consumer['uuid'], "monitoring") #product["label"])
        # Unbind All
        #print uep.unbindAll(consumer['uuid'])
        # Unbind serialNumbers
        #uep.unBindBySerialNumbers(consumer['uuid'], ['SERIAL001','SERIAL001'])
        print uep.getPoolsList(consumer['uuid'])
        # lookup Entitlement Info by PoolId
        #print uep.getEntitlementById("4")
        print "print get Ent list", uep.getEntitlementList(consumer['uuid'])
        print uep.getEntitlementById(consumer['uuid'], "3")
        # delete a consumer
        print uep.unregisterConsumer('admin', 'password', consumer['uuid'])
        print "consumer unregistered"
    except RestlibException, e:
        print"Error:", e
        sys.exit(-1)
