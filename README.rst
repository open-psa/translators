###############################
Translators to the Open-PSA MEF
###############################

.. image:: https://travis-ci.org/open-psa/translators.svg?branch=master
    :target: https://travis-ci.org/open-psa/translators
.. image:: https://codecov.io/gh/open-psa/translators/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/open-psa/translators
.. image:: https://landscape.io/github/open-psa/translators/master/landscape.svg?style=flat
    :target: https://landscape.io/github/open-psa/translators/master
    :alt: Code Health

|

The repository contains free translators provided by the community.

To get schemas for validation, clone this repository with:

.. code-block:: bash

    git clone --recursive

If not cloned recursive, initialize and/or update the schemas submodule with:

.. code-block:: bash

    git submodule update --init --recursive

To install Python modules for testing:

.. code-block:: bash

    sudo pip --install -r requirements-test.txt

Testing against schemas requires ``libxml2`` and ``libxslt``.

The development requirements are optional.

.. code-block:: bash

    sudo pip --install -r requirements-dev.txt
