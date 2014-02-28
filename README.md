pwm [![Build Status](https://travis-ci.org/thusoy/pwm.png?branch=master)](https://travis-ci.org/thusoy/pwm)
===

*A minimal, secure password manager that can't tell on you.*

Most password managers use a master password to keep your site-specific passwords safe. This means that you're password database becomes a very precious target; after all, if you lose it, your entire online presence is compromised. But we still don't want to be back in the hell we were when we tried to remember unique passwords for all different sites we used, that's no good solution either - we're humans after all.

So what does pwm do differently? Instead of storing your passwords, it stores some random bytes (often known as a salt) for each of your sites, and when you want to get the access key for a site you simply enter your master password and an identifier for the site (such as the domain, mybank.com or similar), and pwm will generate a key for you to use as a password on that site, without storing it anywhere. Thus, if your database is lost, all that's present in the database is a random string that's without value without your master password.

Indeed, not even your master password is stored anywhere. Give the wrong password and you'll simply get a different key and probably a nice error message from the site where you're trying to authenticate. 

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


Roadmap
-------

The project is very young still, but this is roughly the roadmap we think we'll follow. If you have any ideas or feature requests, shout out!

* Make it possible to store additional info for a domain (username, notes, etc)
* Make charsets/lengths customizable on a domain-basis, to cope for domains that doesn't allow long passwords or that require passwords to adhere to a given format (needs special characters or similar)
* Make it portable enough
* Make a complementary web interface for the time when you're without your devices and need your passwords


Development
-----------

Set up a new virtualenv:

    $ virtualenv venv
    $ . venv/bin/activate
    $ pip install -e .[test]

Do your stuff, test your code by running nosy, which automatically reruns tests on changes:

    $ nosy

Keep [test coverage](http://thusoy.github.io/pwm/) up.

Philosophy
----------

The idea behind pwm is simple; an easy-to-use, secure password manager you'll always have access to. The client is very simple, and can easily be implemented on multiple platforms. The user should always stay in control of the data, there's no dependencies on externally hosted services and no signup or tracking of your usage.
