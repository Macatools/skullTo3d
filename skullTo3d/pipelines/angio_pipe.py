﻿"""
    Gather all full pipelines

"""
import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from nipype.interfaces.fsl.maths import (
    DilateImage, ErodeImage,
    ApplyMask, UnaryMaths, Threshold)

from nipype.interfaces.fsl.utils import RobustFOV
from nipype.interfaces.fsl.preprocess import FAST, FLIRT


from nipype.interfaces.niftyreg.regutils import RegResample
from nipype.interfaces.niftyreg.reg import RegAladin

from macapype.utils.utils_nodes import NodeParams

from nipype.interfaces.ants import N4BiasFieldCorrection
from nipype.interfaces.ants.segmentation import DenoiseImage

from macapype.pipelines.prepare import _create_avg_reorient_pipeline

from macapype.nodes.prepare import average_align

from macapype.nodes.surface import (keep_gcc, wrap_afni_IsoSurface)

from skullTo3d.nodes.skull import (
    mask_auto_img)

from macapype.utils.misc import parse_key, get_elem

###############################################################################
# #################### CT  ######################
###############################################################################


def create_angio_pipe(name="angio_pipe", params={}):

    # Creating pipeline
    angio_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['angio', 'stereo_T1', 'native_T1',
                                      'native_T2', 'native_to_stereo_trans',
                                      'stereo_T1', 'indiv_params']),
        name='inputnode'
    )

    # align_angio_on_T1
    align_angio_on_T1 = pe.Node(interface=RegAladin(),
                                name="align_angio_on_T1")

    angio_pipe.connect(inputnode, 'angio',
                       align_angio_on_T1, "flo_file")

    angio_pipe.connect(inputnode, "native_T1",
                       align_angio_on_T1, "ref_file")

    # align_angio_on_stereo_T1
    align_angio_on_stereo_T1 = pe.Node(
        interface=RegResample(pad_val=0.0),
        name="align_angio_on_stereo_T1")

    angio_pipe.connect(align_angio_on_T1, 'res_file',
                       align_angio_on_stereo_T1, "flo_file")

    angio_pipe.connect(inputnode, 'native_to_stereo_trans',
                       align_angio_on_stereo_T1, "trans_file")

    angio_pipe.connect(inputnode, "stereo_T1",
                       align_angio_on_stereo_T1, "ref_file")

    # angio_denoise
    angio_denoise = NodeParams(interface=DenoiseImage(),
                               params=parse_key(params, "angio_denoise"),
                               name="angio_denoise")

    angio_pipe.connect(
        align_angio_on_stereo_T1, 'out_file',
        angio_denoise, 'input_image')

    # outputs
    #angio_pipe.connect(denoise_T1, 'output_image',
                                      #outputnode, 'preproc_T1')

    return angio_pipe

    # angio_auto_thresh
    if "angio_mask_thr" in params.keys():

        print("*** angio_mask_thr ***")

        # angio_mask_thr ####### [okey][json]
        angio_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, "angio_mask_thr"),
            name="angio_mask_thr")

        angio_mask_thr.inputs.direction = 'above'

        angio_pipe.connect(
            inputnode, ("indiv_params", parse_key, "angio_mask_thr"),
            angio_mask_thr, "indiv_params")

        angio_pipe.connect(align_angio_on_stereo_T1, "out_file",
                              angio_mask_thr, "in_file")
    else:

        print("*** angio_auto_mask ***")

        angio_auto_mask = NodeParams(
                interface=niu.Function(
                    input_names=["img_file", "operation",
                                 "index", "sample_bins", "distance", "kmeans"],
                    output_names=["mask_img_file"],
                    function=mask_auto_img),
                params=parse_key(params, "angio_auto_mask"),
                name="angio_auto_mask")

        angio_pipe.connect(align_angio_on_stereo_T1, "out_file",
                              angio_auto_mask, "img_file")

        angio_pipe.connect(
            inputnode, ("indiv_params", parse_key, "angio_auto_mask"),
            angio_auto_mask, "indiv_params")

    # angio_mask_binary
    angio_mask_binary = pe.Node(interface=UnaryMaths(),
                                   name="angio_mask_binary")

    angio_mask_binary.inputs.operation = 'bin'
    angio_mask_binary.inputs.output_type = 'NIFTI_GZ'

    if "angio_mask_thr" in params.keys():

        angio_pipe.connect(angio_mask_thr, "out_file",
                              angio_mask_binary, "in_file")
    else:

        angio_pipe.connect(angio_auto_mask, "mask_img_file",
                              angio_mask_binary, "in_file")

    # angio_gcc ####### [okey]
    angio_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="angio_gcc")

    angio_pipe.connect(angio_mask_binary, "out_file",
                          angio_gcc, "nii_file")

    # angio_dilate ####### [okey][json]
    angio_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "angio_dilate"),
        name="angio_dilate")

    angio_pipe.connect(angio_gcc, "gcc_nii_file",
                          angio_dilate, "in_file")

    # angio_fill #######  [okey]
    angio_fill = pe.Node(interface=UnaryMaths(),
                            name="angio_fill")

    angio_fill.inputs.operation = 'fillh'

    angio_pipe.connect(angio_dilate, "out_file",
                          angio_fill, "in_file")

    # angio_erode ####### [okey][json]
    angio_erode = NodeParams(interface=ErodeImage(),
                                params=parse_key(params, "angio_erode"),
                                name="angio_erode")

    angio_pipe.connect(angio_fill, "out_file",
                          angio_erode, "in_file")

    # mesh_angio_skull #######
    mesh_angio_skull = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_afni_IsoSurface),
        name="mesh_angio_skull")

    angio_pipe.connect(angio_erode, "out_file",
                          mesh_angio_skull, "nii_file")

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["stereo_angio_mask",
                    "angio_stl"]),
        name='outputnode')

    angio_pipe.connect(mesh_angio_skull, "stl_file",
                          outputnode, "angio_stl")

    angio_pipe.connect(angio_erode, "out_file",
                          outputnode, "stereo_angio_mask")

    return angio_pipe