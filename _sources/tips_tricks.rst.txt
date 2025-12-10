:orphan:

.. _tips_tricks:

Tips and tricks
_______________

CT images registration to MRI (be it T1w or T2w) can be somehow tricky.

Here a few tricks:

Reorientation can help
######################

The -orient LPS corresponds to the direction where the increasing numbers are pointing at (typically RAS in radiological convention) and take the opposite directions (special AFNI...).

If you want to exchange to axis, change "target" letters accordingly
RPI -> RIP

If you want to revert one dimension, be careful to modify another axis:
RPI -> RPS becomes LPS to exchange I by S, and good R-L dimension as well

.. code:: bash

    $ 3drefit -orient LPS sub-Phoenix_ses-01_acq-CT_T2star.nii.gz

Possibly followed by

.. code:: bash

    $ fslreorient2std sub-Phoenix_ses-01_acq-CT_T2star.nii.gz sub-Phoenix_ses-01_acq-CT_T2star_reorient.nii.gz


Cropping (both T1w et T2w) can help
###################################

Include the full head for the CT image

Be careful with Left-Right orientation
######################################

Most of the images in our center are acquired in the right direction, but with an encoding matching inverse Left-Right Encoding to the one that is coming out of the MRI

.. code:: bash

    $ 3drefit -orient LPI sub-Rusty/ses-01/anat/sub-Rusty_ses-01_acq-CT_run-02_T2star.nii.gz
