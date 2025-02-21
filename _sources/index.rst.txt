.. _skullTo3d:

*********
SkullTo3D
*********
..
.. .. _short_logo:
.. .. |logo1| image:: ./img/logo/logo_skullTo3d_0.1.jpg
..     :scale: 100%
..
.. .. table::
..    :align: center
..
..    +---------+
..    | |logo1| |
..    +---------+
..


**skullTo3d** is an upper layer of `Macapype <https://macatools.github.io/macapype>`_ project, adding to MRI anatomocal brain segmentation **skull** segmentation, either originating from CT scan , MRI petra or T1w sequence, as well as angio images segmentation

.. image:: ./img/logo/logo_skullTo3d_0.1.jpg
    :width: 600
    :align: center


Installation
************

See :ref:`Quick Installation <quick_install>` for installation on your local system if you have adequate softwares (i.e. FSL, AFNI, Ants, SPM) running on your machine/clusters

See :ref:`Container installation <docker_install>` for fully compliant installation (no MRI softwares, or Windows / MacOS operating system)

Once installed, see :ref:`Quick test <quick_test>` for testing if your installation is working properly


Command line parameters
***********************

SkullTo3D is fairly flexible, but requires to specify multiples parameters in command line

See :ref:`Commands <command>` for a description on the avalaible command parameters



Table of contents
******************

.. toctree::
    :maxdepth: 2

    quick_install
    docker_install
    quick_test
    command
    params
    indiv_params



