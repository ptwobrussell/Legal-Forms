# Overview

This GAE sample project provides sample code that demonstrates how to create a minimal web app
that authenticates users via their Twitter accounts and prompts them to purchase sample "legal 
templates" using PayPal's Digital Goods (Express Checkout) product.

Mike Knapp's https://github.com/mikeknapp/AppEngine-OAuth-Library project is used to 
handle making OAuth requests to Twitter to avoid the need to setup and manage user accounts.

Pat Coll's https://github.com/patcoll/paypal-python project was used as a starting point for
implementing a Digital Goods (via Express Checkout) flow using PayPal. (The code as checked in
isn't so much a general purpose library as it is just a convenient means of performing Express
Checkout via NVP with Python.)

See https://cms.paypal.com/cms_content/US/en_US/files/developer/PP_ExpressCheckout_IntegrationGuide_DG.pdf
for more details on PayPal's Digital Goods offering

# Getting Started

Follow these steps to get up and running:

* Download this project's source code
* Configure the source code as a Google App Engine project
* Create a buyer/seller account in PayPal's developer sandbox
* Create a Twitter account 
* Create a sample Twitter application
* Copy config.template.py to config.py and fill in the PayPal API and Twitter API variables
* Launch the project!

# Screenshot

![screenshot!](https://github.com/ptwobrussell/Legal-Forms/raw/master/screenshot.png)

Provided by: Zaffra, LLC - http://zaffra.com
