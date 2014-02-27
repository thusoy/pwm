pwm [![Build Status](https://travis-ci.org/thusoy/pwm.png?branch=master)](https://travis-ci.org/thusoy/pwm)
===

A minimal, secure password manager that can't tell on you.

Most password managers use a master password to keep your site-specific passwords safe. This means that you're password database becomes a very sought after target; after all, if you lose it, your entire online presence is compromised. But we still don't want to be back in the hell we were when we tried to remember unique passwords for all different sites we used, that's no good solution either, we're humans after all.

So what does pwm do differently? Instead of storing your passwords, it stores some random bytes (often known as a salt) for each of your sites, and when you want to get the access key for a site you simply enter your master password and an identifier for the site (such as the domain, mybank.com or similar), and pwm will generate a key for you to use as a password on that site, without storing it anywhere. Thus, if your database is lost, all that's present in the database is a random string that's without value without your master password.

Usage
-----

    $ pwm search .com
    mybank.com
    ebay.com
    facebook.com

    $ pwm get mybank.com
    Enter your master password: 'supersecret'
    61def4de798453e39d5af289f742eb15827973e7


Installation
------------

From pip:

    $ pip install pwm

From source:

    $ python setup.py install


Development
-----------

Set up a new virtualenv:

    $ virtualenv venv
    $ . venv/bin/activate
    $ pip install -e .[test]

Do your stuff, test your code by running nosy, which automatically reruns tests on changes:

    $ nosy
