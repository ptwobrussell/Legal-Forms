# coding=utf-8
"""
The end developer will do most of their work with the PayPalInterface class found
in this module. Configuration, querying, and manipulation can all be done
with it.
"""
import logging
import types
import socket
import urllib
import urllib2
from urlparse import urlsplit, urlunsplit

from settings import PayPalConfig
from response import PayPalResponse
from exceptions import PayPalError, PayPalAPIResponseError
   
class PayPalInterface(object):
    """
    The end developers will do 95% of their work through this class. API
    queries, configuration, etc, all go through here. See the __init__ method
    for config related details.
    """
    def __init__(self , config=None, **kwargs):
        """
        Constructor, which passes all config directives to the config class
        via kwargs. For example:
        
            paypal = PayPalInterface(API_USERNAME='somevalue')
            
        Optionally, you may pass a 'config' kwarg to provide your own
        PayPalConfig object.
        """
        if config:
            # User provided their own PayPalConfig object.
            self.config = config
        else:
            # Take the kwargs and stuff them in a new PayPalConfig object.
            self.config = PayPalConfig(**kwargs)
        
    def _encode_utf8(self, **kwargs):
        """
        UTF8 encodes all of the NVP values.
        """
        unencoded_pairs = kwargs
        for i in unencoded_pairs.keys():
            if isinstance(unencoded_pairs[i], types.UnicodeType):
                unencoded_pairs[i] = unencoded_pairs[i].encode('utf-8')
        return unencoded_pairs
    
    def _call(self, method, **kwargs):
        """
        Wrapper method for executing all API commands over HTTP. This method is
        further used to implement wrapper methods listed here:
    
        https://www.x.com/docs/DOC-1374
    
        ``method`` must be a supported NVP method listed at the above address.
    
        ``kwargs`` will be a hash of
        """
        #socket.setdefaulttimeout(self.config.HTTP_TIMEOUT)
    
        url_values = {
            'METHOD': method,
            'VERSION': self.config.API_VERSION
        }
    
        headers = {}
        if(self.config.API_AUTHENTICATION_MODE == "3TOKEN"):
            url_values['USER'] = self.config.API_USERNAME
            url_values['PWD'] = self.config.API_PASSWORD
            url_values['SIGNATURE'] = self.config.API_SIGNATURE
        elif(self.config.API_AUTHENTICATION_MODE == "UNIPAY"):
            url_values['SUBJECT'] = self.config.SUBJECT

        for k,v in kwargs.iteritems():
            url_values[k.upper()] = v
        
        # When in DEBUG level 2 or greater, print out the NVP pairs.
        if self.config.DEBUG_LEVEL >= 2:
            k = url_values.keys()
            k.sort()
            for i in k:
               logging.info(" %-20s : %s" % (i , url_values[i]))

        u2 = self._encode_utf8(**url_values)

        data = urllib.urlencode(u2)
        req = urllib2.Request(self.config.API_ENDPOINT, data, headers)
        response = PayPalResponse(urllib2.urlopen(req).read(), self.config)

        if self.config.DEBUG_LEVEL >= 1:
            logging.info(" %-20s : %s" % ("ENDPOINT", self.config.API_ENDPOINT))
    
        if not response.success:
            if self.config.DEBUG_LEVEL >= 1:
                logging.info(response)
            raise PayPalAPIResponseError(response)

        return response

    def get_express_checkout_details(self, token):
        return self._call('GetExpressCheckoutDetails', token=token)
        
    def set_express_checkout(self, token='', **kwargs):
        kwargs.update(locals())
        del kwargs['self']
        return self._call('SetExpressCheckout', **kwargs)

    def do_express_checkout_payment(self, token, **kwargs):
        kwargs.update(locals())
        del kwargs['self']
        return self._call('DoExpressCheckoutPayment', **kwargs)
    
    # XXX: Hardcoded for sandbox usage and opt-out of reviewing the express checkout details
    def generate_express_checkout_digital_goods_redirect_url(self, token):
        return "https://www.sandbox.paypal.com/incontext?token=%s&useraction=commit" % (token,)

    def generate_express_checkout_redirect_url(self, token):
        """Submit token, get redirect url for client."""
        url_vars = (self.config.PAYPAL_URL_BASE, token)
        return "%s?cmd=_express-checkout&token=%s" % url_vars
