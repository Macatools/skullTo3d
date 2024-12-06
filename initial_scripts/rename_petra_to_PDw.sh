#!/usr/bin/bash

rename -v "s/_petra.nii.gz/_PDw.nii.gz/" sub-*_ses-01_run-*
rename -v "s/_petra.json/_PDw.json/" sub-*_ses-01_run-*


rename -v "s/_acq-0p2mm_PDw.nii.gz/_PDw.nii.gz/" sub-*_ses-01_run-*
rename -v "s/_acq-0p2mm_PDw.json/_PDw.json/" sub-*_ses-01_run-*


rename -v "s/_acq-0p2mm_petra.nii.gz/_PDw.nii.gz/" sub-*_ses-01_run-*
rename -v "s/_acq-0p2mm_petra.json/_PDw.json/" sub-*_ses-01_run-*


rename -v "s/_acq-petra_T2star.nii.gz/_PDw.nii.gz/" sub-*_ses-01_run-*
rename -v "s/_acq-petra_T2star.json/_PDw.json/" sub-*_ses-01_run-*
