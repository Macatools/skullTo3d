"""
    Gather all full pipelines

"""
import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from nipype.interfaces.fsl.maths import (
    DilateImage, ErodeImage, BinaryMaths,
    ApplyMask, UnaryMaths, Threshold)

from nipype.interfaces.ants import DenoiseImage, N4BiasFieldCorrection

from nipype.interfaces.fsl.utils import RobustFOV
from nipype.interfaces.fsl.preprocess import FAST, FLIRT


from nipype.interfaces.niftyreg.reg import RegAladin
from nipype.interfaces.niftyreg.regutils import RegResample

from macapype.utils.utils_nodes import NodeParams

from nodes.skull import (
    mask_auto_threshold,
    keep_gcc, wrap_nii2mesh, wrap_nii2mesh_old,
    pad_zero_mri)

from macapype.pipelines.prepare import _create_avg_reorient_pipeline

from macapype.nodes.prepare import average_align

from macapype.utils.misc import parse_key

#################################################
# ####################  T1  #####################
#################################################


def create_skull_t1_pipe(name="skull_t1_pipe", params={}):

    # Creating pipeline
    skull_t1_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['brainmask', 't1', 'debiased_T1',
                                      'indiv_params', 'stereo_native_T1',
                                      'native_to_stereo_trans']),
        name='inputnode')

    # align_on_stereo_native_T1
    align_on_stereo_native_T1 = pe.Node(interface=RegResample(pad_val=0.0),
                                        name="align_on_stereo_native_T1")

    skull_t1_pipe.connect(inputnode, 't1',
                          align_on_stereo_native_T1, "flo_file")

    skull_t1_pipe.connect(inputnode, 'native_to_stereo_trans',
                          align_on_stereo_native_T1, "trans_file")

    skull_t1_pipe.connect(inputnode, "stereo_native_T1",
                          align_on_stereo_native_T1, "ref_file")

    # t1_head_mask
    if "t1_head_mask_thr" in params.keys():

        t1_head_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, "t1_head_mask_thr"),
            name="t1_head_mask_thr")

        skull_t1_pipe.connect(align_on_stereo_native_T1, "out_file",
                              t1_head_mask_thr, "in_file")

    else:
        # t1_head_auto_thresh
        t1_head_auto_thresh = pe.Node(
            interface=niu.Function(
                input_names=["img_file", "operation", "index"],
                output_names=["mask_threshold"],
                function=mask_auto_threshold),
            name="t1_head_auto_thresh")

        # t1_head_auto_thresh.inputs.operation = "max"
        t1_head_auto_thresh.inputs.operation = "min"
        t1_head_auto_thresh.inputs.index = 1

        skull_t1_pipe.connect(align_on_stereo_native_T1, "out_file",
                              t1_head_auto_thresh, "img_file")

        # t1_head_mask_thr
        t1_head_mask_thr = pe.Node(interface=Threshold(),
                                   name="t1_head_mask_thr")

        skull_t1_pipe.connect(t1_head_auto_thresh, "mask_threshold",
                              t1_head_mask_thr, "thresh")

        skull_t1_pipe.connect(align_on_stereo_native_T1, "out_file",
                              t1_head_mask_thr, "in_file")

    # t1_head_mask_binary
    t1_head_mask_binary = pe.Node(interface=UnaryMaths(),
                                  name="t1_head_mask_binary")

    t1_head_mask_binary.inputs.operation = 'bin'
    t1_head_mask_binary.inputs.output_type = 'NIFTI_GZ'

    skull_t1_pipe.connect(t1_head_mask_thr, "out_file",
                          t1_head_mask_binary, "in_file")

    # keep_gcc_t1_head
    keep_gcc_t1_head = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["gcc_nii_file"],
                               function=keep_gcc),
        name="keep_gcc_t1_head")

    skull_t1_pipe.connect(t1_head_mask_binary, "out_file",
                          keep_gcc_t1_head, "nii_file")

    # t1_head_dilate
    t1_head_dilate = NodeParams(interface=DilateImage(),
                                params=parse_key(params, "t1_head_dilate"),
                                name="t1_head_dilate")

    skull_t1_pipe.connect(keep_gcc_t1_head, "gcc_nii_file",
                          t1_head_dilate, "in_file")

    # t1_head_fill
    t1_head_fill = pe.Node(interface=UnaryMaths(),
                           name="t1_head_fill")

    t1_head_fill.inputs.operation = 'fillh'

    skull_t1_pipe.connect(t1_head_dilate, "out_file",
                          t1_head_fill, "in_file")

    # t1_head_erode
    t1_head_erode = NodeParams(interface=ErodeImage(),
                               params=parse_key(params, "t1_head_erode"),
                               name="t1_head_erode")

    skull_t1_pipe.connect(t1_head_fill, "out_file",
                          t1_head_erode, "in_file")

    # t1_hmasked
    t1_hmasked = pe.Node(interface=ApplyMask(),
                         name="t1_hmasked")

    skull_t1_pipe.connect(align_on_stereo_native_T1, "out_file",
                          t1_hmasked, "in_file")

    skull_t1_pipe.connect(t1_head_erode, "out_file",
                          t1_hmasked, "mask_file")

    # fast_t1
    t1_fast = NodeParams(interface=FAST(),
                         params=parse_key(params, "t1_fast"),
                         name="t1_fast")

    skull_t1_pipe.connect(t1_hmasked, "out_file",
                          t1_fast, "in_files")

    # t1_hmasked_recip
    t1_hmasked_recip = pe.Node(
         interface=UnaryMaths(),
         name="t1_hmasked_recip")

    t1_hmasked_recip.inputs.operation = 'recip'

    skull_t1_pipe.connect(t1_fast, "restored_image",
                          t1_hmasked_recip, "in_file")

    # t1_hmasked_log
    t1_hmasked_log = pe.Node(
        interface=UnaryMaths(),
        name="t1_hmasked_log")

    t1_hmasked_log.inputs.operation = 'log'

    skull_t1_pipe.connect(t1_hmasked_recip, "out_file",
                          t1_hmasked_log, "in_file")

    # t1_hmasked_inv
    t1_hmasked_inv = pe.Node(
        interface=BinaryMaths(),
        name="t1_hmasked_inv")

    skull_t1_pipe.connect(t1_hmasked_log, "out_file",
                          t1_hmasked_inv, "in_file")

    t1_hmasked_inv.inputs.operation = 'mul'
    t1_hmasked_inv.inputs.operand_value = -1

    # t1_skull_mask_thr
    t1_skull_mask_thr = NodeParams(
        interface=Threshold(),
        params=parse_key(params, "t1_skull_mask_thr"),
        name="t1_skull_mask_thr")

    skull_t1_pipe.connect(t1_hmasked_inv, "out_file",
                          t1_skull_mask_thr, "in_file")

    # t1_skull_mask_bin
    t1_skull_mask_bin = pe.Node(interface=UnaryMaths(),
                                name="t1_skull_mask_bin")

    t1_skull_mask_bin.inputs.operation = 'bin'
    t1_skull_mask_bin.inputs.output_type = 'NIFTI_GZ'

    skull_t1_pipe.connect(t1_skull_mask_thr, "out_file",
                          t1_skull_mask_bin, "in_file")

    # t1_head_erode_skin
    if "t1_head_erode_skin" in params.keys():

        t1_head_erode_skin = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "t1_head_erode_skin"),
            name="t1_head_erode_skin")

        skull_t1_pipe.connect(t1_head_erode, "out_file",
                              t1_head_erode_skin, "in_file")

        # ### Masking with t1_head mask
        # t1_head_hmasked ####### [okey]
        t1_head_skin_masked = pe.Node(interface=ApplyMask(),
                                      name="t1_head_skin_masked")

        skull_t1_pipe.connect(t1_skull_mask_bin, "out_file",
                              t1_head_skin_masked, "in_file")

        skull_t1_pipe.connect(t1_head_erode_skin, "out_file",
                              t1_head_skin_masked, "mask_file")

    # t1_skull_gcc ####### [okey]
    t1_skull_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="t1_skull_gcc")

    if "t1_head_erode_skin" in params.keys():

        skull_t1_pipe.connect(t1_head_skin_masked, "out_file",
                              t1_skull_gcc, "nii_file")
    else:
        skull_t1_pipe.connect(t1_skull_mask_bin, "out_file",
                              t1_skull_gcc, "nii_file")

    # t1_skull_dilate
    t1_skull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "t1_skull_dilate"),
        name="t1_skull_dilate")

    skull_t1_pipe.connect(t1_skull_gcc, "gcc_nii_file",
                          t1_skull_dilate, "in_file")

    # t1_skull_t1_fill
    t1_skull_fill = pe.Node(interface=UnaryMaths(),
                            name="t1_skull_fill")

    t1_skull_fill.inputs.operation = 'fillh'

    skull_t1_pipe.connect(t1_skull_dilate, "out_file",
                          t1_skull_fill, "in_file")

    # t1_skull_t1_erode
    t1_skull_erode = NodeParams(interface=ErodeImage(),
                                params=parse_key(params, "t1_skull_erode"),
                                name="t1_skull_erode")

    skull_t1_pipe.connect(t1_skull_fill, "out_file",
                          t1_skull_erode, "in_file")

    # mesh_t1_skull_t1 #######
    mesh_t1_skull_t1 = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh),
        name="mesh_t1_skull_t1")

    skull_t1_pipe.connect(t1_skull_erode, "out_file",
                          mesh_t1_skull_t1, "nii_file")

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["t1_skull_mask", "t1_skull_stl", "head_mask"]),
        name='outputnode')

    skull_t1_pipe.connect(t1_head_erode, "out_file",
                          outputnode, "t1_head_mask")

    skull_t1_pipe.connect(mesh_t1_skull_t1, "stl_file",
                          outputnode, "t1_skull_stl")

    skull_t1_pipe.connect(t1_skull_erode, "out_file",
                          outputnode, "t1_skull_mask")

    return skull_t1_pipe

#################################################
# #################### CT  ######################
#################################################


def create_skull_ct_pipe(name="skull_ct_pipe", params={}):

    # Creating pipeline
    skull_ct_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['ct', 'stereo_native_T1', 'native_T1',
                                      'native_T2', 'native_to_stereo_trans',
                                      'stereo_native_T1', 'indiv_params']),
        name='inputnode'
    )

    # align_ct_on_T1
    align_ct_on_T1 = pe.Node(interface=RegAladin(),
                             name="align_ct_on_T1")

    skull_ct_pipe.connect(inputnode, 'ct',
                          align_ct_on_T1, "flo_file")

    skull_ct_pipe.connect(inputnode, "native_T1",
                          align_ct_on_T1, "ref_file")

    # align_ct_on_stereo_native_T1
    align_ct_on_stereo_native_T1 = pe.Node(interface=RegResample(pad_val=0.0),
                                           name="align_ct_on_stereo_native_T1")

    skull_ct_pipe.connect(align_ct_on_T1, 'res_file',
                          align_ct_on_stereo_native_T1, "flo_file")

    skull_ct_pipe.connect(inputnode, 'native_to_stereo_trans',
                          align_ct_on_stereo_native_T1, "trans_file")

    skull_ct_pipe.connect(inputnode, "stereo_native_T1",
                          align_ct_on_stereo_native_T1, "ref_file")

    # ct_thr ####### Direct apres aligner
    ct_skull_mask_thr = NodeParams(
        interface=Threshold(),
        params=parse_key(params, "ct_skull_mask_thr"),
        name="ct_skull_mask_thr")

    skull_ct_pipe.connect(align_ct_on_stereo_native_T1, "out_file",
                          ct_skull_mask_thr, "in_file")

    skull_ct_pipe.connect(inputnode, "indiv_params",
                          ct_skull_mask_thr, "indiv_params")

    # ct_binary ####### [okey]
    ct_skull_mask_binary = pe.Node(interface=UnaryMaths(),
                                   name="ct_skull_mask_binary")

    ct_skull_mask_binary.inputs.operation = 'bin'
    ct_skull_mask_binary.inputs.output_type = 'NIFTI_GZ'

    skull_ct_pipe.connect(ct_skull_mask_thr, "out_file",
                          ct_skull_mask_binary, "in_file")

    # ct_skull_gcc ####### [okey]
    ct_skull_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="ct_skull_gcc")

    skull_ct_pipe.connect(ct_skull_mask_binary, "out_file",
                          ct_skull_gcc, "nii_file")

    # ct_skull_dilate ####### [okey][json]
    ct_skull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "ct_skull_dilate"),
        name="ct_skull_dilate")

    skull_ct_pipe.connect(ct_skull_gcc, "gcc_nii_file",
                          ct_skull_dilate, "in_file")

    # ct_skull_fill #######  [okey]
    ct_skull_fill = pe.Node(interface=UnaryMaths(),
                            name="ct_skull_fill")

    ct_skull_fill.inputs.operation = 'fillh'

    skull_ct_pipe.connect(ct_skull_dilate, "out_file",
                          ct_skull_fill, "in_file")

    # ct_skull_erode ####### [okey][json]
    ct_skull_erode = NodeParams(interface=ErodeImage(),
                                params=parse_key(params, "ct_skull_erode"),
                                name="ct_skull_erode")

    skull_ct_pipe.connect(ct_skull_fill, "out_file",
                          ct_skull_erode, "in_file")

    # mesh_ct_skull #######
    mesh_ct_skull = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh_old),
        name="mesh_ct_skull")

    skull_ct_pipe.connect(ct_skull_erode, "out_file",
                          mesh_ct_skull, "nii_file")

    # ct_skull_fov
    ct_skull_fov = NodeParams(interface=RobustFOV(),
                              params=parse_key(params, "ct_skull_fov"),
                              name="ct_skull_fov")

    skull_ct_pipe.connect(ct_skull_erode, "out_file",
                          ct_skull_fov, "in_file")

    # ct_skull_gcc ####### [okey]
    ct_skull_fov_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="ct_skull_fov_gcc")

    skull_ct_pipe.connect(ct_skull_fov, "out_roi",
                          ct_skull_fov_gcc, "nii_file")

    # mesh_ct_skull_fov #######
    mesh_ct_skull_fov = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh_old),
        name="mesh_ct_skull_fov")

    skull_ct_pipe.connect(ct_skull_fov_gcc, "gcc_nii_file",
                          mesh_ct_skull_fov, "nii_file")

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["stereo_ct_skull_mask",
                    "ct_skull_stl", "ct_skull_fov_stl"]),
        name='outputnode')

    skull_ct_pipe.connect(mesh_ct_skull, "stl_file",
                          outputnode, "ct_skull_stl")

    skull_ct_pipe.connect(mesh_ct_skull_fov, "stl_file",
                          outputnode, "ct_skull_fov_stl")

    skull_ct_pipe.connect(ct_skull_erode, "out_file",
                          outputnode, "stereo_ct_skull_mask")

    return skull_ct_pipe

# ##################################################
# ####################  PETRA  #####################
# ##################################################


def create_skull_petra_pipe(name="skull_petra_pipe", params={}):

    # creating pipeline
    skull_petra_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['petra', 'stereo_native_T1',
                                      'native_img',
                                      'native_to_stereo_trans',
                                      'indiv_params']),
        name='inputnode'
    )

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

    """
    # align_petra_on_T1
    align_petra_on_T1 = pe.Node(interface=FLIRT(),
                                name="align_petra_on_T1")

    align_petra_on_T1.inputs.apply_xfm = True
    align_petra_on_T1.inputs.uses_qform = True
    align_petra_on_T1.inputs.interp = 'spline'

    skull_petra_pipe.connect(av_PETRA, 'avg_img',
                               align_petra_on_T1, "in_file")

    skull_petra_pipe.connect(inputnode, "native_T1",
                               align_petra_on_T1, "reference")
    """

    # align_petra_on_native
    align_petra_on_native = pe.Node(interface=FLIRT(),
                                    name="align_petra_on_native")

    align_petra_on_native.inputs.apply_xfm = True
    align_petra_on_native.inputs.uses_qform = True
    align_petra_on_native.inputs.interp = 'spline'

    if "avg_reorient_pipe" in params.keys():
        skull_petra_pipe.connect(av_PETRA, 'outputnode.std_img',
                                 align_petra_on_native, "in_file")
    else:
        skull_petra_pipe.connect(av_PETRA, 'avg_img',
                                   align_petra_on_native, "in_file")

    skull_petra_pipe.connect(inputnode, "native_img",
                             align_petra_on_native, "reference")

    # align_petra_on_stereo_native_T1
    align_petra_on_stereo_native_T1 = pe.Node(
        interface=RegResample(pad_val=0.0),
        name="align_petra_on_stereo_native_T1")

    skull_petra_pipe.connect(align_petra_on_native, 'out_file',
                             align_petra_on_stereo_native_T1, "flo_file")

    skull_petra_pipe.connect(inputnode, 'native_to_stereo_trans',
                             align_petra_on_stereo_native_T1, "trans_file")

    skull_petra_pipe.connect(inputnode, "stereo_native_T1",
                             align_petra_on_stereo_native_T1, "ref_file")

    # ### head mask
    # headmask_threshold
    if "petra_head_mask_thr" in params.keys():
        # petra_head_mask_thr
        petra_head_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, 'petra_head_mask_thr'),
            name="petra_head_mask_thr")

        skull_petra_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                                 petra_head_mask_thr, "in_file")

        skull_petra_pipe.connect(
            inputnode, ('indiv_params', parse_key, "petra_head_mask_thr"),
            petra_head_mask_thr, "indiv_params")
    else:
        if "petra_head_auto_thresh" in params.keys():
            # petra_head_auto_thresh
            petra_head_auto_thresh = NodeParams(
                interface=niu.Function(
                    input_names=["img_file", "operation", "index"],
                    output_names=["mask_threshold"],
                    function=mask_auto_threshold),
                params=parse_key(params, "petra_head_auto_thresh"),
                name="petra_head_auto_thresh")

        else:
            # petra_head_auto_thresh
            petra_head_auto_thresh = pe.Node(
                interface=niu.Function(
                    input_names=["img_file", "operation", "index"],
                    output_names=["mask_threshold"],
                    function=mask_auto_threshold),
                name="petra_head_auto_thresh")

            # petra_head_auto_thresh.inputs.operation = "max"
            petra_head_auto_thresh.inputs.operation = "min"
            petra_head_auto_thresh.inputs.index = 1

        skull_petra_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                                 petra_head_auto_thresh, "img_file")

        # petra_head_mask_thr
        petra_head_mask_thr = pe.Node(interface=Threshold(),
                                      name="petra_head_mask_thr")

        skull_petra_pipe.connect(petra_head_auto_thresh, "mask_threshold",
                                 petra_head_mask_thr, "thresh")
        skull_petra_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                                 petra_head_mask_thr, "in_file")

    # petra_head_mask_binary
    petra_head_mask_binary = pe.Node(interface=UnaryMaths(),
                                     name="petra_head_mask_binary")

    petra_head_mask_binary.inputs.operation = 'bin'
    petra_head_mask_binary.inputs.output_type = 'NIFTI_GZ'

    skull_petra_pipe.connect(petra_head_mask_thr, "out_file",
                             petra_head_mask_binary, "in_file")

    # petra_head_mask_binary_clean1
    petra_head_gcc = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["gcc_nii_file"],
                               function=keep_gcc),
        name="petra_head_gcc")

    skull_petra_pipe.connect(petra_head_mask_binary, "out_file",
                             petra_head_gcc, "nii_file")

    # petra_head_dilate
    petra_head_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "petra_head_dilate"),
        name="petra_head_dilate")

    skull_petra_pipe.connect(petra_head_gcc, "gcc_nii_file",
                             petra_head_dilate, "in_file")

    # petra_head_fill
    petra_head_fill = pe.Node(interface=UnaryMaths(),
                              name="petra_head_fill")

    petra_head_fill.inputs.operation = 'fillh'

    skull_petra_pipe.connect(petra_head_dilate, "out_file",
                             petra_head_fill, "in_file")

    # petra_head_erode ####### [okey][json]
    petra_head_erode = NodeParams(interface=ErodeImage(),
                                  params=parse_key(params, "petra_head_erode"),
                                  name="petra_head_erode")

    skull_petra_pipe.connect(petra_head_fill, "out_file",
                             petra_head_erode, "in_file")

    # ### Masking with head mask
    # petra_hmasked ####### [okey]
    petra_hmasked = pe.Node(interface=ApplyMask(),
                            name="petra_hmasked")

    skull_petra_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                             petra_hmasked, "in_file")

    skull_petra_pipe.connect(petra_head_erode, "out_file",
                             petra_hmasked, "mask_file")

    # petra_fast
    petra_fast = NodeParams(interface=FAST(),
                            params=parse_key(params, "petra_fast"),
                            name="petra_fast")

    skull_petra_pipe.connect(petra_hmasked, "out_file",
                             petra_fast, "in_files")

    # petra_skull_auto_thresh
    if "petra_skull_mask_thr" in params.keys():

        # petra_skull_mask_thr ####### [okey][json]
        petra_skull_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, "petra_skull_mask_thr"),
            name="petra_skull_mask_thr")

        petra_skull_mask_thr.inputs.direction = 'above'

        skull_petra_pipe.connect(
            inputnode, ("indiv_params", parse_key, "petra_skull_mask_thr"),
            petra_skull_mask_thr, "indiv_params")

        skull_petra_pipe.connect(petra_fast, "restored_image",
                                 petra_skull_mask_thr, "in_file")
    else:
        if "petra_skull_auto_thresh" in params.keys():

            petra_skull_auto_thresh = NodeParams(
                interface=niu.Function(
                    input_names=["img_file", "operation", "index"],
                    output_names=["mask_threshold"],
                    function=mask_auto_threshold),
                params=parse_key(params, "petra_skull_auto_thresh"),
                name="petra_skull_auto_thresh")

            skull_petra_pipe.connect(
                inputnode, ("indiv_params", parse_key,
                            "petra_skull_auto_thresh"),
                petra_skull_auto_thresh, "indiv_params")

        else:
            petra_skull_auto_thresh = pe.Node(
                interface=niu.Function(
                    input_names=["img_file", "operation", "index"],
                    output_names=["mask_threshold"],
                    function=mask_auto_threshold),
                name="petra_skull_auto_thresh")

            # petra_skull_auto_thresh.inputs.operation = "max"
            petra_skull_auto_thresh.inputs.operation = "min"
            petra_skull_auto_thresh.inputs.index = 1

        skull_petra_pipe.connect(petra_fast, "restored_image",
                                 petra_skull_auto_thresh, "img_file")

        # petra_skull_mask_thr ####### [okey][json]
        petra_skull_mask_thr = pe.Node(
            interface=Threshold(),
            name="petra_skull_mask_thr")

        petra_skull_mask_thr.inputs.direction = 'above'

        skull_petra_pipe.connect(petra_skull_auto_thresh,
                                 "mask_threshold",
                                 petra_skull_mask_thr, "thresh")

        skull_petra_pipe.connect(petra_fast, "restored_image",
                                 petra_skull_mask_thr, "in_file")

    # petra_skull_auto_thresh
    if "petra_head_erode_skin" in params.keys():

        petra_head_erode_skin = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, "petra_head_erode_skin"),
            name="petra_head_erode_skin")

        skull_petra_pipe.connect(petra_head_erode, "out_file",
                                 petra_head_erode_skin, "in_file")

        # ### Masking with petra_head mask
        # petra_hmasked ####### [okey]
        petra_skin_masked = pe.Node(interface=ApplyMask(),
                                    name="petra_skin_masked")

        skull_petra_pipe.connect(petra_skull_mask_thr, "out_file",
                                 petra_skin_masked, "in_file")

        skull_petra_pipe.connect(petra_head_erode_skin, "out_file",
                                 petra_skin_masked, "mask_file")

    # petra_skull_gcc ####### [okey]
    petra_skull_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="petra_skull_gcc")

    if "petra_head_erode_skin" in params.keys():

        skull_petra_pipe.connect(petra_skin_masked, "out_file",
                                 petra_skull_gcc, "nii_file")
    else:
        skull_petra_pipe.connect(petra_skull_mask_thr, "out_file",
                                 petra_skull_gcc, "nii_file")

    # petra_skull_dilate ####### [okey][json]
    petra_skull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "petra_skull_dilate"),
        name="petra_skull_dilate")

    skull_petra_pipe.connect(petra_skull_gcc, "gcc_nii_file",
                             petra_skull_dilate, "in_file")

    # petra_skull_fill #######  [okey]
    petra_skull_fill = pe.Node(interface=UnaryMaths(),
                               name="petra_skull_fill")

    petra_skull_fill.inputs.operation = 'fillh'

    skull_petra_pipe.connect(petra_skull_dilate, "out_file",
                             petra_skull_fill, "in_file")

    # petra_skull_erode ####### [okey][json]
    petra_skull_erode = NodeParams(
        interface=ErodeImage(),
        params=parse_key(params, "petra_skull_erode"),
        name="petra_skull_erode")

    skull_petra_pipe.connect(petra_skull_fill, "out_file",
                             petra_skull_erode, "in_file")

    # mesh_petra_skull #######
    mesh_petra_skull = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh_old),
        name="mesh_petra_skull")


    skull_petra_pipe.connect(petra_skull_erode, "out_file",
                             mesh_petra_skull, "nii_file")

    if "petra_skull_fov" in params.keys():

        # petra_skull_fov ####### [okey][json]

        petra_skull_fov = NodeParams(
            interface=RobustFOV(),
            params=parse_key(params, "petra_skull_fov"),
            name="petra_skull_fov")

        skull_petra_pipe.connect(petra_skull_erode, "out_file",
                                 petra_skull_fov, "in_file")

        # petra_skull_clean ####### [okey]
        petra_skull_clean = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name="petra_skull_clean")

        skull_petra_pipe.connect(petra_skull_fov, "out_roi",
                                 petra_skull_clean, "nii_file")

        # mesh_robustpetra_skull #######
        mesh_robustpetra_skull = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["stl_file"],
                                   function=wrap_nii2mesh_old),
            name="mesh_robustpetra_skull")

        skull_petra_pipe.connect(petra_skull_clean, "gcc_nii_file",
                                 mesh_robustpetra_skull, "nii_file")

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["petra_skull_mask", "petra_skull_stl",
                    "robustpetra_skull_mask", "robustpetra_skull_stl",
                    "petra_head_mask"]),
        name='outputnode')

    skull_petra_pipe.connect(petra_head_erode, "out_file",
                             outputnode, "petra_head_mask")

    skull_petra_pipe.connect(mesh_petra_skull, "stl_file",
                             outputnode, "petra_skull_stl")

    skull_petra_pipe.connect(petra_skull_erode, "out_file",
                             outputnode, "petra_skull_mask")

    if "petra_skull_fov" in params.keys():
        skull_petra_pipe.connect(petra_skull_fov, "out_roi",
                                 outputnode, "robustpetra_skull_mask")

        skull_petra_pipe.connect(mesh_robustpetra_skull, "stl_file",
                                outputnode, "robustpetra_skull_stl")

    return skull_petra_pipe
