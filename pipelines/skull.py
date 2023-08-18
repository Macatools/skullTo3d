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
    skull_segment_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['brainmask', 't1', 'debiased_T1',
                                      'indiv_params','stereo_native_T1',
                                      'native_to_stereo_trans']),
        name='inputnode')

    # align_on_stereo_native_T1
    align_on_stereo_native_T1 = pe.Node(interface=RegResample(pad_val=0.0),
                                        name="align_on_stereo_native_T1")

    skull_segment_pipe.connect(inputnode, 't1',
                               align_on_stereo_native_T1, "flo_file")

    skull_segment_pipe.connect(inputnode, 'native_to_stereo_trans',
                               align_on_stereo_native_T1, "trans_file")

    skull_segment_pipe.connect(inputnode, "stereo_native_T1",
                               align_on_stereo_native_T1, "ref_file")

    # fast_t1
    fast_t1 = NodeParams(interface=FAST(),
                         params=parse_key(params, "fast_t1"),
                         name="fast_t1")

    skull_segment_pipe.connect(align_on_stereo_native_T1, "out_file",
                               fast_t1, "in_files")

    # fast2_t1
    fast2_t1 = NodeParams(interface=FAST(),
                          params=parse_key(params, "fast2_t1"),
                          name="fast2_t1")

    skull_segment_pipe.connect(fast_t1, "restored_image",
                               fast2_t1, "in_files")

    #pad_fast2
    #pad_fast2 = NodeParams(
        #interface=niu.Function(
            #input_names=["img_file", "pad_val"],
            #output_names=["img_padded_file"],
            #function=pad_zero_mri),
        #params=parse_key(params, "pad_fast2"),
        #name="pad_fast2")

    #skull_segment_pipe.connect(fast2_t1, "restored_image",
                               #pad_fast2, "img_file")

    
    # head_mask
    head_mask = NodeParams(interface=Threshold(),
                           params=parse_key(params, "head_mask"),
                           name="head_mask")

    skull_segment_pipe.connect(fast2_t1, "restored_image",
                               head_mask, "in_file")

    # head_mask_binary
    head_mask_binary = pe.Node(interface=UnaryMaths(),
                               name="head_mask_binary")

    head_mask_binary.inputs.operation = 'bin'
    head_mask_binary.inputs.output_type = 'NIFTI_GZ'

    skull_segment_pipe.connect(head_mask, "out_file",
                               head_mask_binary, "in_file")

    # keep_gcc_head
    keep_gcc_head = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["gcc_nii_file"],
                               function=keep_gcc),
        name="keep_gcc_head")

    skull_segment_pipe.connect(head_mask_binary, "out_file",
                               keep_gcc_head, "nii_file")

    # head_dilate
    head_dilate = NodeParams(interface=DilateImage(),
                             params=parse_key(params, "head_dilate"),
                             name="head_dilate")

    skull_segment_pipe.connect(keep_gcc_head, "gcc_nii_file",
                               head_dilate, "in_file")

    # head_fill
    head_fill = pe.Node(interface=UnaryMaths(),
                        name="head_fill")

    head_fill.inputs.operation = 'fillh'

    skull_segment_pipe.connect(head_dilate, "out_file",
                               head_fill, "in_file")

    # head_erode
    head_erode = NodeParams(interface=ErodeImage(),
                            params=parse_key(params, "head_erode"),
                            name="head_erode")

    skull_segment_pipe.connect(head_fill, "out_file",
                               head_erode, "in_file")
    
    # padded_fast2_t1_hmasked
    padded_fast2_t1_hmasked = pe.Node(interface=ApplyMask(),
                                 name="padded_fast2_t1_hmasked")

    skull_segment_pipe.connect(fast2_t1, "restored_image",
                               padded_fast2_t1_hmasked, "in_file")

    skull_segment_pipe.connect(head_erode, "out_file",
                               padded_fast2_t1_hmasked, "mask_file")

    # padded_fast2_t1_hmasked_recip
    padded_fast2_t1_hmasked_recip = pe.Node(
         interface=UnaryMaths(),
         name="padded_fast2_t1_hmasked_recip")

    padded_fast2_t1_hmasked_recip.inputs.operation = 'recip'

    skull_segment_pipe.connect(padded_fast2_t1_hmasked, "out_file",
                               padded_fast2_t1_hmasked_recip, "in_file")

    # padded_fast2_t1_hmasked_recip_log
    padded_fast2_t1_hmasked_recip_log = pe.Node(
        interface=UnaryMaths(),
        name="padded_fast2_t1_hmasked_recip_log")

    padded_fast2_t1_hmasked_recip_log.inputs.operation = 'log'

    skull_segment_pipe.connect(padded_fast2_t1_hmasked_recip, "out_file",
                               padded_fast2_t1_hmasked_recip_log, "in_file")

    # padded_fast2_t1_hmasked_maths
    padded_fast2_t1_hmasked_maths = NodeParams(
        interface=BinaryMaths(),
        params=parse_key(params, "padded_fast2_t1_hmasked_maths"),
        name="padded_fast2_t1_hmasked_maths")

    skull_segment_pipe.connect(padded_fast2_t1_hmasked_recip_log, "out_file",
                               padded_fast2_t1_hmasked_maths, "in_file")

    # skull_t1
    skull_t1 = NodeParams(
        interface=Threshold(),
        params=parse_key(params, "skull_t1"),
        name="skull_t1")

    skull_segment_pipe.connect(padded_fast2_t1_hmasked_maths, "out_file",
                               skull_t1, "in_file")

    # skull_t1_gcc
    skull_t1_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="skull_t1_gcc")

    skull_segment_pipe.connect(skull_t1, "out_file",
                               skull_t1_gcc, "nii_file")

    # skull_t1_gcc_dilated
    skull_t1_gcc_dilated = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "skull_t1_gcc_dilated"),
        name="skull_t1_gcc_dilated")

    skull_segment_pipe.connect(skull_t1_gcc, "gcc_nii_file",
                               skull_t1_gcc_dilated, "in_file")

    # skull_t1_fill
    skull_t1_fill = pe.Node(interface=UnaryMaths(),
                         name="skull_t1_fill")

    skull_t1_fill.inputs.operation = 'fillh'

    skull_segment_pipe.connect(skull_t1_gcc_dilated, "out_file",
                               skull_t1_fill, "in_file")

    # skull_t1_erode
    skull_t1_erode = NodeParams(interface=ErodeImage(),
                                  params=parse_key(params, "skull_t1_erode"),
                                  name="skull_t1_erode")

    skull_segment_pipe.connect(skull_t1_fill, "out_file",
                               skull_t1_erode, "in_file")

    # skull_t1_bin
    skull_t1_bin = pe.Node(interface=UnaryMaths(),
                           name="skull_t1_bin")

    skull_t1_bin.inputs.operation = 'bin'
    skull_t1_bin.inputs.output_type = 'NIFTI_GZ'

    skull_segment_pipe.connect(skull_t1_erode, "out_file",
                               skull_t1_bin, "in_file")

    # skull_t1_bin_gc
    skull_t1_bin_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="skull_t1_bin_gcc")

    skull_segment_pipe.connect(skull_t1_bin, "out_file",
                               skull_t1_bin_gcc, "nii_file")

    # mesh_skull_t1 #######
    mesh_skull_t1 = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh),
        name="mesh_skull_t1")

    skull_segment_pipe.connect(skull_t1_bin_gcc, "gcc_nii_file",
                               mesh_skull_t1, "nii_file")

    #creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["skull_mask", "skull_stl", "head_mask"]),
        name='outputnode')

    skull_segment_pipe.connect(head_erode, "out_file",
                               outputnode, "head_mask")

    skull_segment_pipe.connect(mesh_skull_t1, "stl_file",
                               outputnode, "skull_stl")

    skull_segment_pipe.connect(skull_t1_bin_gcc, "gcc_nii_file",
                               outputnode, "skull_mask")

   
    return skull_segment_pipe

#################################################
# #################### CT  ######################
#################################################


def create_skull_ct_pipe(name="skull_ct_pipe", params={}):

    # Creating pipeline
    skull_segment_pipe = pe.Workflow(name=name)

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

    skull_segment_pipe.connect(inputnode, 'ct',
                               align_ct_on_T1, "flo_file")

    skull_segment_pipe.connect(inputnode, "native_T1",
                               align_ct_on_T1, "ref_file")

    # align_ct_on_stereo_native_T1
    align_ct_on_stereo_native_T1 = pe.Node(interface=RegResample(pad_val=0.0),
                                           name="align_ct_on_stereo_native_T1")

    skull_segment_pipe.connect(align_ct_on_T1, 'res_file',
                               align_ct_on_stereo_native_T1, "flo_file")

    skull_segment_pipe.connect(inputnode, 'native_to_stereo_trans',
                               align_ct_on_stereo_native_T1, "trans_file")

    skull_segment_pipe.connect(inputnode, "stereo_native_T1",
                               align_ct_on_stereo_native_T1, "ref_file")

    # ct_thr ####### Direct apres aligner
    ct_thr = NodeParams(
        interface=Threshold(),
        params=parse_key(params, "ct_thr"),
        name="ct_thr")

    skull_segment_pipe.connect(align_ct_on_stereo_native_T1, "out_file",
                               ct_thr, "in_file")

    skull_segment_pipe.connect(inputnode, "indiv_params",
                               ct_thr, "indiv_params")


    # ct_binary ####### [okey]
    ct_binary = pe.Node(interface=UnaryMaths(),
                        name="ct_binary")

    ct_binary.inputs.operation = 'bin'
    ct_binary.inputs.output_type = 'NIFTI_GZ'

    skull_segment_pipe.connect(ct_thr, "out_file",
                               ct_binary, "in_file")

    # skull_gcc ####### [okey]
    skull_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="skull_gcc")

    skull_segment_pipe.connect(ct_binary, "out_file",
                               skull_gcc, "nii_file")

    # skull_gcc_dilated ####### [okey][json]
    skull_gcc_dilated = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "skull_gcc_dilated"),
        name="skull_gcc_dilated")

    # skull_segment_pipe.connect(ct_binary, "out_file",
    skull_segment_pipe.connect(skull_gcc, "gcc_nii_file",
                               skull_gcc_dilated, "in_file")

    # skull_fill #######  [okey]
    skull_fill = pe.Node(interface=UnaryMaths(),
                         name="skull_fill")

    skull_fill.inputs.operation = 'fillh'

    skull_segment_pipe.connect(skull_gcc_dilated, "out_file",
                               skull_fill, "in_file")

    # skull_fill_erode ####### [okey][json]
    skull_fill_erode = NodeParams(interface=ErodeImage(),
                                  params=parse_key(params, "skull_fill_erode"),
                                  name="skull_fill_erode")

    skull_segment_pipe.connect(skull_fill, "out_file",
                               skull_fill_erode, "in_file")

    # mesh_skull #######
    mesh_skull = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh_old),
        name="mesh_skull")

    skull_segment_pipe.connect(skull_fill_erode, "out_file",
                               mesh_skull, "nii_file")

    # skull_fov
    skull_fov = NodeParams(interface=RobustFOV(),
                           params=parse_key(params, "skull_fov"),
                           name="skull_fov")

    skull_segment_pipe.connect(skull_fill_erode, "out_file",
                               skull_fov, "in_file")

    # skull_gcc ####### [okey]
    skull_fov_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="skull_fov_gcc")

    skull_segment_pipe.connect(skull_fov, "out_roi",
                               skull_fov_gcc, "nii_file")

    # mesh_skull_fov #######
    mesh_skull_fov = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh_old),
        name="mesh_skull_fov")

    skull_segment_pipe.connect(skull_fov_gcc, "gcc_nii_file",
                               mesh_skull_fov, "nii_file")

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["stereo_skull_mask", "skull_stl", "skull_fov_stl"]),
        name='outputnode')

    skull_segment_pipe.connect(mesh_skull, "stl_file",
                               outputnode, "skull_stl")

    skull_segment_pipe.connect(mesh_skull_fov, "stl_file",
                               outputnode, "skull_fov_stl")

    skull_segment_pipe.connect(skull_fill_erode, "out_file",
                               outputnode, "stereo_skull_mask")

    return skull_segment_pipe

# ##################################################
# ####################  PETRA  #####################
# ##################################################


def create_skull_petra_pipe(name="skull_petra_pipe", params={}):

    # creating pipeline
    skull_segment_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['petra', 'stereo_native_T1', 'native_img',
                                      'native_to_stereo_trans',
                                      'indiv_params']),
        name='inputnode'
    )

    # average if multiple PETRA
    if "avg_reorient_pipe" in params.keys():
        print("Found avg_reorient_pipe for av_PETRA")

        av_PETRA = _create_avg_reorient_pipeline(
            name="av_PETRA", params=parse_key(params, "avg_reorient_pipe"))

        skull_segment_pipe.connect(inputnode, 'petra',
                                   av_PETRA, "inputnode.list_img")

        skull_segment_pipe.connect(inputnode, 'indiv_params',
                                   av_PETRA, "inputnode.indiv_params")
    else:
        print("Using average_align for av_PETRA")
        print(params)

        av_PETRA = pe.Node(
            niu.Function(input_names=['list_img', "reorient"],
                         output_names=['avg_img'],
                         function=average_align),
            name="av_PETRA")

        skull_segment_pipe.connect(inputnode, 'petra',
                                   av_PETRA, "list_img")

    """
    # align_petra_on_T1
    align_petra_on_T1 = pe.Node(interface=FLIRT(),
                                name="align_petra_on_T1")

    align_petra_on_T1.inputs.apply_xfm = True
    align_petra_on_T1.inputs.uses_qform = True
    align_petra_on_T1.inputs.interp = 'spline'

    skull_segment_pipe.connect(av_PETRA, 'avg_img',
                               align_petra_on_T1, "in_file")

    skull_segment_pipe.connect(inputnode, "native_T1",
                               align_petra_on_T1, "reference")
    """

    # align_petra_on_native
    align_petra_on_native = pe.Node(interface=FLIRT(),
                                name="align_petra_on_native")

    align_petra_on_native.inputs.apply_xfm = True
    align_petra_on_native.inputs.uses_qform = True
    align_petra_on_native.inputs.interp = 'spline'

    if "avg_reorient_pipe" in params.keys():
        skull_segment_pipe.connect(av_PETRA, 'outputnode.std_img',
                                   align_petra_on_native, "in_file")
    else:
        skull_segment_pipe.connect(av_PETRA, 'avg_img',
                                   align_petra_on_native, "in_file")

    skull_segment_pipe.connect(inputnode, "native_img",
                               align_petra_on_native, "reference")

    # align_petra_on_stereo_native_T1
    align_petra_on_stereo_native_T1 = pe.Node(
        interface=RegResample(pad_val=0.0),
        name="align_petra_on_stereo_native_T1")

    skull_segment_pipe.connect(align_petra_on_native, 'out_file',
                               align_petra_on_stereo_native_T1, "flo_file")

    skull_segment_pipe.connect(inputnode, 'native_to_stereo_trans',
                               align_petra_on_stereo_native_T1, "trans_file")

    skull_segment_pipe.connect(inputnode, "stereo_native_T1",
                               align_petra_on_stereo_native_T1, "ref_file")

    # ### head mask
    # headmask_threshold
    if "head_mask" in params.keys():
        # head_mask
        head_mask = NodeParams(interface=Threshold(),
                            params=parse_key(params, 'head_mask'),
                            name="head_mask")

        skull_segment_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                                head_mask, "in_file")

        skull_segment_pipe.connect(inputnode,
                                ('indiv_params', parse_key, "head_mask"),
                                head_mask, "indiv_params")
    else:
        # headmask_threshold_value
        headmask_threshold_value = pe.Node(
            interface=niu.Function(input_names=["img_file", "operation", "index"],
                                output_names=["mask_threshold"],
                                function=mask_auto_threshold),
            name="headmask_threshold_value")

        headmask_threshold_value.inputs.operation = "min"
        headmask_threshold_value.inputs.index = 1

        skull_segment_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                                headmask_threshold_value, "img_file")

        # head_mask
        head_mask = pe.Node(interface=Threshold(),
                            name="head_mask")

        skull_segment_pipe.connect(headmask_threshold_value, "mask_threshold",
                                head_mask, "thresh")
        skull_segment_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                                head_mask, "in_file")

        skull_segment_pipe.connect(inputnode,
                                ('indiv_params', parse_key, "head_mask"),
                                head_mask, "indiv_params")

    # head_mask_binary
    head_mask_binary = pe.Node(interface=UnaryMaths(),
                               name="head_mask_binary")

    head_mask_binary.inputs.operation = 'bin'
    head_mask_binary.inputs.output_type = 'NIFTI_GZ'

    skull_segment_pipe.connect(head_mask, "out_file",
                               head_mask_binary, "in_file")

    # head_mask_binary_clean1
    keep_gcc_head = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["gcc_nii_file"],
                               function=keep_gcc),
        name="keep_gcc_head")

    skull_segment_pipe.connect(head_mask_binary, "out_file",
                               keep_gcc_head, "nii_file")

    # head_dilate
    head_dilate = NodeParams(interface=DilateImage(),
                             params=parse_key(params, "head_dilate"),
                             name="head_dilate")

    skull_segment_pipe.connect(keep_gcc_head, "gcc_nii_file",
                               head_dilate, "in_file")

    # head_fill
    head_fill = pe.Node(interface=UnaryMaths(),
                        name="head_fill")

    head_fill.inputs.operation = 'fillh'

    skull_segment_pipe.connect(head_dilate, "out_file",
                               head_fill, "in_file")

    # head_erode ####### [okey][json]
    head_erode = NodeParams(interface=ErodeImage(),
                            params=parse_key(params, "head_erode"),
                            name="head_erode")

    skull_segment_pipe.connect(head_fill, "out_file",
                               head_erode, "in_file")

    # ### Masking with head mask
    # fast_petra_hmasked ####### [okey]
    fast_petra_hmasked = pe.Node(interface=ApplyMask(),
                                 name="fast_petra_hmasked")

    skull_segment_pipe.connect(align_petra_on_stereo_native_T1, "out_file",
                               fast_petra_hmasked, "in_file")

    skull_segment_pipe.connect(head_erode, "out_file",
                               fast_petra_hmasked, "mask_file")

    # fast_petra
    fast_petra = NodeParams(interface=FAST(),
                            params=parse_key(params, "fast_petra"),
                            name="fast_petra")

    skull_segment_pipe.connect(fast_petra_hmasked, "out_file",
                               fast_petra, "in_files")

    # skull_extraction_threshold_value
    skull_extraction_threshold_value = pe.Node(
        interface=niu.Function(input_names=["img_file", "operation", "index"],
                               output_names=["mask_threshold"],
                               function=mask_auto_threshold),
        name="skull_extraction_threshold_value")

    skull_extraction_threshold_value.inputs.operation = "mean"
    skull_extraction_threshold_value.inputs.index = 1

    skull_segment_pipe.connect(fast_petra, "restored_image",
                               skull_extraction_threshold_value, "img_file")

    # fast_petra_hmasked_thr ####### [okey][json]
    fast_petra_hmasked_thr = pe.Node(
        interface=Threshold(),
        name="fast_petra_hmasked_thr")

    fast_petra_hmasked_thr.inputs.direction = 'above'

    skull_segment_pipe.connect(skull_extraction_threshold_value,
                               "mask_threshold",
                               fast_petra_hmasked_thr, "thresh")

    skull_segment_pipe.connect(fast_petra, "restored_image",
                               fast_petra_hmasked_thr, "in_file")

    # skull_gcc ####### [okey]
    skull_gcc = pe.Node(
        interface=niu.Function(
            input_names=["nii_file"],
            output_names=["gcc_nii_file"],
            function=keep_gcc),
        name="skull_gcc")

    skull_segment_pipe.connect(fast_petra_hmasked_thr, "out_file",
                               skull_gcc, "nii_file")

    # skull_gcc_dilated ####### [okey][json]
    skull_gcc_dilated = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, "skull_gcc_dilated"),
        name="skull_gcc_dilated")

    skull_segment_pipe.connect(skull_gcc, "gcc_nii_file",
                               skull_gcc_dilated, "in_file")

    # skull_fill #######  [okey]
    skull_fill = pe.Node(interface=UnaryMaths(),
                         name="skull_fill")

    skull_fill.inputs.operation = 'fillh'

    skull_segment_pipe.connect(skull_gcc_dilated, "out_file",
                               skull_fill, "in_file")

    # skull_fill_erode ####### [okey][json]
    skull_fill_erode = NodeParams(interface=ErodeImage(),
                                  params=parse_key(params, "skull_fill_erode"),
                                  name="skull_fill_erode")

    skull_segment_pipe.connect(skull_fill, "out_file",
                               skull_fill_erode, "in_file")

    # skull_bmask_cleaning ####### [okey]
    skull_bmask_cleaning = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["gcc_nii_file"],
                               function=keep_gcc),
        name="skull_bmask_cleaning")

    skull_segment_pipe.connect(skull_fill_erode, "out_file",
                               skull_bmask_cleaning, "nii_file")

    # mesh_skull #######
    mesh_skull = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh_old),
        name="mesh_skull")

    skull_segment_pipe.connect(skull_bmask_cleaning, "gcc_nii_file",
                               mesh_skull, "nii_file")

    # skull_fov ####### [okey][json]

    skull_fov = NodeParams(interface=RobustFOV(),
                           params=parse_key(params, "skull_fov"),
                           name="skull_fov")

    skull_segment_pipe.connect(skull_bmask_cleaning, "gcc_nii_file",
                               skull_fov, "in_file")

    # mesh_robustskull #######
    mesh_robustskull = pe.Node(
        interface=niu.Function(input_names=["nii_file"],
                               output_names=["stl_file"],
                               function=wrap_nii2mesh_old),
        name="mesh_robustskull")

    skull_segment_pipe.connect(skull_fov, "out_roi",
                               mesh_robustskull, "nii_file")

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["skull_mask", "skull_stl",
                    "robustskull_mask", "robustskull_stl",
                    "head_mask"]),
        name='outputnode')

    skull_segment_pipe.connect(head_erode, "out_file",
                               outputnode, "head_mask")

    skull_segment_pipe.connect(mesh_skull, "stl_file",
                               outputnode, "skull_stl")

    skull_segment_pipe.connect(skull_fov, "out_roi",
                               outputnode, "robustskull_mask")

    skull_segment_pipe.connect(mesh_robustskull, "stl_file",
                               outputnode, "robustskull_stl")

    skull_segment_pipe.connect(skull_bmask_cleaning, "gcc_nii_file",
                               outputnode, "skull_mask")

    return skull_segment_pipe
