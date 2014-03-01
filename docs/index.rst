.. pwm documentation master file, created by
   sphinx-quickstart on Sat Mar 01 19:33:18 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pwm's documentation!
===============================

pwm is a lightweight password manager that doesn't store passwords.

The idea is to store just a salt (random token) for each site you use, and then compute an access
key when you need it instead of storing passwords. This way, the salt database is practically
worthless without the master password. Everything rests upon the strength of your master password
though, so don't go easy on that one.

We want to expose a very simple core API that can easily be implemented on several platforms as the
need grows. We also have plans for a web interface you can use when all devices are dead, stay
tuned!

If you're a developer, you might want to skim through the API docs.

Contents:

.. toctree::
   :maxdepth: 2

   api



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

