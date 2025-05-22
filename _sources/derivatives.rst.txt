:orphan:

.. _derivatives:

***********
Derivatives
***********

Introduction
************

Depending on the options provided by command line and params.json, different files will ouput

Derivatives will be output if option ``-deriv`` is provided to the command line (See `Commands <command>`_):

All files are by default in stereo space; if option ``-padback`` is provided to the command line (See `Commands <command>`), files in native  will also be output.

For all files provided by macapype, see `Derivatives <https://macatools.github.io/macapype/derivatives.html>`_ and see `Derivatives <https://macatools.github.io/macapype/derivatives.html>`_


Data Preparation (Padded files)
*******************************

**If pad_template is defined in params (normalily used to coregister stereo to petra, T1w and CT):**

*sub-Stevie_ses-01_space-stereo_desc-pad_T1w.nii.gz*

*sub-Stevie_ses-01_space-stereo_desc-pad_T2w.nii.gz*

|

**Some files computed with macapype are put in the same space after pad:**

*sub-Stevie_ses-01_space-stereo_desc-pad_desc-brain_mask.nii.gz*

*sub-Stevie_ses-01_space-stereo_desc-pad_desc-brain_dseg.nii.gz*

|

**If ``-pad`` is defined in command line (See `Commands <commands>`):**

*sub-Stevie_ses-01_space-native_desc-pad_T1w.nii.gz*

*sub-Stevie_ses-01_space-native_desc-pad_T2w.nii.gz*

|

Petra Skull extraction
**********************

|

**Petra in stereo space:**

*sub-Stevie_ses-01_space-stereo_desc-petra_PDw.nii.gz*

|
**Headmask in stereo and native (normally corresponding to native T1w) spaces:**

*sub-Stevie_ses-01_space-stereo_desc-petra_headmask.nii.gz*

*sub-Stevie_ses-01_space-native_desc-petra_headmask.nii.gz*

|

**Skullmask in stereo and native (normally corresponding to native T1w) spaces:**

*sub-Stevie_ses-01_space-stereo_desc-petra_skullmask.nii.gz*

*sub-Stevie_ses-01_space-native_desc-petra_skullmask.nii.gz*

|

**Meshes of headmask and skullmask:**

*sub-Stevie_ses-01_desc-petra_skullmask.stl*

*sub-Stevie_ses-01_desc-petra_headmask.stl*

T1w Skull extraction
********************


**Headmask in stereo and native spaces:**

*sub-Stevie_ses-01_space-stereo_desc-t1_headmask.nii.gz*

*sub-Stevie_ses-01_space-native_desc-t1_headmask.nii.gz*

|

**Skullmask in stereo and native spaces:**

*sub-Stevie_ses-01_space-stereo_desc-t1_skullmask.nii.gz*

*sub-Stevie_ses-01_space-native_desc-t1_skullmask.nii.gz*

|

**Meshes of headmask and skullmask:**

*sub-Stevie_ses-01_desc-t1_skullmask.stl*

*sub-Stevie_ses-01_desc-t1_headmask.stl* (is missing so far)

|

CT Skull extraction
*******************

|

**CT file in stereo space:**

*sub-Stevie_ses-01_space-stereo_desc-ct_T2star.nii.gz*

|

**Skullmask in stereo and native spaces:**

*sub-Stevie_ses-01_space-stereo-ct_skullmask.nii.gz*

*sub-Stevie_ses-01_space-native_desc-ct_skullmask.nii.gz*

|

**Mesh of skullmask:**

*sub-Stevie_ses-01_desc-ct_skullmask.stl*


|

**NB** if pad_template is defined (as normally is by default in all skullTo3d parameter files...) , stereo corresponds to desc-pad files for macapype processing.
