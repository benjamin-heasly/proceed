Installation
============

Proceed requires `Python <https://www.python.org/>`_ and `Docker <https://www.docker.com/>`_ to be installed.
With those, it should be able to run a wide variety pipelines and steps via containers.

pip
---

Proceed itself is not yet available on `PyPI <https://pypi.org/>`_.
When it is, this will be the recommended way to install Proceed:

.. code-block:: console

  $ pip install proceed # TODO

git and pip
-----------

You can also install Proceed from source.

.. code-block:: console

  $ git checkout https://github.com/benjamin-heasly/proceed.git
  $ pip install ./proceed


check installation
------------------

You can check if Proceed installed correctly using the `proceed` command.

.. code-block:: console

  $ proceed --version
  Proceed x.y.z

  $ proceed --help
  usage etc...
