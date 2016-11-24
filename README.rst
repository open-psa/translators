###############################
Translators to the Open-PSA MEF
###############################

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

The developement requirements are optional.

.. code-block:: bash

    sudo pip --install -r requirements-dev.txt
