:orphan:

.. _quick_install:

************
Installation
************

Dependancies
############

External software dependancies
------------------------------

SkullTo3d relies heavily on other neuroimaging Softwares, predominentyly:

* `FSL <http://www.fmrib.ox.ac.uk/fsl/index.html>`_
* `ANTS <http://stnava.github.io/ANTs/>`_
* `AFNI <https://afni.nimh.nih.gov/>`_
* `SPM <https://www.fil.ion.ucl.ac.uk/spm/>`_

Python packages dependancies
----------------------------

SkullTo3d relies on python packages. Here we provide installations using Anaconda

Creating environment with all packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In case you have access to a conda environment, here is the procedure to initialize your own environnment (called "skullTo3d_env", but can be called the name you prefer):

.. code-block:: bash

    $ conda init bash
    $ conda create -n skullTo3d_env python=3.10
    $ conda activate skullTo3d_env

Install skullTo3d package
########################

from github
-----------

.. _git_install:

Using git
~~~~~~~~~

.. code:: bash

    $ git clone https://github.com/Macatools/skullTo3d.git
    $ cd skullTo3d
    $ python setup.py develop --user

Using pip
~~~~~~~~~

.. code:: bash

    $ pip install git+https://github.com/Macatools/skullTo3d

.. _pip_install:

from pypi
---------

SkullTo3d is available on * `pypi.org <https://pypi.org/project/skullTo3d/>`_:

If 'pip' package is installed on your system, you can install the lastest stable version with:

.. code:: bash

    $ pip install skullTo3d

Testing the install
###################


.. code:: bash

    $ ipython

.. code:: ipython

    In [1]: import skullTo3d; print (skullTo3d.__version__)

See :ref:`Quick test <quick_test>` for testing if your installation works properly on test datasets.
