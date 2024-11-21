.. _indiv_params:

Individual Parameters
_____________________

Adding -indiv
*************

You can include "-indiv indiv_params.json" in the python command, for specifiying parameters specific parameters:

.. code:: bash

    $ python workflows/segment_petra.py -data ~/Data_maca -out ./local_test -soft SPM -params params.json -indiv indiv_params.json

Advanced parameters settings
****************************


Here is json file with all possible nodes to be tuned in indiv_params; In particular, the specifications of sub- and ses- are mandatory before the specification of nodes; Also note that, as for `macapype individual paramters <https://macatools.github.io/macapype/indiv_params.html>`_, the nodes are specified directly, without specifiying the sub-pipelines they belong to.

Please refer to the `parameter page <params>`_ for more explanation on the possible structure of nodes.

.. include:: ../examples_doc/indiv_params_skull.json
   :literal:
