#!/usr/bin/env python

##################################################################################################
# This GAE sample project provides sample code that demonstrates how to create a minimal web app
# that authenticates users via their Twitter accounts and prompts them to purchase sample "legal 
# templates" using PayPal's Digital Goods (Express Checkout) product.
#
# Mike Knapp's https://github.com/mikeknapp/AppEngine-OAuth-Library project is used to 
# handle making OAuth requests to Twitter to avoid the need to setup and manage user accounts.
#
# Pat Coll's https://github.com/patcoll/paypal-python project was used as a starting point for
# implementing a Digital Goods (via Express Checkout) flow using PayPal. (The code as checked in
# isn't so much a general purpose library as it is just a convenient means of performing Express
# Checkout via NVP with Python.)
#
# See https://cms.paypal.com/cms_content/US/en_US/files/developer/PP_ExpressCheckout_IntegrationGuide_DG.pdf
# for more details on PayPal's Digital Goods offering
##################################################################################################

import os

# Use newer version of Django than 0.96 (and also
# declare a specific version for when the default changes)

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
from google.appengine.dist import use_library
use_library('django', '1.2')
from django.template.loader import render_to_string

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from django.utils import simplejson as json

import oauth
import random
import logging

from paypal.interface import PayPalInterface

# Copy config.template.py to config.py and fill in these values in that file

from config import CONSUMER_KEY,\
                   CONSUMER_SECRET,\
                   PP_API_USERNAME,\
                   PP_API_PASSWORD,\
                   PP_API_SIGNATURE

# A simple (twitter_username, [id1, id2, ... ]) scheme to track purchases

class User(db.Model):
  twitter_username = db.StringProperty(required=True)
  purchases = db.StringListProperty(required=True)

# A simple abstraction for representing a product catalog

class Catalog(object):
  @staticmethod
  def getProducts():

    # This sample app only features a single product: a sample invoice template. Additional products could be added by 
    # extending this method to read the data from a flat file or data store.

    return {
            'invoice_template1' : {'price' : '3.00', 'description' : 'Super Simple Invoice Template'},
            'letter_of_resignation1' : {'price' : '2.50', 'description' : 'Unapologetic Letter of Resignation'}
           }

# Logic for interacting wtih PayPal's Digital Goods (via ExpressCheckout) product

class PaymentHandler(webapp.RequestHandler):

  def _getPayPal(self):

    return PayPalInterface(API_USERNAME=PP_API_USERNAME, API_PASSWORD=PP_API_PASSWORD, API_SIGNATURE=PP_API_SIGNATURE)

  def post(self, mode=""):

    # Setting up Express Checkout happens just before the lightbox or mini-browser is displayed

    if mode == "set_ec":

      sid = self.request.get("sid")
      user_info = memcache.get(sid)

      item_id = self.request.get("item_id")
      product = Catalog().getProducts()[item_id]

      pp = self._getPayPal()
      response = pp.set_express_checkout(
                 paymentrequest_0_currencycode="USD",
                 paymentrequest_0_amt=product['price'], 
                 paymentrequest_0_itemamt=product['price'], 

                 returnurl=self.request.host_url+"/do_ec_payment?sid=%s&item_id=%s" % (sid, item_id,),
                 cancelurl=self.request.host_url+"/cancel_ec?sid="+sid, 

                 l_paymentrequest_0_name0=product['description'],
                 l_paymentrequest_0_amt0=product['price'],
                 l_paymentrequest_0_qty0="1",
                 l_paymentrequest_0_itemcategory0="Digital",

                 reqconfirmshipping=0,
                 noshipping=1,
                 
                 paymentrequest_0_paymentaction='Sale')

      if not response.success:
        logging.error("Failure for SetExpressCheckout")

        return render_to_string("unknown_error.html", {
          'title' : 'Error',
          'operation' : 'SetExpressCheckout'
        })

      # Redirect to PayPal and allow user to confirm payment details.
      # Then PayPal redirects back to the /get_ec_details or /cancel_ec endpoints.
      # Assuming /get_ec_details, we complete the transaction with pp.get_express_checkout_details
      # and pp.do_express_checkout_payment

      redirect_url = pp.generate_express_checkout_digital_goods_redirect_url(response.TOKEN)
      logging.info("redirect_url=" + redirect_url)
      return self.redirect(redirect_url)

    else:
      logging.error("Unknown mode for POST request!")

  def get(self, mode=""):


    # This sample code is "fast tracked" to avoid reviewing the checkout details, so there's no call to
    # GetExpressCheckoutDetails. The user goes directly from the lightbox (or mini-browser) back to  
    # the website where the payment is completed (or cancelled.)
     
    if mode == "do_ec_payment":

      if memcache.get(self.request.get('sid')) is not None: # Without an account reference, we can't credit the purchase
        pp = self._getPayPal()
        payerid = self.request.get('PayerID')

        item_id = self.request.get('item_id')
        product = Catalog().getProducts()[item_id]

        # Note that you must send all of the same params back in for DoExpressCheckoutPayment even though
        # they've already been passed to SetExpressCheckout to get the digital goods rate.

        response = pp.do_express_checkout_payment(self.request.get('token'),
                payerid=payerid, 

                l_paymentrequest_0_name0=product['description'],
                l_paymentrequest_0_amt0=product['price'],
                l_paymentrequest_0_qty0="1",
                l_paymentrequest_0_itemcategory0="Digital",

                paymentrequest_0_amt=product['price'], 
                paymentrequest_0_itemamt=product['price'], 

                paymentrequest_0_currencycode='USD',
                paymentrequest_0_paymentaction='Sale')

        if not response.success:
          logging.error("Failure for DoExpressCheckoutPayment")

          self.response.out.write(render_to_string('unknown_error.html', {
            'title' : 'Error',
            'operation' : 'DoExpressCheckoutPayment'
          }))


        # Add the purchase to the user's account

        sid = self.request.get("sid")
        user_info = memcache.get(sid)
        twitter_username = user_info['username']
        query = User.all().filter("twitter_username =", twitter_username)
        user = query.get()
        user.purchases += [item_id]
        db.put(user)

        # The successful payment template takes care of updating the page to 
        # allow the user to retrieve the digital goods purchase

        self.response.out.write(render_to_string('successful_payment.html', {
          'title' : 'Successful Payment',
          'description' : product['description'],
          'item_id' : item_id,
          'sid' : sid
        }))

      else:
        logging.error("Invalid/expired session in /do_ec_payment")

        self.response.out.write(render_to_string('session_expired.html', {
          'title' : 'Session Expired',
        }))

    elif mode == "cancel_ec":
      self.response.out.write(render_to_string('cancel_purchase.html', {
        'title' : 'Cancel Purchase',
      }))

# Logic for interacting with Twitter's API and handling the minimal
# application logic involved.

class AppHandler(webapp.RequestHandler):

  # The get method takes care of all api endpoints in this app except for /set_ec

  def get(self, mode=""):
    
    client = oauth.TwitterClient(CONSUMER_KEY, CONSUMER_SECRET, "%s/app" % self.request.host_url)
   
    # The /app context displays the main catalog page

    if mode == "app":

      # Pull out auth token/verifier in order to get an access token
      # and in order to get some basic information about the user.

      auth_token = self.request.get("oauth_token")
      auth_verifier = self.request.get("oauth_verifier")
      user_info = client.get_user_info(auth_token, auth_verifier=auth_verifier)

      twitter_username = user_info['username']

      # Has a user already used this webapp with twitter_username?

      query = User.all().filter("twitter_username =", twitter_username)
      user = query.get()

      # If not, create a user

      if user is None:
        user = User(twitter_username=twitter_username, )
        user.put()

      # Avoid a full-blown Session implementation for purposes of simplicity in this demo code. (See 
      # http://stackoverflow.com/questions/2560022/simple-app-engine-sessions-implementation
      # for some very pragmatic tips on how you might approach that in a very lightweight fashion.)
      # Sessions will be needed in both the if and the else clause below, so go ahead and compute it

      sid = str(random.random())[5:] + str(random.random())[5:] + str(random.random())[5:]

      memcache.set(sid, user_info, time=60*10) # seconds

      user = User.all().filter("twitter_username =", twitter_username).get()

      self.response.out.write(render_to_string('digital_goods.html', { 
        'title' : 'Legal Templates: Catalog',
        'sid' : sid,
        'catalog' : Catalog().getProducts(),
        'purchases' : user.purchases 
      })) 

    elif mode == "login":

      return self.redirect(client.get_authorization_url())

    # /purchases is used to allow the user to access their digital goods purchases. When users login (or
    # immediately after they complete a purchase), they'll be able to click on a "already purchased" link
    # that takes them to the template that they purchased.

    elif mode == "purchases":

      sid = self.request.get('sid')
      if memcache.get(sid) is not None: # Without an account reference, we can't credit the purchase

        item_id = self.request.get('item_id')

        # Verify that the user purchased the item by checking the account information

        user_info = memcache.get(sid)
        twitter_username = user_info['username']
        query = User.all().filter("twitter_username =", twitter_username)
        user = query.get()
        if item_id in user.purchases:
          self.response.out.write(render_to_string('legal_templates/%s.html' % (item_id,), {
            'title' : Catalog().getProducts()[item_id]['description']
          }))
        else:
          logging.error("User %s has not purchased %s" % (twitter_username, item_id,))

          self.response.out.write(render_to_string('unknown_error.html', {
            'title' : 'Invalid Access',
            'operation' : 'document access'
          }))


      else:
        logging.error("Invalid/expired session in /purchases")

        self.response.out.write(render_to_string('session_expired.html', {
          'title' : 'Session Expired',
        }))


    else: # root URL context which is used for setting up the login flow

      self.response.out.write(render_to_string('root.html', {
        'title' : 'Legal Templates',
      }))

def main():

  application = webapp.WSGIApplication([('/(set_ec)', PaymentHandler),
                                        ('/(do_ec_payment)', PaymentHandler),                                      
                                        ('/(cancel_ec)', PaymentHandler),                                      

                                        ('/(purchases)', AppHandler),
                                        ('/(app)', AppHandler),
                                        ('/(login)', AppHandler),
                                        ('/', AppHandler)],
                                       debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
