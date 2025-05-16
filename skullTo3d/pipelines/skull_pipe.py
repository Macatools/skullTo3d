"""
    Gather all full pipelines

"""
import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from nipype.interfaces.fsl.maths import (
    DilateImage, ErodeImage,
    ApplyMask, UnaryMaths, Threshold)


import nipype.interfaces.fsl as fsl

from nipype.interfaces.fsl.utils import RobustFOV
from nipype.interfaces.fsl.preprocess import FAST


from nipype.interfaces.niftyreg.regutils import RegResample
from nipype.interfaces.niftyreg.reg import RegAladin

from macapype.utils.utils_nodes import NodeParams

from skullTo3d.nodes.noise import DenoiseImage

from macapype.pipelines.prepare import _create_avg_reorient_pipeline

from macapype.nodes.prepare import average_align

from macapype.nodes.surface import (keep_gcc, IsoSurface)

from macapype.nodes.correct_bias import itk_debias

from skullTo3d.nodes.skull import mask_auto_img

from macapype.nodes.prepare import apply_li_thresh

from macapype.utils.misc import parse_key, get_elem

#################################################
# ####################  T1  #####################
#################################################


def _create_headmask_t1_pipe(name="headmask_t1_pipe", params={}):

    headmask_t1_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['indiv_params', 'stereo_T1']),
        name='inputnode')

    # ### head mask
    # headmask_threshold
    if "t1_head_mask_thr" in params.keys():
        # t1_head_mask_thr
        t1_head_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, 't1_head_mask_thr'),
            name="t1_head_mask_thr")

        headmask_t1_pipe.connect(
            inputnode, "stereo_T1",
            t1_head_mask_thr, "in_file")

        headmask_t1_pipe.connect(
            inputnode, ('indiv_params', parse_key, "t1_head_mask_thr"),
            t1_head_mask_thr, "indiv_params")

    elif "t1_head_auto_mask" in params:

        t1_head_auto_mask = NodeParams(
                interface=niu.Function(
                    input_names=["img_file", "operation",
                                 "index", "sample_bins", "distance", "kmeans"],
                    output_names=["mask_img_file"],
                    function=mask_auto_img),
                params=parse_key(params, "t1_head_auto_mask"),
                name="t1_head_auto_mask")

        headmask_t1_pipe.connect(
            inputnode, "stereo_T1",
            t1_head_auto_mask, "img_file")

        headmask_t1_pipe.connect(
            inputnode, ('indiv_params', parse_key, "t1_head_auto_mask"),
            t1_head_auto_mask, "indiv_params")
    else:

        t1_head_li_mask = pe.Node(
                interface=niu.Function(
                    input_names=["orig_img_file"],
                    output_names=["lithr_img_file"],
                    function=apply_li_thresh),
                name="t1_head_li_mask")

        headmask_t1_pipe.connect(
            inputnode, "stereo_T1",
            t1_head_li_mask, "orig_img_file")

    # t1_head_mask_binary
    t1_head_mask_binary = pe.Node(interface=UnaryMaths(),
                                  name="t1_head_mask_binary")

    t1_head_mask_binary.inputs.operation = 'bin'
    t1_head_mask_binary.inputs.output_type = 'NIFTI_GZ'

    if "t1_head_mask_thr" in params.keys():
        headmask_t1_pipe.connect(
            t1_head_mask_thr, "out_file",
            t1_head_mask_binary, "in_file")

    elif "t1_head_auto_mask" in params.keys():
        headmask_t1_pipe.connect(
            t1_head_auto_mask, "mask_img_file",
            t1_head_mask_binary, "in_file")

    else:
        headmask_t1_pipe.connect(
            t1_head_li_mask, "lithr_img_file",
            t1_head_mask_binary, "in_file")

    if "t1_head_gcc_erode" in params and "t1_head_gcc_dilate" in params:

        # #### gcc erode gcc and dilate back
        # t1_head_gcc_erode
        t1_head_gcc_erode = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "t1_head_gcc_erode"),
            name="t1_head_gcc_erode")

        headmask_t1_pipe.connect(
            t1_head_mask_binary, "out_file",
            t1_head_gcc_erode, "in_file")

        headmask_t1_pipe.connect(
                inputnode, ('indiv_params', parse_key, "t1_head_gcc_erode"),
                t1_head_gcc_erode, "indiv_params")

        # t1_head_mask_binary_clean1
        t1_head_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name="t1_head_gcc")

        headmask_t1_pipe.connect(
            t1_head_gcc_erode, "out_file",
            t1_head_gcc, "nii_file")

        # t1_head_gcc_dilate
        t1_head_gcc_dilate = NodeParams(
            interface=DilateImage(),
            params=parse_key(params, "t1_head_gcc_dilate"),
            name="t1_head_gcc_dilate")

        headmask_t1_pipe.connect(
            t1_head_gcc, "gcc_nii_file",
            t1_head_gcc_dilate, "in_file")

        headmask_t1_pipe.connect(
                inputnode, ('indiv_params',
                            parse_key, "t1_head_gcc_dilate"),
                t1_head_gcc_dilate, "indiv_params")
    else:

        # t1_head_mask_binary_clean1
        t1_head_gcc = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name="t1_head_gcc")

        headmask_t1_pipe.connect(
            t1_head_mask_binary, "out_file",
            t1_head_gcc, "nii_file")

    # ### fill dilate fill and erode back
    # t1_head_dilate
    t1_head_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "t1_head_dilate"),
        name="t1_head_dilate")

    if "t1_head_gcc_erode" in params and "t1_head_gcc_dilate" in params:
        headmask_t1_pipe.connect(
            t1_head_gcc_dilate, "out_file",
            t1_head_dilate, "in_file")
    else:
        headmask_t1_pipe.connect(
            t1_head_gcc, "gcc_nii_file",
            t1_head_dilate, "in_file")

    headmask_t1_pipe.connect(
        inputnode, ('indiv_params', parse_key, "t1_head_dilate"),
        t1_head_dilate, "indiv_params")

    # t1_head_fill
    t1_head_fill = pe.Node(interface=UnaryMaths(),
                           name="t1_head_fill")

    t1_head_fill.inputs.operation = 'fillh'

    headmask_t1_pipe.connect(
        t1_head_dilate, "out_file",
        t1_head_fill, "in_file")

    # t1_head_erode
    t1_head_erode = NodeParams(interface=ErodeImage(),
                               params=parse_key(params, "t1_head_erode"),
                               name="t1_head_erode")

    headmask_t1_pipe.connect(
        t1_head_fill, "out_file",
        t1_head_erode, "in_file")

    headmask_t1_pipe.connect(
        inputnode, ('indiv_params', parse_key, "t1_head_erode"),
        t1_head_erode, "indiv_params")

    # t1_hmasked
    t1_hmasked = pe.Node(interface=ApplyMask(),
                         name="t1_hmasked")

    headmask_t1_pipe.connect(
        inputnode, "stereo_T1",
        t1_hmasked, "in_file")

    headmask_t1_pipe.connect(
        t1_head_erode, "out_file",
        t1_hmasked, "mask_file")

    return headmask_t1_pipe


def _create_skullmask_t1_pipe(name="skullmask_t1_pipe", params={}):

    skullmask_t1_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['indiv_params',
                                      'headmasked_T1',
                                      "headmask"]),
        name='inputnode')

    if "t1_denoise" in params.keys():

        # N4 intensity normalization over T1
        t1_denoise = NodeParams(DenoiseImage(),
                                params=parse_key(params, "t1_denoise"),
                                name='t1_denoise')

        skullmask_t1_pipe.connect(
            inputnode, "headmasked_T1",
            t1_denoise, "input_image")

        skullmask_t1_pipe.connect(
            inputnode, "headmask",
            t1_denoise, "mask_image")

        skullmask_t1_pipe.connect(
            inputnode, ('indiv_params', parse_key, "t1_denoise"),
            t1_denoise, "indiv_params")

    t1_fast = NodeParams(interface=FAST(),
                         params=parse_key(params, "t1_fast"),
                         name="t1_fast")

    if "t1_denoise" in params.keys():
        skullmask_t1_pipe.connect(
            t1_denoise, "output_image",
            t1_fast, "in_files")
    else:
        skullmask_t1_pipe.connect(
            inputnode, "headmasked_T1",
            t1_fast, "in_files")

    skullmask_t1_pipe.connect(
        inputnode, ('indiv_params', parse_key, "t1_fast"),
        t1_fast, "indiv_params")

    # t1_skull_mask_binary
    t1_skull_mask_binary = pe.Node(interface=UnaryMaths(),
                                   name="t1_skull_mask_binary")

    t1_skull_mask_binary.inputs.operation = 'bin'
    t1_skull_mask_binary.inputs.output_type = 'NIFTI_GZ'

    skullmask_t1_pipe.connect(
        t1_fast,
        ("partial_volume_files", get_elem, 0),
        t1_skull_mask_binary, "in_file")

    # t1_head_erode_skin
    if "t1_head_erode_skin" in params.keys():

        t1_head_erode_skin = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "t1_head_erode_skin"),
            name="t1_head_erode_skin")

        skullmask_t1_pipe.connect(
            inputnode, "headmask",
            t1_head_erode_skin, "in_file")

        skullmask_t1_pipe.connect(
            inputnode, ('indiv_params', parse_key, "t1_head_erode_skin"),
            t1_head_erode_skin, "indiv_params")

        # ### Masking with t1_head mask
        # t1_head_hmasked ####### [okey]
        t1_head_skin_masked = pe.Node(interface=ApplyMask(),
                                      name="t1_head_skin_masked")

        skullmask_t1_pipe.connect(
            t1_skull_mask_binary, "out_file",
            t1_head_skin_masked, "in_file")

        skullmask_t1_pipe.connect(
            t1_head_erode_skin, "out_file",
            t1_head_skin_masked, "mask_file")

    if "t1_skull_gcc_erode" in params and \
            "t1_skull_gcc_dilate" in params:

        # t1_skull_erode ####### [okey][json]
        t1_skull_gcc_erode = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "t1_skull_gcc_erode"),
            name="t1_skull_gcc_erode")

        if "t1_head_erode_skin" in params.keys():
            skullmask_t1_pipe.connect(
                t1_head_skin_masked, "out_file",
                t1_skull_gcc_erode, "in_file")
        else:
            skullmask_t1_pipe.connect(
                t1_skull_mask_binary, "out_file",
                t1_skull_gcc_erode, "in_file")

        skullmask_t1_pipe.connect(
            inputnode, ('indiv_params', parse_key, "t1_skull_gcc_erode"),
            t1_skull_gcc_erode, "indiv_params")

        # t1_skull_gcc ####### [okey]
        t1_skull_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name="t1_skull_gcc")

        skullmask_t1_pipe.connect(
            t1_skull_gcc_erode, "out_file",
            t1_skull_gcc, "nii_file")

        # t1_skull_gcc_dilate ####### [okey][json]
        t1_skull_gcc_dilate = NodeParams(
            interface=DilateImage(),
            params=parse_key(params, "t1_skull_gcc_dilate"),
            name="t1_skull_gcc_dilate")

        skullmask_t1_pipe.connect(
            t1_skull_gcc, "gcc_nii_file",
            t1_skull_gcc_dilate, "in_file")

        skullmask_t1_pipe.connect(
            inputnode, ('indiv_params', parse_key, "t1_skull_gcc_dilate"),
            t1_skull_gcc_dilate, "indiv_params")

    else:

        # t1_skull_gcc ####### [okey]
        t1_skull_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name="t1_skull_gcc")

        if "t1_head_erode_skin" in params.keys():
            skullmask_t1_pipe.connect(
                t1_head_skin_masked, "out_file",
                t1_skull_gcc, "nii_file")
        else:
            skullmask_t1_pipe.connect(
                t1_skull_mask_binary, "out_file",
                t1_skull_gcc, "nii_file")

    # t1_skull_dilate ####### [okey][json]
    t1_skull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "t1_skull_dilate"),
        name="t1_skull_dilate")

    if "t1_skull_gcc_erode" in params and \
            "t1_skull_gcc_dilate" in params:

        skullmask_t1_pipe.connect(
            t1_skull_gcc_dilate, "out_file",
            t1_skull_dilate, "in_file")
    else:
        skullmask_t1_pipe.connect(
            t1_skull_gcc, "gcc_nii_file",
            t1_skull_dilate, "in_file")

    skullmask_t1_pipe.connect(
        inputnode, ('indiv_params', parse_key, "t1_skull_dilate"),
        t1_skull_dilate, "indiv_params")

    # t1_skull_t1_fill
    t1_skull_fill = pe.Node(interface=UnaryMaths(),
                            name="t1_skull_fill")

    t1_skull_fill.inputs.operation = 'fillh'

    skullmask_t1_pipe.connect(
        t1_skull_dilate, "out_file",
        t1_skull_fill, "in_file")

    # t1_skull_t1_erode
    t1_skull_erode = NodeParams(interface=ErodeImage(),
                                params=parse_key(params, "t1_skull_erode"),
                                name="t1_skull_erode")

    skullmask_t1_pipe.connect(
        t1_skull_fill, "out_file",
        t1_skull_erode, "in_file")

    skullmask_t1_pipe.connect(
        inputnode, ('indiv_params', parse_key, "t1_skull_erode"),
        t1_skull_erode, "indiv_params")

    # mesh_t1_skull #######
    mesh_t1_skull = pe.Node(
        IsoSurface(),
        name="mesh_t1_skull")

    skullmask_t1_pipe.connect(
        t1_skull_erode, "out_file",
        mesh_t1_skull, "nii_file")

    if "t1_skull_fov" in params.keys():

        # t1_skull_fov ####### [okey][json]
        t1_skull_fov = NodeParams(
            interface=RobustFOV(),
            params=parse_key(params, "t1_skull_fov"),
            name="t1_skull_fov")

        skullmask_t1_pipe.connect(
            t1_skull_erode, "out_file",
            t1_skull_fov, "in_file")

        skullmask_t1_pipe.connect(
            inputnode, ('indiv_params', parse_key, "t1_skull_fov"),
            t1_skull_fov, "indiv_params")

        # t1_skull_clean ####### [okey]
        t1_skull_clean = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name="t1_skull_clean")

        skullmask_t1_pipe.connect(
            t1_skull_fov, "out_roi",
            t1_skull_clean, "nii_file")

        # mesh_robustt1_skull #######
        mesh_robustt1_skull = pe.Node(
            interface=IsoSurface(),
            name="mesh_robustt1_skull")

        skullmask_t1_pipe.connect(
            t1_skull_clean, "gcc_nii_file",
            mesh_robustt1_skull, "nii_file")

    return skullmask_t1_pipe


def create_skull_t1_pipe(name="skull_t1_pipe", params={}):

    skull_t1_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['indiv_params', 'stereo_T1']),
        name='inputnode')

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["t1_skull_mask", "t1_skull_stl",
                    "robustt1_skull_mask", "robustt1_skull_stl",
                    "t1_head_mask"]),
        name='outputnode')

    # Creating headmask_t1_pipe
    if "headmask_t1_pipe" in params:
        headmask_t1_pipe = _create_headmask_t1_pipe(
            name="headmask_t1_pipe", params=params["headmask_t1_pipe"])

        skull_t1_pipe.connect(inputnode, "stereo_T1",
                              headmask_t1_pipe, "inputnode.stereo_T1")

        skull_t1_pipe.connect(inputnode, "indiv_params",
                              headmask_t1_pipe, "inputnode.indiv_params")
    else:
        return skull_t1_pipe

    skull_t1_pipe.connect(
        headmask_t1_pipe, "t1_head_erode.out_file",
        outputnode, "t1_head_mask")

    # Creating skullmask_t1_pipe
    if "skullmask_t1_pipe" in params:
        skullmask_t1_pipe = _create_skullmask_t1_pipe(
            name="skullmask_t1_pipe", params=params["skullmask_t1_pipe"])

        skull_t1_pipe.connect(headmask_t1_pipe, "t1_hmasked.out_file",
                              skullmask_t1_pipe, "inputnode.headmasked_T1")

        skull_t1_pipe.connect(headmask_t1_pipe, "t1_head_erode.out_file",
                              skullmask_t1_pipe, "inputnode.headmask")

        skull_t1_pipe.connect(inputnode, "indiv_params",
                              skullmask_t1_pipe, "inputnode.indiv_params")
    else:
        return skull_t1_pipe

    skull_t1_pipe.connect(
        skullmask_t1_pipe, "mesh_t1_skull.stl_file",
        outputnode, "t1_skull_stl")

    skull_t1_pipe.connect(
        skullmask_t1_pipe, "t1_skull_erode.out_file",
        outputnode, "t1_skull_mask")

    if "t1_skull_fov" in params.keys():
        skull_t1_pipe.connect(
            skullmask_t1_pipe, "t1_skull_fov.out_roi",
            outputnode, "robustt1_skull_mask")

        skull_t1_pipe.connect(
            skullmask_t1_pipe, "mesh_robustt1_skull.stl_file",
            outputnode, "robustt1_skull_stl")

    return skull_t1_pipe

###############################################################################
# #################### CT  ######################
###############################################################################


def _create_skullmask_ct_pipe(name="skullmask_ct_pipe", params={}):

    # Creating pipeline
    skullmask_ct_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['realigned_ct', "indiv_params"]),
        name='inputnode'
    )

    # skullmask_threshold
    if "ct_skull_mask_thr" in params.keys():
        # ct_skull_mask_thr
        ct_skull_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, 'ct_skull_mask_thr'),
            name="ct_skull_mask_thr")

        skullmask_ct_pipe.connect(inputnode, "realigned_ct",
                                  ct_skull_mask_thr, "in_file")

        skullmask_ct_pipe.connect(
            inputnode, ('indiv_params', parse_key, "ct_skull_mask_thr"),
            ct_skull_mask_thr, "indiv_params")

    elif "ct_skull_auto_mask" in params:

        ct_skull_auto_mask = NodeParams(
                interface=niu.Function(
                    input_names=["img_file", "operation",
                                 "index", "sample_bins", "distance", "kmeans"],
                    output_names=["mask_img_file"],
                    function=mask_auto_img),
                params=parse_key(params, "ct_skull_auto_mask"),
                name="ct_skull_auto_mask")

        skullmask_ct_pipe.connect(inputnode, "realigned_ct",
                                  ct_skull_auto_mask, "img_file")

        skullmask_ct_pipe.connect(
            inputnode, ('indiv_params', parse_key, "ct_skull_auto_mask"),
            ct_skull_auto_mask, "indiv_params")
    else:

        ct_skull_li_mask = pe.Node(
                interface=niu.Function(
                    input_names=["orig_img_file"],
                    output_names=["lithr_img_file"],
                    function=apply_li_thresh),
                name="ct_skull_li_mask")

        skullmask_ct_pipe.connect(
            inputnode, "realigned_ct",
            ct_skull_li_mask, "orig_img_file")

    # ct_skull_mask_binary
    ct_skull_mask_binary = pe.Node(interface=UnaryMaths(),
                                   name="ct_skull_mask_binary")

    ct_skull_mask_binary.inputs.operation = 'bin'
    ct_skull_mask_binary.inputs.output_type = 'NIFTI_GZ'

    if "ct_skull_mask_thr" in params.keys():
        skullmask_ct_pipe.connect(
            ct_skull_mask_thr, "out_file",
            ct_skull_mask_binary, "in_file")

    elif "ct_skull_auto_mask" in params.keys():
        skullmask_ct_pipe.connect(
            ct_skull_auto_mask, "mask_img_file",
            ct_skull_mask_binary, "in_file")

    else:
        skullmask_ct_pipe.connect(
            ct_skull_li_mask, "lithr_img_file",
            ct_skull_mask_binary, "in_file")

    # ct_skull_gcc ####### [okey]
    ct_skull_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="ct_skull_gcc")

    skullmask_ct_pipe.connect(
        ct_skull_mask_binary, "out_file",
        ct_skull_gcc, "nii_file")

    # ct_skull_dilate ####### [okey][json]
    ct_skull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "ct_skull_dilate"),
        name="ct_skull_dilate")

    skullmask_ct_pipe.connect(
        ct_skull_gcc, "gcc_nii_file",
        ct_skull_dilate, "in_file")

    skullmask_ct_pipe.connect(
        inputnode, ("indiv_params", parse_key, "ct_skull_dilate"),
        ct_skull_dilate, "indiv_params")

    # ct_skull_fill #######  [okey]
    ct_skull_fill = pe.Node(interface=UnaryMaths(),
                            name="ct_skull_fill")

    ct_skull_fill.inputs.operation = 'fillh'

    skullmask_ct_pipe.connect(
        ct_skull_dilate, "out_file",
        ct_skull_fill, "in_file")

    # ct_skull_erode ####### [okey][json]
    ct_skull_erode = NodeParams(interface=ErodeImage(),
                                params=parse_key(params, "ct_skull_erode"),
                                name="ct_skull_erode")

    skullmask_ct_pipe.connect(
        ct_skull_fill, "out_file",
        ct_skull_erode, "in_file")

    skullmask_ct_pipe.connect(
        inputnode, ("indiv_params", parse_key, "ct_skull_erode"),
        ct_skull_erode, "indiv_params")

    # mesh_ct_skull #######
    mesh_ct_skull = pe.Node(
        interface=IsoSurface(),
        name="mesh_ct_skull")

    skullmask_ct_pipe.connect(
        ct_skull_erode, "out_file",
        mesh_ct_skull, "nii_file")

    if "ct_skull_fov" in params.keys():

        # ct_skull_fov ####### [okey][json]
        ct_skull_fov = NodeParams(
            interface=RobustFOV(),
            params=parse_key(params, "ct_skull_fov"),
            name="ct_skull_fov")

        skullmask_ct_pipe.connect(
            ct_skull_erode, "out_file",
            ct_skull_fov, "in_file")

        skullmask_ct_pipe.connect(
            inputnode, ('indiv_params', parse_key, "ct_skull_fov"),
            ct_skull_fov, "indiv_params")

        # ct_skull_clean ####### [okey]
        ct_skull_clean = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name="ct_skull_clean")

        skullmask_ct_pipe.connect(
            ct_skull_fov, "out_roi",
            ct_skull_clean, "nii_file")

        # mesh_robustct_skull #######
        mesh_robustct_skull = pe.Node(
            interface=IsoSurface(),
            name="mesh_robustct_skull")

        skullmask_ct_pipe.connect(
            ct_skull_clean, "gcc_nii_file",
            mesh_robustct_skull, "nii_file")

        return skullmask_ct_pipe


def create_skull_ct_pipe(name="skull_ct_pipe", params={}):

    # Creating pipeline
    skull_ct_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['ct', 'stereo_T1', 'native_T1',
                                      'native_T2', 'native_to_stereo_trans',
                                      'stereo_T1', 'indiv_params']),
        name='inputnode'
    )

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["stereo_ct_skull_mask", "stereo_ct",
                    "robustct_skull_mask", "robustct_skull_stl",
                    "ct_skull_stl"]),
        name='outputnode')

    if "crop_CT" in params:
        print('crop_CT is in params')

        assert "args" in params["crop_CT"].keys(), \
            "Error, args is not specified for crop node, breaking"

        # cropping
        # Crop bounding box for T1
        crop_CT = NodeParams(fsl.ExtractROI(),
                             params=parse_key(params, 'crop_CT'),
                             name='crop_CT')

        skull_ct_pipe.connect(
            inputnode, ("indiv_params", parse_key, "crop_CT"),
            crop_CT, 'indiv_params')

        skull_ct_pipe.connect(inputnode, 'ct',
                              crop_CT, 'in_file')

    # align_ct_on_T1
    align_ct_on_T1 = pe.Node(interface=RegAladin(),
                             name="align_ct_on_T1")

    align_ct_on_T1.inputs.rig_only_flag = True

    if "crop_CT" in params:
        skull_ct_pipe.connect(
            crop_CT, "roi_file",
            align_ct_on_T1, "flo_file")
    else:
        skull_ct_pipe.connect(
            inputnode, 'ct',
            align_ct_on_T1, "flo_file")

    skull_ct_pipe.connect(inputnode, "native_T1",
                          align_ct_on_T1, "ref_file")

    if "align_ct_on_T1_2" in params:

        # align_ct_on_T1
        align_ct_on_T1_2 = pe.Node(interface=RegAladin(),
                                   name="align_ct_on_T1_2")

        align_ct_on_T1_2.inputs.rig_only_flag = True

        skull_ct_pipe.connect(align_ct_on_T1, 'res_file',
                              align_ct_on_T1_2, "flo_file")

        skull_ct_pipe.connect(inputnode, "native_T1",
                              align_ct_on_T1_2, "ref_file")

    # align_ct_on_stereo_T1
    align_ct_on_stereo_T1 = pe.Node(
        interface=RegResample(pad_val=0.0),
        name="align_ct_on_stereo_T1")

    if "align_ct_on_T1_2" in params:
        skull_ct_pipe.connect(align_ct_on_T1_2, 'res_file',
                              align_ct_on_stereo_T1, "flo_file")

    else:
        skull_ct_pipe.connect(align_ct_on_T1, 'res_file',
                              align_ct_on_stereo_T1, "flo_file")

    skull_ct_pipe.connect(inputnode, 'native_to_stereo_trans',
                          align_ct_on_stereo_T1, "trans_file")

    skull_ct_pipe.connect(inputnode, "stereo_T1",
                          align_ct_on_stereo_T1, "ref_file")
    # output node
    skull_ct_pipe.connect(align_ct_on_stereo_T1, "out_file",
                          outputnode, "stereo_ct")

    if "skullmask_ct_pipe" in params:

        skullmask_ct_pipe = _create_skullmask_ct_pipe(
            name="skullmask_ct_pipe",
            params=params["skullmask_ct_pipe"])

        skull_ct_pipe.connect(align_ct_on_stereo_T1, "out_file",
                              skullmask_ct_pipe, "inputnode.realigned_ct")

        skull_ct_pipe.connect(inputnode, "indiv_params",
                              skullmask_ct_pipe, "inputnode.indiv_params")

    else:
        return skull_ct_pipe

    skull_ct_pipe.connect(skullmask_ct_pipe, "mesh_ct_skull.stl_file",
                          outputnode, "ct_skull_stl")

    skull_ct_pipe.connect(skullmask_ct_pipe, "ct_skull_erode.out_file",
                          outputnode, "stereo_ct_skull_mask")

    if "ct_skull_fov" in params.keys():
        skull_ct_pipe.connect(skullmask_ct_pipe, "ct_skull_fov.out_roi",
                              outputnode, "robustct_skull_mask")

        skull_ct_pipe.connect(skullmask_ct_pipe,
                              "mesh_robustct_skull.stl_file",
                              outputnode, "robustct_skull_stl")

    return skull_ct_pipe


def create_autonomous_skull_ct_pipe(name="skull_ct_pipe", params={}):

    # Creating pipeline
    skull_ct_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['ct', 'indiv_params']),
        name='inputnode'
    )

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["stereo_ct_skull_mask",
                    "robustct_skull_mask", "robustct_skull_stl",
                    "ct_skull_stl"]),
        name='outputnode')

    if "skullmask_ct_pipe" in params:

        skullmask_ct_pipe = _create_skullmask_ct_pipe(
            name="skullmask_ct_pipe",
            params=params["skullmask_ct_pipe"])

        skull_ct_pipe.connect(inputnode, "ct",
                              skullmask_ct_pipe, "inputnode.realigned_ct")

        skull_ct_pipe.connect(inputnode, "indiv_params",
                              skullmask_ct_pipe, "inputnode.indiv_params")

    else:
        return skullmask_ct_pipe

    skull_ct_pipe.connect(skullmask_ct_pipe, "mesh_ct_skull.stl_file",
                          outputnode, "ct_skull_stl")

    skull_ct_pipe.connect(skullmask_ct_pipe, "ct_skull_erode.out_file",
                          outputnode, "stereo_ct_skull_mask")

    if "ct_skull_fov" in params.keys():
        skull_ct_pipe.connect(skullmask_ct_pipe, "ct_skull_fov.out_roi",
                              outputnode, "robustct_skull_mask")

        skull_ct_pipe.connect(skullmask_ct_pipe,
                              "mesh_robustct_skull.stl_file",
                              outputnode, "robustct_skull_stl")

    return skull_ct_pipe


###############################################################################
# #################################  PETRA  ###################################
###############################################################################

def _create_petra_head_mask(name="headmask_petra_pipe", params={}):

    # creating pipeline
    headmask_petra_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['reoriented_petra',
                                      'indiv_params']),
        name='inputnode'
    )

    if "petra_itk_debias" in params.keys():
        # Adding early petra_debias
        petra_itk_debias = pe.Node(
                interface=niu.Function(
                    input_names=["img_file"],
                    output_names=["cor_img_file", "bias_img_file"],
                    function=itk_debias),
                name="petra_itk_debias")

        headmask_petra_pipe.connect(
            inputnode, "reoriented_petra",
            petra_itk_debias, "img_file")

    # ### head mask
    # headmask_threshold
    if "petra_head_mask_thr" in params.keys():
        # petra_head_mask_thr
        petra_head_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, 'petra_head_mask_thr'),
            name="petra_head_mask_thr")

        if "petra_itk_debias" in params.keys():

            headmask_petra_pipe.connect(
                petra_itk_debias, "cor_img_file",
                petra_head_mask_thr, "in_file")
        else:

            headmask_petra_pipe.connect(
                inputnode, "reoriented_petra",
                petra_head_mask_thr, "in_file")

        headmask_petra_pipe.connect(
            inputnode, ('indiv_params', parse_key, "petra_head_mask_thr"),
            petra_head_mask_thr, "indiv_params")

    elif "petra_head_auto_mask" in params:

        petra_head_auto_mask = NodeParams(
                interface=niu.Function(
                    input_names=["img_file", "operation",
                                 "index", "sample_bins", "distance", "kmeans"],
                    output_names=["mask_img_file"],
                    function=mask_auto_img),
                params=parse_key(params, "petra_head_auto_mask"),
                name="petra_head_auto_mask")

        if "petra_itk_debias" in params.keys():

            headmask_petra_pipe.connect(
                petra_itk_debias, "cor_img_file",
                petra_head_auto_mask, "img_file")
        else:

            headmask_petra_pipe.connect(
                inputnode, "reoriented_petra",
                petra_head_auto_mask, "img_file")

        headmask_petra_pipe.connect(
            inputnode, ('indiv_params', parse_key, "petra_head_auto_mask"),
            petra_head_auto_mask, "indiv_params")

    else:

        petra_head_li_mask = pe.Node(
                interface=niu.Function(
                    input_names=["orig_img_file"],
                    output_names=["lithr_img_file"],
                    function=apply_li_thresh),
                name="petra_head_li_mask")

        if "petra_itk_debias" in params.keys():

            headmask_petra_pipe.connect(
                petra_itk_debias, "cor_img_file",
                petra_head_li_mask, "orig_img_file")
        else:

            headmask_petra_pipe.connect(
                inputnode, "reoriented_petra",
                petra_head_li_mask, "orig_img_file")

    # petra_head_mask_binary
    petra_head_mask_binary = pe.Node(interface=UnaryMaths(),
                                     name="petra_head_mask_binary")

    petra_head_mask_binary.inputs.operation = 'bin'
    petra_head_mask_binary.inputs.output_type = 'NIFTI_GZ'

    if "petra_head_mask_thr" in params.keys():
        headmask_petra_pipe.connect(
            petra_head_mask_thr, "out_file",
            petra_head_mask_binary, "in_file")

    elif "petra_head_auto_mask" in params.keys():
        headmask_petra_pipe.connect(
            petra_head_auto_mask, "mask_img_file",
            petra_head_mask_binary, "in_file")

    else:
        headmask_petra_pipe.connect(
            petra_head_li_mask, "lithr_img_file",
            petra_head_mask_binary, "in_file")

    if "petra_head_gcc_erode" in params and "petra_head_gcc_dilate" in params:

        # #### gcc erode gcc and dilate back
        # petra_head_gcc_erode
        petra_head_gcc_erode = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "petra_head_gcc_erode"),
            name="petra_head_gcc_erode")

        headmask_petra_pipe.connect(
            petra_head_mask_binary, "out_file",
            petra_head_gcc_erode, "in_file")

        headmask_petra_pipe.connect(
                inputnode, ('indiv_params', parse_key, "petra_head_gcc_erode"),
                petra_head_gcc_erode, "indiv_params")

        # petra_head_mask_binary_clean1
        petra_head_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name="petra_head_gcc")

        headmask_petra_pipe.connect(
            petra_head_gcc_erode, "out_file",
            petra_head_gcc, "nii_file")

        # petra_head_gcc_dilate
        petra_head_gcc_dilate = NodeParams(
            interface=DilateImage(),
            params=parse_key(params, "petra_head_gcc_dilate"),
            name="petra_head_gcc_dilate")

        headmask_petra_pipe.connect(
            petra_head_gcc, "gcc_nii_file",
            petra_head_gcc_dilate, "in_file")

        headmask_petra_pipe.connect(
                inputnode, ('indiv_params',
                            parse_key, "petra_head_gcc_dilate"),
                petra_head_gcc_dilate, "indiv_params")
    else:

        # petra_head_mask_binary_clean1
        petra_head_gcc = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name="petra_head_gcc")

        headmask_petra_pipe.connect(
            petra_head_mask_binary, "out_file",
            petra_head_gcc, "nii_file")

    # ### fill dilate fill and erode back
    # petra_head_dilate
    petra_head_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "petra_head_dilate"),
        name="petra_head_dilate")

    if "petra_head_gcc_erode" in params and "petra_head_gcc_dilate" in params:
        headmask_petra_pipe.connect(
            petra_head_gcc_dilate, "out_file",
            petra_head_dilate, "in_file")
    else:
        headmask_petra_pipe.connect(
            petra_head_gcc, "gcc_nii_file",
            petra_head_dilate, "in_file")

    headmask_petra_pipe.connect(
        inputnode, ('indiv_params', parse_key, "petra_head_dilate"),
        petra_head_dilate, "indiv_params")

    # petra_head_fill
    petra_head_fill = pe.Node(interface=UnaryMaths(),
                              name="petra_head_fill")

    petra_head_fill.inputs.operation = 'fillh'

    headmask_petra_pipe.connect(
        petra_head_dilate, "out_file",
        petra_head_fill, "in_file")

    # petra_head_erode ####### [okey][json]
    petra_head_erode = NodeParams(interface=ErodeImage(),
                                  params=parse_key(params, "petra_head_erode"),
                                  name="petra_head_erode")

    headmask_petra_pipe.connect(
        petra_head_fill, "out_file",
        petra_head_erode, "in_file")

    headmask_petra_pipe.connect(
        inputnode, ('indiv_params', parse_key, "petra_head_erode"),
        petra_head_erode, "indiv_params")

    # mask_head
    # mesh_petra_head #######
    mesh_petra_head = pe.Node(
        interface=IsoSurface(),
        name="mesh_petra_head")

    headmask_petra_pipe.connect(
        petra_head_erode, "out_file",
        mesh_petra_head, "nii_file")

    # ### Masking with head mask
    # petra_hmasked ####### [okey]
    petra_hmasked = pe.Node(interface=ApplyMask(),
                            name="petra_hmasked")

    if "petra_itk_debias" in params.keys():

        headmask_petra_pipe.connect(
            petra_itk_debias, "cor_img_file",
            petra_hmasked, "in_file")
    else:

        headmask_petra_pipe.connect(
            inputnode, "reoriented_petra",
            petra_hmasked, "in_file")

    headmask_petra_pipe.connect(
        petra_head_erode, "out_file",
        petra_hmasked, "mask_file")

    return headmask_petra_pipe


def _create_petra_skull_mask(name="skullmask_petra_pipe", params={}):

    # creating pipeline
    skullmask_petra_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['headmasked_petra',
                                      "headmask",
                                      'indiv_params']),
        name='inputnode'
    )

    if "petra_denoise" in params.keys():

        # N4 intensity normalization over T1
        petra_denoise = NodeParams(DenoiseImage(),
                                   params=parse_key(params, "petra_denoise"),
                                   name='petra_denoise')

        skullmask_petra_pipe.connect(
            inputnode, "headmasked_petra",
            petra_denoise, "input_image")

        skullmask_petra_pipe.connect(
            inputnode, "headmask",
            petra_denoise, "mask_image")

        skullmask_petra_pipe.connect(
            inputnode, ('indiv_params', parse_key, "petra_denoise"),
            petra_denoise, "indiv_params")

    petra_fast = NodeParams(interface=FAST(),
                            params=parse_key(params, "petra_fast"),
                            name="petra_fast")

    if "petra_denoise" in params.keys():
        skullmask_petra_pipe.connect(
            petra_denoise, "output_image",
            petra_fast, "in_files")
    else:
        skullmask_petra_pipe.connect(
            inputnode, "headmasked_petra",
            petra_fast, "in_files")

    # petra_skull_mask_binary
    petra_skull_mask_binary = pe.Node(interface=UnaryMaths(),
                                      name="petra_skull_mask_binary")

    petra_skull_mask_binary.inputs.operation = 'bin'
    petra_skull_mask_binary.inputs.output_type = 'NIFTI_GZ'

    skullmask_petra_pipe.connect(
        petra_fast, ("partial_volume_files", get_elem, 0),
        petra_skull_mask_binary, "in_file")

    # petra_skull_auto_thresh
    if "petra_head_erode_skin" in params.keys():

        petra_head_erode_skin = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "petra_head_erode_skin"),
            name="petra_head_erode_skin")

        skullmask_petra_pipe.connect(
            inputnode, "headmask",
            petra_head_erode_skin, "in_file")

        skullmask_petra_pipe.connect(
            inputnode, ("indiv_params", parse_key, "petra_head_erode_skin"),
            petra_head_erode_skin, "indiv_params")

        # ### Masking with petra_head mask
        # petra_hmasked ####### [okey]
        petra_skin_masked = pe.Node(interface=ApplyMask(),
                                    name="petra_skin_masked")

        skullmask_petra_pipe.connect(
            petra_skull_mask_binary, "out_file",
            petra_skin_masked, "in_file")

        skullmask_petra_pipe.connect(
            petra_head_erode_skin, "out_file",
            petra_skin_masked, "mask_file")

    if "petra_skull_gcc_erode" in params and \
            "petra_skull_gcc_dilate" in params:

        # petra_skull_erode ####### [okey][json]
        petra_skull_gcc_erode = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "petra_skull_gcc_erode"),
            name="petra_skull_gcc_erode")

        if "petra_head_erode_skin" in params.keys():
            skullmask_petra_pipe.connect(
                petra_skin_masked, "out_file",
                petra_skull_gcc_erode, "in_file")
        else:
            skullmask_petra_pipe.connect(
                petra_skull_mask_binary, "out_file",
                petra_skull_gcc_erode, "in_file")

        skullmask_petra_pipe.connect(
            inputnode, ('indiv_params', parse_key, "petra_skull_gcc_erode"),
            petra_skull_gcc_erode, "indiv_params")

        # petra_skull_gcc ####### [okey]
        petra_skull_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name="petra_skull_gcc")

        skullmask_petra_pipe.connect(
            petra_skull_gcc_erode, "out_file",
            petra_skull_gcc, "nii_file")

        # petra_skull_gcc_dilate ####### [okey][json]
        petra_skull_gcc_dilate = NodeParams(
            interface=DilateImage(),
            params=parse_key(params, "petra_skull_gcc_dilate"),
            name="petra_skull_gcc_dilate")

        skullmask_petra_pipe.connect(
            petra_skull_gcc, "gcc_nii_file",
            petra_skull_gcc_dilate, "in_file")

        skullmask_petra_pipe.connect(
            inputnode, ('indiv_params', parse_key, "petra_skull_gcc_dilate"),
            petra_skull_gcc_dilate, "indiv_params")

    else:

        # petra_skull_gcc ####### [okey]
        petra_skull_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name="petra_skull_gcc")

        if "petra_head_erode_skin" in params.keys():
            skullmask_petra_pipe.connect(
                petra_skin_masked, "out_file",
                petra_skull_gcc, "nii_file")
        else:
            skullmask_petra_pipe.connect(
                petra_skull_mask_binary, "out_file",
                petra_skull_gcc, "nii_file")

    # petra_skull_dilate ####### [okey][json]
    petra_skull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "petra_skull_dilate"),
        name="petra_skull_dilate")

    if "petra_skull_gcc_erode" in params and \
            "petra_skull_gcc_dilate" in params:

        skullmask_petra_pipe.connect(
            petra_skull_gcc_dilate, "out_file",
            petra_skull_dilate, "in_file")
    else:
        skullmask_petra_pipe.connect(
            petra_skull_gcc, "gcc_nii_file",
            petra_skull_dilate, "in_file")

    skullmask_petra_pipe.connect(
        inputnode, ('indiv_params', parse_key, "petra_skull_dilate"),
        petra_skull_dilate, "indiv_params")

    # petra_skull_fill #######  [okey]
    petra_skull_fill = pe.Node(interface=UnaryMaths(),
                               name="petra_skull_fill")

    petra_skull_fill.inputs.operation = 'fillh'

    skullmask_petra_pipe.connect(
        petra_skull_dilate, "out_file",
        petra_skull_fill, "in_file")

    # petra_skull_erode ####### [okey][json]
    petra_skull_erode = NodeParams(
        interface=ErodeImage(),
        params=parse_key(params, "petra_skull_erode"),
        name="petra_skull_erode")

    skullmask_petra_pipe.connect(
        petra_skull_fill, "out_file",
        petra_skull_erode, "in_file")

    skullmask_petra_pipe.connect(
        inputnode, ('indiv_params', parse_key, "petra_skull_erode"),
        petra_skull_erode, "indiv_params")

    # mesh_petra_skull #######
    mesh_petra_skull = pe.Node(
        interface=IsoSurface(),
        name="mesh_petra_skull")

    skullmask_petra_pipe.connect(
        petra_skull_erode, "out_file",
        mesh_petra_skull, "nii_file")

    if "petra_skull_fov" in params.keys():

        # petra_skull_fov ####### [okey][json]
        petra_skull_fov = NodeParams(
            interface=RobustFOV(),
            params=parse_key(params, "petra_skull_fov"),
            name="petra_skull_fov")

        skullmask_petra_pipe.connect(
            petra_skull_erode, "out_file",
            petra_skull_fov, "in_file")

        skullmask_petra_pipe.connect(
            inputnode, ('indiv_params', parse_key, "petra_skull_fov"),
            petra_skull_fov, "indiv_params")

        # petra_skull_clean ####### [okey]
        petra_skull_clean = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name="petra_skull_clean")

        skullmask_petra_pipe.connect(
            petra_skull_fov, "out_roi",
            petra_skull_clean, "nii_file")

        # mesh_robustpetra_skull #######
        mesh_robustpetra_skull = pe.Node(
            interface=IsoSurface(),
            name="mesh_robustpetra_skull")

        skullmask_petra_pipe.connect(
            petra_skull_clean, "gcc_nii_file",
            mesh_robustpetra_skull, "nii_file")

    return skullmask_petra_pipe


def create_autonomous_skull_petra_pipe(name="skull_petra_pipe", params={}):

    # creating pipeline
    skull_petra_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['petra',
                                      'indiv_params']),
        name='inputnode'
    )

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["petra_skull_mask", "petra_skull_stl", "stereo_petra",
                    "robustpetra_skull_mask", "robustpetra_skull_stl",
                    "petra_head_mask", "petra_head_stl"]),
        name='outputnode')

    # average if multiple PETRA
    if "avg_reorient_pipe" in params.keys():
        print("Found avg_reorient_pipe for av_PETRA")

        av_PETRA = _create_avg_reorient_pipeline(
            name="av_PETRA", params=parse_key(params, "avg_reorient_pipe"))

        skull_petra_pipe.connect(inputnode, 'petra',
                                 av_PETRA, "inputnode.list_img")

        skull_petra_pipe.connect(inputnode, 'indiv_params',
                                 av_PETRA, "inputnode.indiv_params")
    else:
        print("Using average_align for av_PETRA")
        print(params)

        av_PETRA = pe.Node(
            niu.Function(input_names=['list_img', "reorient"],
                         output_names=['avg_img'],
                         function=average_align),
            name="av_PETRA")

        skull_petra_pipe.connect(inputnode, 'petra',
                                 av_PETRA, "list_img")

    if "crop_petra" in params:

        # cropping
        # Crop bounding box for petra
        crop_petra = NodeParams(fsl.ExtractROI(),
                                params=parse_key(params, 'crop_petra'),
                                name='crop_petra')

        skull_petra_pipe.connect(
            inputnode, ("indiv_params", parse_key, "crop_petra"),
            crop_petra, 'indiv_params')

        if "avg_reorient_pipe" in params.keys():
            skull_petra_pipe.connect(av_PETRA, 'outputnode.std_img',
                                     crop_petra, 'in_file')
        else:
            skull_petra_pipe.connect(av_PETRA, 'avg_img',
                                     crop_petra, 'in_file')

    # ## headmask
    if "headmask_petra_pipe" in params:

        headmask_pipe = _create_petra_head_mask(
            name="headmask_petra_pipe",
            params=params["headmask_petra_pipe"])
        # TODO

        if "crop_petra" in params:
            skull_petra_pipe.connect(
                crop_petra, "out_file",
                headmask_pipe, "inputnode.reoriented_petra")
        elif "avg_reorient_pipe" in params.keys():
            skull_petra_pipe.connect(
                av_PETRA, 'outputnode.std_img',
                headmask_pipe, "inputnode.reoriented_petra")
        else:
            skull_petra_pipe.connect(
                av_PETRA, 'avg_img',
                headmask_pipe, "inputnode.reoriented_petra")

        skull_petra_pipe.connect(inputnode, "indiv_params",
                                 headmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(headmask_pipe, "petra_head_erode.out_file",
                             outputnode, "petra_head_mask")

    skull_petra_pipe.connect(headmask_pipe, "mesh_petra_head.stl_file",
                             outputnode, "petra_head_stl")

    # ## skull mask
    if "skullmask_petra_pipe" in params:

        skullmask_pipe = _create_petra_skull_mask(
            name="skullmask_petra_pipe",
            params=params["skullmask_petra_pipe"])

        skull_petra_pipe.connect(
            headmask_pipe, "petra_hmasked.out_file",
            skullmask_pipe, "inputnode.headmasked_petra")

        skull_petra_pipe.connect(
            headmask_pipe, "petra_head_erode.out_file",
            skullmask_pipe, "inputnode.headmask")

        skull_petra_pipe.connect(
            inputnode, "indiv_params",
            skullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(skullmask_pipe, "mesh_petra_skull.stl_file",
                             outputnode, "petra_skull_stl")

    skull_petra_pipe.connect(skullmask_pipe, "petra_skull_erode.out_file",
                             outputnode, "petra_skull_mask")

    if "petra_skull_fov" in params.keys():

        skull_petra_pipe.connect(
            skullmask_pipe, "petra_skull_fov.out_roi",
            outputnode, "robustpetra_skull_mask")

        skull_petra_pipe.connect(
            skullmask_pipe, "mesh_robustpetra_skull.stl_file",
            outputnode, "robustpetra_skull_stl")

    return skull_petra_pipe


def create_skull_petra_pipe(name="skull_petra_pipe", params={}):

    # creating pipeline
    skull_petra_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['petra', 'stereo_T1',
                                      'native_img',
                                      'native_to_stereo_trans',
                                      'indiv_params']),
        name='inputnode'
    )

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["petra_skull_mask", "petra_skull_stl", "stereo_petra",
                    "robustpetra_skull_mask", "robustpetra_skull_stl",
                    "petra_head_mask", "petra_head_stl"]),
        name='outputnode')

    # average if multiple PETRA
    if "avg_reorient_pipe" in params.keys():
        print("Found avg_reorient_pipe for av_PETRA")

        av_PETRA = _create_avg_reorient_pipeline(
            name="av_PETRA", params=parse_key(params, "avg_reorient_pipe"))

        skull_petra_pipe.connect(inputnode, 'petra',
                                 av_PETRA, "inputnode.list_img")

        skull_petra_pipe.connect(inputnode, 'indiv_params',
                                 av_PETRA, "inputnode.indiv_params")
    else:
        print("Using average_align for av_PETRA")
        print(params)

        av_PETRA = pe.Node(
            niu.Function(input_names=['list_img', "reorient"],
                         output_names=['avg_img'],
                         function=average_align),
            name="av_PETRA")

        skull_petra_pipe.connect(inputnode, 'petra',
                                 av_PETRA, "list_img")

    # align_petra_on_native
    align_petra_on_native = pe.Node(interface=RegAladin(),
                                    name="align_petra_on_native")

    align_petra_on_native.inputs.rig_only_flag = True

    if "avg_reorient_pipe" in params.keys():
        skull_petra_pipe.connect(av_PETRA, 'outputnode.std_img',
                                 align_petra_on_native, "flo_file")
    else:
        skull_petra_pipe.connect(av_PETRA, 'avg_img',
                                 align_petra_on_native, "flo_file")

    skull_petra_pipe.connect(inputnode, "native_img",
                             align_petra_on_native, "ref_file")

    if "align_petra_on_native_2" in params:

        # align_petra_on_native
        align_petra_on_native_2 = pe.Node(interface=RegAladin(),
                                          name="align_petra_on_native_2")

        align_petra_on_native_2.inputs.rig_only_flag = True

        skull_petra_pipe.connect(align_petra_on_native, 'res_file',
                                 align_petra_on_native_2, "flo_file")

        skull_petra_pipe.connect(inputnode, "native_img",
                                 align_petra_on_native_2, "ref_file")

    # align_petra_on_stereo
    align_petra_on_stereo = pe.Node(
        interface=RegResample(pad_val=0.0),
        name="align_petra_on_stereo")

    if "align_petra_on_native_2" in params:
        skull_petra_pipe.connect(
            align_petra_on_native_2, 'res_file',
            align_petra_on_stereo, "flo_file")

    else:
        skull_petra_pipe.connect(
            align_petra_on_native, 'res_file',
            align_petra_on_stereo, "flo_file")

    skull_petra_pipe.connect(inputnode, 'native_to_stereo_trans',
                             align_petra_on_stereo, "trans_file")

    skull_petra_pipe.connect(inputnode, 'stereo_T1',
                             align_petra_on_stereo, "ref_file")
    # outputnode
    skull_petra_pipe.connect(align_petra_on_stereo, "out_file",
                             outputnode, "stereo_petra")

    # ## headmask
    if "headmask_petra_pipe" in params:

        headmask_pipe = _create_petra_head_mask(
            name="headmask_petra_pipe",
            params=params["headmask_petra_pipe"])
        # TODO
        skull_petra_pipe.connect(
            align_petra_on_stereo, "out_file",
            headmask_pipe, "inputnode.reoriented_petra")

        skull_petra_pipe.connect(
            inputnode, "indiv_params",
            headmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(headmask_pipe, "petra_head_erode.out_file",
                             outputnode, "petra_head_mask")

    skull_petra_pipe.connect(headmask_pipe, "mesh_petra_head.stl_file",
                             outputnode, "petra_head_stl")

    # ## skull mask
    if "skullmask_petra_pipe" in params:

        skullmask_pipe = _create_petra_skull_mask(
            name="skullmask_petra_pipe",
            params=params["skullmask_petra_pipe"])

        skull_petra_pipe.connect(
            headmask_pipe, "petra_hmasked.out_file",
            skullmask_pipe, "inputnode.headmasked_petra")

        skull_petra_pipe.connect(
            headmask_pipe, "petra_head_erode.out_file",
            skullmask_pipe, "inputnode.headmask")

        skull_petra_pipe.connect(
            inputnode, "indiv_params",
            skullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(skullmask_pipe, "mesh_petra_skull.stl_file",
                             outputnode, "petra_skull_stl")

    skull_petra_pipe.connect(skullmask_pipe, "petra_skull_erode.out_file",
                             outputnode, "petra_skull_mask")

    if "petra_skull_fov" in params.keys():

        skull_petra_pipe.connect(
            skullmask_pipe, "petra_skull_fov.out_roi",
            outputnode, "robustpetra_skull_mask")

        skull_petra_pipe.connect(
            skullmask_pipe, "mesh_robustpetra_skull.stl_file",
            outputnode, "robustpetra_skull_stl")

    return skull_petra_pipe
