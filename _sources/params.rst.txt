.. _params:

Parameters
__________

Adding -params
**************

Definition of the sequence of nodes in processing pipelines, as well as general parameters, are specified by json file. When specifying a -species and -soft (see `Commands <command>`_), the corresponding default parameter file will be used; They are located in the *workflows* directory of the package.

The original parameter file can be altered by some options in -soft (e.g. _robustreg, _prep, etc.; see `Commands <command>`_).

Here is an example of the params.json with parameters -soft ANTS_skull for -species macaque:

.. include:: ../workflows/params_segment_macaque_ants_skull.json
   :literal:

It is also possible to alter values of some nodes for individual sessions/subjects. See `individual parameter section <indiv_params>`_).

**Note**: Individual parameter will not modify the pipeline sequence itself, a value specified in indiv_params for a node that do not exists in params will ignored

Advanced parameters settings
****************************

For advanced user, it is however possible to pass the pipeline sequence as a params.json file. In this case all further alteration will be canceled.

Here is json file with all possible nodes to be tuned; Some node are optional, some nodes are exclusive with each other (XOR). All parameters given here are give as examples and may vary

.. include:: ../examples_doc/params_skull.json
   :literal:

**Note**: The json file provided here only pass the node available in pipelines specific to skullTo3d processing. A functionnal pipeline will also require some pipeline sequence from macapype itself, *a minima* the definition of a short_preparation_pipe sequence of nodes. See `macapype params page <https://macatools.github.io/macapype/params.html>`_ for more details.
