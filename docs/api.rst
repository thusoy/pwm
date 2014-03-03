API documentation
=================

All classes and methods exposed by the core pwm API is documented here.

This is a short dictionary of the terms used in the source code and the documentation:

alphabet
    An alias for a charset, or a full set of characters to use. Translation to charset can be with
    the :func:`lookup_alphabet <pwm.encoding.lookup_alphabet>` function from the encoding module.

charset
    A set of characters the computed key will consist of.

domain
    A set of values for a site or application pwm manages for you. In the minimal case it has a
    name and a salt for the site, potentially also a username and other notes you hav added for
    this site.

domain names
    An identifier for a given site or applicaiton. Can be whatever you desire, like 'fb' or
    'facebook.com', but the latter might be preferable is you want to integrate your database with
    other pwm-compatible tools like browser plugins or similar, which can automatically lookup keys
    based on the current domain.

keys
    Something you use to get access to other sites. Gets computed from your master password, a
    domain name, and a salt.

password
    A password is something you remember to prove that you are you. In pwm there is only one
    password, and that is your master password. What you use to access other sites are *keys*,
    which generally is not something you'll easily remember.


salt
    A random base64-encoded string. If one of your keys is exposed in some way, all you need to do
    is generate a new salt for the domain and switch keys.


.. automodule:: pwm.core
   :members:

.. automodule:: pwm.encoding
   :members:
