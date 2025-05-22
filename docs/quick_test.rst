:orphan:

.. _quick_test:

**********
Quick test
**********

Download datasets
#################

.. code:: bash

    $ cd /path/to/data

    $ curl https://amubox.univ-amu.fr/public.php/dav/files/7tf4ooJsyjHfSbG --output skullTo3d_CI_v2.zip

    $ unzip -o skullTo3d_CI_v2.zip -d skullTo3d_CI_v2

Testing depending on the installation
#####################################

Testing from Singularity image
------------------------------

.. code:: bash

    $ singularity run -B /path/to/data:/data /path/to/containers/skullto3d_v0.0.5.sif segment_skull -data /data/skullTo3d_CI_v2/cerimed_marmo -out /data/skullTo3d_CI_v2/cerimed_marmo/results -soft ANTS_skull_robustreg -species marmo -sub Tresor -ses 01 -brain_dt T1 T2 -skull_dt T1 petra CT -deriv -padback


Testing from docker image
------------------------

For testing the docker installation, the beginning of the commands should be replaced by docker run -v /path/to/data:/data macatools/macapype:v0.3.1, e.g.

.. code:: bash

    $ docker run -v /path/to/data:/data macatools/skullto3d:v0.0.5 segment_skull -data /data/skullTo3d_CI_v2/cerimed_marmo -out /data/skullTo3d_CI_v2/cerimed_marmo/results -soft ANTS_skull_robustreg -species marmo -sub Tresor -ses 01 -brain_dt T1 T2 -skull_dt T1 petra CT -deriv -padback

Testing from python package install
-----------------------------------

From pip install
~~~~~~~~~~~~~~~~
.. code:: bash

    $ segment_skull -data /path/to/data/skullTo3d_CI_v2/cerimed_marmo -out /path/to/data/skullTo3d_CI_v2/cerimed_marmo/results -soft ANTS_skull_robustreg -species marmo -sub Tresor -ses 01 -brain_dt T1 T2 -skull_dt T1 petra CT -deriv -padback

From github install
~~~~~~~~~~~~~~~~
.. code:: bash

    $ python workflows/segment_skull.py -data /path/to/data/skullTo3d_CI_v2/cerimed_marmo -out /path/to/data/skullTo3d_CI_v2/cerimed_marmo/results -soft ANTS_skull_robustreg -species marmo -sub Tresor -ses 01  -brain_dt T1 T2 -skull_dt T1 petra CT -deriv -padback

**Note the /path/to/data instead of /data (as in the container install) in the arguments**

Testing the macaque datasets with CT and petra
##############################################

Two other dataset, corresponding to one macaque and one baboon, are available in the test dataset. Please not that due to higher image resolution, the preprocessing will take a longer time.


Testing from Singularity image
------------------------------

Macaque CT petra
~~~~~~~~~~~~~~~~

.. code:: bash

    $ singularity run -B /path/to/data/:/data /path/to/containers/skullto3d_v0.0.5.sif segment_skull  -data /data/skullTo3d_CI_v2/cerimed_macaque -out /data/skullTo3d_CI_v2/cerimed_macaque/results -soft ANTS_skull_robustreg -species macaque -sub Stevie -ses 01 -brain_dt T1 T2 -skull_dt CT petra t1 -deriv -padback

See  :ref:`Commands <command>` for more info on robustreg in soft
