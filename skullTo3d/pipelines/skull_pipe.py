"""
    Gather all full pipelines

"""
import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe

from nipype.interfaces.fsl.maths import (
    DilateImage, ErodeImage,
    ApplyMask, Threshold,
    UnaryMaths, BinaryMaths, MathsCommand)

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

from skullTo3d.nodes.utils import empty_node

from skullTo3d.nodes.skull import mask_auto_img

from macapype.nodes.prepare import apply_li_thresh

from macapype.utils.misc import parse_key, get_elem


def _create_head_mask(name="headmask_pipe", params={}, prefix=""):

    # creating pipeline
    headmask_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['stereo_img',
                                      'indiv_params']),
        name='inputnode'
    )

    if prefix + "itkdebias" in params.keys():
        # Adding early debias
        itkdebias = pe.Node(
                interface=niu.Function(
                    input_names=["img_file"],
                    output_names=["cor_img_file",
                                  "bias_img_file",
                                  "mask_file"],
                    function=itk_debias),
                name=prefix + "itkdebias")

        headmask_pipe.connect(
            inputnode, "stereo_img",
            itkdebias, "img_file")

    # ### head mask
    # headmask_threshold
    if prefix + "head_mask_thr" in params.keys():
        # head_mask_thr
        head_mask_thr = NodeParams(
            interface=Threshold(),
            params=parse_key(params, 'head_mask_thr'),
            name=prefix + "head_mask_thr")

        if prefix + "itkdebias" in params.keys():

            headmask_pipe.connect(
                itkdebias, "cor_img_file",
                head_mask_thr, "in_file")
        else:

            headmask_pipe.connect(
                inputnode, "stereo_img",
                head_mask_thr, "in_file")

        headmask_pipe.connect(
            inputnode, ('indiv_params', parse_key, prefix + "head_mask_thr"),
            head_mask_thr, "indiv_params")

    elif prefix + "head_auto_mask" in params:

        head_auto_mask = NodeParams(
                interface=niu.Function(
                    input_names=["img_file", "operation",
                                 "index", "sample_bins", "distance", "kmeans"],
                    output_names=["mask_img_file"],
                    function=mask_auto_img),
                params=parse_key(params, prefix + "head_auto_mask"),
                name=prefix + "head_auto_mask")

        if prefix + "itkdebias" in params.keys():

            headmask_pipe.connect(
                itkdebias, "cor_img_file",
                head_auto_mask, "img_file")
        else:

            headmask_pipe.connect(
                inputnode, "stereo_img",
                head_auto_mask, "img_file")

        headmask_pipe.connect(
            inputnode, ('indiv_params', parse_key, prefix + "head_auto_mask"),
            head_auto_mask, "indiv_params")

    else:

        head_li_mask = pe.Node(
                interface=niu.Function(
                    input_names=["orig_img_file"],
                    output_names=["lithr_img_file"],
                    function=apply_li_thresh),
                name=prefix + "head_li_mask")

        if prefix + "itkdebias" in params.keys():

            headmask_pipe.connect(
                itkdebias, "cor_img_file",
                head_li_mask, "orig_img_file")
        else:

            headmask_pipe.connect(
                inputnode, "stereo_img",
                head_li_mask, "orig_img_file")

    # head_mask_binary
    head_mask_binary = pe.Node(
        interface=UnaryMaths(),
        name=prefix + "head_mask_binary")

    head_mask_binary.inputs.operation = 'bin'
    head_mask_binary.inputs.output_type = 'NIFTI_GZ'

    if prefix + "head_mask_thr" in params.keys():
        headmask_pipe.connect(
            head_mask_thr, "out_file",
            head_mask_binary, "in_file")

    elif prefix + "head_auto_mask" in params.keys():
        headmask_pipe.connect(
            head_auto_mask, "mask_img_file",
            head_mask_binary, "in_file")

    else:
        headmask_pipe.connect(
            head_li_mask, "lithr_img_file",
            head_mask_binary, "in_file")

    if prefix + "head_gcc_erode" in params and \
            prefix + "head_gcc_dilate" in params:

        # #### gcc erode gcc and dilate back
        # head_gcc_erode
        head_gcc_erode = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, prefix + "head_gcc_erode"),
            name=prefix + "head_gcc_erode")

        headmask_pipe.connect(
            head_mask_binary, "out_file",
            head_gcc_erode, "in_file")

        headmask_pipe.connect(
                inputnode,
                ('indiv_params', parse_key, prefix + "head_gcc_erode"),
                head_gcc_erode, "indiv_params")

        # head_mask_binary_clean1
        head_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name=prefix + "head_gcc")

        headmask_pipe.connect(
            head_gcc_erode, "out_file",
            head_gcc, "nii_file")

        # head_gcc_dilate
        head_gcc_dilate = NodeParams(
            interface=DilateImage(),
            params=parse_key(params, prefix + "head_gcc_dilate"),
            name=prefix + "head_gcc_dilate")

        headmask_pipe.connect(
            head_gcc, "gcc_nii_file",
            head_gcc_dilate, "in_file")

        headmask_pipe.connect(
                inputnode, ('indiv_params',
                            parse_key, prefix + "head_gcc_dilate"),
                head_gcc_dilate, "indiv_params")
    else:

        # head_mask_binary_clean1
        head_gcc = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name=prefix + "head_gcc")

        headmask_pipe.connect(
            head_mask_binary, "out_file",
            head_gcc, "nii_file")

    # ### fill dilate fill and erode back
    # head_dilate
    head_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, prefix + "head_dilate"),
        name=prefix + "head_dilate")

    if prefix + "head_gcc_erode" in params and \
            prefix + "head_gcc_dilate" in params:

        headmask_pipe.connect(
            head_gcc_dilate, "out_file",
            head_dilate, "in_file")
    else:
        headmask_pipe.connect(
            head_gcc, "gcc_nii_file",
            head_dilate, "in_file")

    headmask_pipe.connect(
        inputnode, ('indiv_params', parse_key, prefix + "head_dilate"),
        head_dilate, "indiv_params")

    # head_fill
    head_fill = pe.Node(interface=UnaryMaths(),
                        name=prefix + "head_fill")

    head_fill.inputs.operation = 'fillh'

    headmask_pipe.connect(
        head_dilate, "out_file",
        head_fill, "in_file")

    # head_erode ####### [okey][json]
    head_erode = NodeParams(interface=ErodeImage(),
                            params=parse_key(params, prefix + "head_erode"),
                            name=prefix + "head_erode")

    headmask_pipe.connect(
        head_fill, "out_file",
        head_erode, "in_file")

    headmask_pipe.connect(
        inputnode, ('indiv_params', parse_key, prefix + "head_erode"),
        head_erode, "indiv_params")

    # mask_head
    # mesh_head #######
    mesh_head = pe.Node(
        interface=IsoSurface(),
        name=prefix + "mesh_head")

    headmask_pipe.connect(
        head_erode, "out_file",
        mesh_head, "nii_file")

    # ### Masking with head mask
    # hmasked ####### [okey]
    hmasked = pe.Node(interface=ApplyMask(),
                      name=prefix + "hmasked")

    if prefix + "itkdebias" in params.keys():
        headmask_pipe.connect(
            itkdebias, "cor_img_file",
            hmasked, "in_file")
    else:

        headmask_pipe.connect(
            inputnode, "stereo_img",
            hmasked, "in_file")

    headmask_pipe.connect(
        head_erode, "out_file",
        hmasked, "mask_file")

    return headmask_pipe


def _create_skull_mask(name="skullmask_pipe", params={}, prefix=""):

    # creating pipeline
    skullmask_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['headmasked_img',
                                      "headmask",
                                      'indiv_params']),
        name='inputnode'
    )

    if prefix + "denoise" in params.keys():

        # N4 intensity normalization over T1
        denoise = NodeParams(DenoiseImage(),
                             params=parse_key(params, prefix + "denoise"),
                             name='denoise')

        skullmask_pipe.connect(
            inputnode, "headmasked_img",
            denoise, "input_image")

        skullmask_pipe.connect(
            inputnode, "headmask",
            denoise, "mask_image")

        skullmask_pipe.connect(
            inputnode, ('indiv_params', parse_key, prefix + "denoise"),
            denoise, "indiv_params")

    if prefix + "fast" in params.keys():

        fast = NodeParams(interface=FAST(),
                          params=parse_key(params, prefix + "fast"),
                          name=prefix + "fast")

        if prefix + "denoise" in params.keys():
            skullmask_pipe.connect(
                denoise, "output_image",
                fast, "in_files")
        else:
            skullmask_pipe.connect(
                inputnode, "headmasked_img",
                fast, "in_files")

        # skull_mask_binary
        skull_mask_binary = pe.Node(
            interface=UnaryMaths(),
            name=prefix + "skull_mask_binary")

        skull_mask_binary.inputs.operation = 'bin'
        skull_mask_binary.inputs.output_type = 'NIFTI_GZ'

        skullmask_pipe.connect(
            fast, ("partial_volume_files", get_elem, 0),
            skull_mask_binary, "in_file")

    else:
        # skull_li_mask
        skull_li_mask = pe.Node(
                interface=niu.Function(
                    input_names=["orig_img_file"],
                    output_names=["lithr_img_file"],
                    function=apply_li_thresh),
                name=prefix + "skull_li_mask")

        if prefix + "denoise" in params.keys():
            skullmask_pipe.connect(
                denoise, "output_image",
                skull_li_mask, "orig_img_file")
        else:
            skullmask_pipe.connect(
                inputnode, "headmasked_img",
                skull_li_mask, "orig_img_file")

        # fslmaths mask -mul -1 -add 1 invmask
        skull_inv = pe.Node(
                interface=MathsCommand(),
                name=prefix + "skull_inv")

        skull_inv.inputs.args = " -mul -1 -add 1"

        skullmask_pipe.connect(
            skull_li_mask, "lithr_img_file",
            skull_inv, "in_file")

    # skull_auto_thresh
    if prefix + "head_erode_skin" in params.keys():

        head_erode_skin = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, prefix + "head_erode_skin"),
            name=prefix + "head_erode_skin")

        skullmask_pipe.connect(
            inputnode, "headmask",
            head_erode_skin, "in_file")

        skullmask_pipe.connect(
            inputnode, ("indiv_params", parse_key, prefix + "head_erode_skin"),
            head_erode_skin, "indiv_params")

    # ### Masking with head mask or skin_erode_head_mask
    # skin_masked ####### [okey]
    skin_masked = pe.Node(interface=ApplyMask(),
                          name=prefix + "skin_masked")

    if prefix + "head_erode_skin" in params.keys():
        skullmask_pipe.connect(
            head_erode_skin, "out_file",
            skin_masked, "mask_file")
    else:
        skullmask_pipe.connect(
            inputnode, "headmask",
            skin_masked, "mask_file")

    if prefix + "fast" in params.keys():
        skullmask_pipe.connect(
            skull_mask_binary, "out_file",
            skin_masked, "in_file")

    else:
        skullmask_pipe.connect(
            skull_inv, "out_file",
            skin_masked, "in_file")

    if prefix+"mesh_rawskull" in params:

        # mesh_awskull #######
        mesh_rawskull = pe.Node(
            IsoSurface(),
            name=prefix+"mesh_rawskull")

        skullmask_pipe.connect(
            skin_masked, "out_file",
            mesh_rawskull, "nii_file")

    if prefix + "skull_gcc_erode" in params and \
            prefix + "skull_gcc_dilate" in params:

        # skull_erode ####### [okey][json]
        skull_gcc_erode = NodeParams(
            interface=ErodeImage(),
            params=parse_key(params, prefix + "skull_gcc_erode"),
            name=prefix + "skull_gcc_erode")

        if prefix + "head_erode_skin" in params.keys():
            skullmask_pipe.connect(
                skin_masked, "out_file",
                skull_gcc_erode, "in_file")
        else:
            skullmask_pipe.connect(
                skull_mask_binary, "out_file",
                skull_gcc_erode, "in_file")

        skullmask_pipe.connect(
            inputnode, ('indiv_params', parse_key, prefix + "skull_gcc_erode"),
            skull_gcc_erode, "indiv_params")

        # skull_gcc ####### [okey]
        skull_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name=prefix + "skull_gcc")

        skullmask_pipe.connect(
            skull_gcc_erode, "out_file",
            skull_gcc, "nii_file")

        # skull_gcc_dilate ####### [okey][json]
        skull_gcc_dilate = NodeParams(
            interface=DilateImage(),
            params=parse_key(params, prefix + "skull_gcc_dilate"),
            name=prefix + "skull_gcc_dilate")

        skullmask_pipe.connect(
            skull_gcc, "gcc_nii_file",
            skull_gcc_dilate, "in_file")

        skullmask_pipe.connect(
            inputnode,
            ('indiv_params', parse_key, prefix + "skull_gcc_dilate"),
            skull_gcc_dilate, "indiv_params")

    else:

        # skull_gcc ####### [okey]
        skull_gcc = pe.Node(
            interface=niu.Function(
                input_names=["nii_file"],
                output_names=["gcc_nii_file"],
                function=keep_gcc),
            name=prefix + "skull_gcc")

        if prefix + "head_erode_skin" in params.keys():
            skullmask_pipe.connect(
                skin_masked, "out_file",
                skull_gcc, "nii_file")
        else:
            skullmask_pipe.connect(
                skull_mask_binary, "out_file",
                skull_gcc, "nii_file")

    # skull_dilate ####### [okey][json]
    skull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, prefix + "skull_dilate"),
        name=prefix + "skull_dilate")

    if prefix + "skull_gcc_erode" in params and \
            prefix + "skull_gcc_dilate" in params:

        skullmask_pipe.connect(
            skull_gcc_dilate, "out_file",
            skull_dilate, "in_file")
    else:
        skullmask_pipe.connect(
            skull_gcc, "gcc_nii_file",
            skull_dilate, "in_file")

    skullmask_pipe.connect(
        inputnode, ('indiv_params', parse_key, prefix + "skull_dilate"),
        skull_dilate, "indiv_params")

    # skull_fill #######  [okey]
    skull_fill = pe.Node(interface=UnaryMaths(),
                         name=prefix + "skull_fill")

    skull_fill.inputs.operation = 'fillh'

    skullmask_pipe.connect(
        skull_dilate, "out_file",
        skull_fill, "in_file")

    # skull_erode ####### [okey][json]
    skull_erode = NodeParams(
        interface=ErodeImage(),
        params=parse_key(params, prefix + "skull_erode"),
        name=prefix + "skull_erode")

    skullmask_pipe.connect(
        skull_fill, "out_file",
        skull_erode, "in_file")

    skullmask_pipe.connect(
        inputnode, ('indiv_params', parse_key, prefix + "skull_erode"),
        skull_erode, "indiv_params")

    # mesh_skull #######
    mesh_skull = pe.Node(
        interface=IsoSurface(),
        name=prefix + "mesh_skull")

    skullmask_pipe.connect(
        skull_erode, "out_file",
        mesh_skull, "nii_file")

    if prefix + "skull_fov" in params.keys():

        # skull_fov ####### [okey][json]
        skull_fov = NodeParams(
            interface=RobustFOV(),
            params=parse_key(params, prefix + "skull_fov"),
            name=prefix + "skull_fov")

        skullmask_pipe.connect(
            skull_erode, "out_file",
            skull_fov, "in_file")

        skullmask_pipe.connect(
            inputnode, ('indiv_params', parse_key, prefix + "skull_fov"),
            skull_fov, "indiv_params")

        # skull_clean ####### [okey]
        skull_clean = pe.Node(
            interface=niu.Function(input_names=["nii_file"],
                                   output_names=["gcc_nii_file"],
                                   function=keep_gcc),
            name=prefix + "skull_clean")

        skullmask_pipe.connect(
            skull_fov, "out_roi",
            skull_clean, "nii_file")

        # mesh_robustskull #######
        mesh_robustskull = pe.Node(
            interface=IsoSurface(),
            name=prefix + "mesh_robustskull")

        skullmask_pipe.connect(
            skull_clean, "gcc_nii_file",
            mesh_robustskull, "nii_file")

    return skullmask_pipe


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

    mesh_ct_skull.inputs.KPB = 0.0001
    mesh_ct_skull.inputs.NITER = 1000

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

        mesh_robustct_skull.inputs.KPB = 0.0001
        mesh_robustct_skull.inputs.NITER = 1000

        skullmask_ct_pipe.connect(
            ct_skull_clean, "gcc_nii_file",
            mesh_robustct_skull, "nii_file")

        return skullmask_ct_pipe


def _create_fullskull_mask(name="fullskull_pipe", params={}, prefix=""):

    print("Running fullskull_pipe with:", params)
    # Creating pipeline
    fullskull_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['segmented_brain_mask',
                                      "skullmask",
                                      "indiv_params"]),
        name='inputnode')

    # ct_skull_mask_binary
    brainmask_binary = pe.Node(
        interface=UnaryMaths(),
        name=prefix + "brainmask_binary")

    brainmask_binary.inputs.operation = 'bin'
    brainmask_binary.inputs.output_type = 'NIFTI_GZ'

    fullskull_pipe.connect(
            inputnode, "segmented_brain_mask",
            brainmask_binary, "in_file")

    # brainmask_expand

    # fullskull_dilate ####### [okey][json]
    brainmask_expand = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, prefix + "brainmask_expand"),
        name=prefix + "brainmask_expand")

    fullskull_pipe.connect(
        brainmask_binary, "out_file",
        brainmask_expand, "in_file")

    # add masks
    fullskull_mask_add = pe.Node(
        interface=BinaryMaths(),
        name=prefix + "fullskull_mask_add")

    fullskull_mask_add.inputs.operation = 'add'

    fullskull_pipe.connect(
            inputnode, "skullmask",
            fullskull_mask_add, "in_file")

    fullskull_pipe.connect(
            brainmask_binary, "out_file",
            fullskull_mask_add, "operand_file")

    # fullskull_dilate ####### [okey][json]
    fullskull_dilate = NodeParams(
        interface=DilateImage(),
        params=parse_key(params, prefix + "fullskull_dilate"),
        name=prefix + "fullskull_dilate")

    fullskull_pipe.connect(
        fullskull_mask_add, "out_file",
        fullskull_dilate, "in_file")

    # fullskull_fill #######  [okey]
    fullskull_fill = pe.Node(
        interface=UnaryMaths(),
        name=prefix + "fullskull_fill")

    fullskull_fill.inputs.operation = 'fillh'

    fullskull_pipe.connect(
        fullskull_dilate, "out_file",
        fullskull_fill, "in_file")

    # fullskull_erode ####### [okey][json]
    fullskull_erode = NodeParams(
        interface=ErodeImage(),
        params=parse_key(params, prefix + "fullskull_erode"),
        name=prefix + "fullskull_erode")

    fullskull_pipe.connect(
        fullskull_fill, "out_file",
        fullskull_erode, "in_file")

    # mesh_fullskull #######
    mesh_fullskull = pe.Node(
        interface=IsoSurface(),
        name=prefix + "mesh_fullskull")

    mesh_fullskull.inputs.KPB = 0.0001
    mesh_fullskull.inputs.NITER = 1000

    fullskull_pipe.connect(
        fullskull_erode, "out_file",
        mesh_fullskull, "nii_file")

    # fullskull_crop
    fullskull_crop = NodeParams(
            interface=ApplyMask(),
            params=parse_key(params, prefix + "fullskull_crop"),
            name=prefix + "fullskull_crop")

    fullskull_pipe.connect(
        fullskull_erode, "out_file",
        fullskull_crop, "in_file")

    fullskull_pipe.connect(
        brainmask_expand, "out_file",
        fullskull_crop, "mask_file")

    # mesh_fullskull_crop #######
    mesh_fullskull_crop = pe.Node(
        interface=IsoSurface(),
        name=prefix + "mesh_fullskull_crop")

    mesh_fullskull_crop.inputs.KPB = 0.0001
    mesh_fullskull_crop.inputs.NITER = 1000

    fullskull_pipe.connect(
        fullskull_crop, "out_file",
        mesh_fullskull_crop, "nii_file")

    return fullskull_pipe

##############################################################################
# ####################################  T1  ##################################
##############################################################################


def create_skull_t1_pipe(name="skull_t1_pipe", params={}):

    skull_t1_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['indiv_params', 'stereo_T1',
                                      "segmented_brain_mask"]),
        name='inputnode')

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["t1_skull_mask", "t1_skull_stl",
                    "t1_rawskull_mask", "t1_rawskull_stl",
                    "robustt1_skull_mask", "robustt1_skull_stl",
                    "t1_head_mask", "t1_head_stl",

                    "t1_fullskull_stl",
                    "t1_fullskull_mask",
                    "t1_fullskull_crop_stl",
                    "t1_fullskull_crop_mask"]),

        name='outputnode')

    # Creating headmask_t1_pipe
    if "headmask_t1_pipe" in params:
        headmask_t1_pipe = _create_head_mask(
            name="headmask_t1_pipe",
            params=params["headmask_t1_pipe"],
            prefix="t1_")

        skull_t1_pipe.connect(inputnode, "stereo_T1",
                              headmask_t1_pipe, "inputnode.stereo_img")

        skull_t1_pipe.connect(inputnode, "indiv_params",
                              headmask_t1_pipe, "inputnode.indiv_params")
    else:
        empty = pe.Node(
                interface=niu.Function(
                    input_names=["in_file"],
                    output_names=["out_file"],
                    function=empty_node),
                name="empty")

        skull_t1_pipe.connect(inputnode, "stereo_T1",
                              empty, "in_file")

        return skull_t1_pipe

    skull_t1_pipe.connect(
        headmask_t1_pipe, "t1_head_erode.out_file",
        outputnode, "t1_head_mask")

    skull_t1_pipe.connect(
        headmask_t1_pipe, "t1_mesh_head.stl_file",
        outputnode, "t1_head_stl")

    # Creating skullmask_t1_pipe
    if "skullmask_t1_pipe" in params:
        skullmask_t1_pipe = _create_skull_mask(
            name="skullmask_t1_pipe",
            params=params["skullmask_t1_pipe"],
            prefix="t1_")

        skull_t1_pipe.connect(headmask_t1_pipe, "t1_hmasked.out_file",
                              skullmask_t1_pipe, "inputnode.headmasked_img")

        skull_t1_pipe.connect(headmask_t1_pipe, "t1_head_erode.out_file",
                              skullmask_t1_pipe, "inputnode.headmask")

        skull_t1_pipe.connect(inputnode, "indiv_params",
                              skullmask_t1_pipe, "inputnode.indiv_params")
    else:
        return skull_t1_pipe

    # outputnode
    skull_t1_pipe.connect(
        skullmask_t1_pipe, "t1_mesh_skull.stl_file",
        outputnode, "t1_skull_stl")

    skull_t1_pipe.connect(
        skullmask_t1_pipe, "t1_skull_erode.out_file",
        outputnode, "t1_skull_mask")

    # rawskull t1
    if "t1_mesh_rawskull" in params["skullmask_t1_pipe"].keys():
        skull_t1_pipe.connect(
            skullmask_t1_pipe, "t1_mesh_rawskull.stl_file",
            outputnode, "t1_rawskull_stl")

    if "t1_head_erode_skin" in params["skullmask_t1_pipe"].keys():
        skull_t1_pipe.connect(
            skullmask_t1_pipe, "t1_skin_masked.out_file",
            outputnode, "t1_rawskull_mask")

    else:
        if "t1_fast" in params["skullmask_t1_pipe"].keys():

            skull_t1_pipe.connect(
                skullmask_t1_pipe, "t1_skull_mask_binary.out_file",
                outputnode, "t1_rawskull_mask")
        else:

            skull_t1_pipe.connect(
                skullmask_t1_pipe, "t1_skull_inv.out_file",
                outputnode, "t1_rawskull_mask")

    if "t1_skull_fov" in params["skullmask_t1_pipe"].keys():

        skull_t1_pipe.connect(
            skullmask_t1_pipe, "t1_skull_fov.out_roi",
            outputnode, "robustt1_skull_mask")

        skull_t1_pipe.connect(
            skullmask_t1_pipe, "t1_mesh_robustskull.stl_file",
            outputnode, "robustt1_skull_stl")

    # ## skull mask
    if "fullskullmask_t1_pipe" in params:

        fullskullmask_pipe = _create_fullskull_mask(
            name="fullskullmask_t1_pipe",
            params=params["fullskullmask_t1_pipe"],
            prefix="t1_")

        skull_t1_pipe.connect(
            skullmask_t1_pipe, "t1_skull_erode.out_file",
            fullskullmask_pipe, "inputnode.skullmask")

        skull_t1_pipe.connect(
            inputnode, "segmented_brain_mask",
            fullskullmask_pipe, "inputnode.segmented_brain_mask")

        skull_t1_pipe.connect(
            inputnode, "indiv_params",
            fullskullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_t1_pipe

    # outputnode
    skull_t1_pipe.connect(
        fullskullmask_pipe, "t1_fullskull_erode.out_file",
        outputnode, "t1_fullskull_mask")

    skull_t1_pipe.connect(
        fullskullmask_pipe, "t1_mesh_fullskull.stl_file",
        outputnode, "t1_fullskull_stl")

    skull_t1_pipe.connect(
        fullskullmask_pipe, "t1_fullskull_crop.out_file",
        outputnode, "t1_fullskull_crop_mask")

    skull_t1_pipe.connect(
        fullskullmask_pipe, "t1_mesh_fullskull_crop.stl_file",
        outputnode, "t1_fullskull_crop_stl")

    return skull_t1_pipe


###############################################################################
# #################################  PETRA  ###################################
###############################################################################

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

        headmask_pipe = _create_head_mask(
            name="headmask_petra_pipe",
            params=params["headmask_petra_pipe"], prefix="petra_")

        # TODO
        if "crop_petra" in params:
            skull_petra_pipe.connect(
                crop_petra, "out_file",
                headmask_pipe, "inputnode.stereo_img")
        elif "avg_reorient_pipe" in params.keys():
            skull_petra_pipe.connect(
                av_PETRA, 'outputnode.std_img',
                headmask_pipe, "inputnode.stereo_img")
        else:
            skull_petra_pipe.connect(
                av_PETRA, 'avg_img',
                headmask_pipe, "inputnode.stereo_img")

        skull_petra_pipe.connect(inputnode, "indiv_params",
                                 headmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(headmask_pipe, "petra_head_erode.out_file",
                             outputnode, "petra_head_mask")

    skull_petra_pipe.connect(headmask_pipe, "petra_mesh_head.stl_file",
                             outputnode, "petra_head_stl")

    # ## skull mask
    if "skullmask_petra_pipe" in params:

        skullmask_pipe = _create_skull_mask(
            name="skullmask_petra_pipe",
            params=params["skullmask_petra_pipe"], prefix="petra_")

        skull_petra_pipe.connect(
            headmask_pipe, "petra_hmasked.out_file",
            skullmask_pipe, "inputnode.headmasked_img")

        skull_petra_pipe.connect(
            headmask_pipe, "petra_head_erode.out_file",
            skullmask_pipe, "inputnode.headmask")

        skull_petra_pipe.connect(
            inputnode, "indiv_params",
            skullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(skullmask_pipe, "petra_mesh_skull.stl_file",
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
                                      "segmented_brain_mask",
                                      'native_to_stereo_trans',
                                      'indiv_params']),
        name='inputnode'
    )

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["petra_skull_mask", "petra_skull_stl", "stereo_petra",
                    "robustpetra_skull_mask", "robustpetra_skull_stl",
                    "petra_head_mask", "petra_head_stl",
                    "petra_fullskull_stl",
                    "petra_fullskull_mask",
                    "petra_fullskull_crop_stl",
                    "petra_fullskull_crop_mask"]),
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

        headmask_pipe = _create_head_mask(
            name="headmask_petra_pipe",
            params=params["headmask_petra_pipe"], prefix="petra_")
        # TODO
        skull_petra_pipe.connect(
            align_petra_on_stereo, "out_file",
            headmask_pipe, "inputnode.stereo_img")

        skull_petra_pipe.connect(
            inputnode, "indiv_params",
            headmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(headmask_pipe, "petra_head_erode.out_file",
                             outputnode, "petra_head_mask")

    skull_petra_pipe.connect(headmask_pipe, "petra_mesh_head.stl_file",
                             outputnode, "petra_head_stl")

    # ## skull mask
    if "skullmask_petra_pipe" in params:

        skullmask_pipe = _create_skull_mask(
            name="skullmask_petra_pipe",
            params=params["skullmask_petra_pipe"], prefix="petra_")

        skull_petra_pipe.connect(
            headmask_pipe, "petra_hmasked.out_file",
            skullmask_pipe, "inputnode.headmasked_img")

        skull_petra_pipe.connect(
            headmask_pipe, "petra_head_erode.out_file",
            skullmask_pipe, "inputnode.headmask")

        skull_petra_pipe.connect(
            inputnode, "indiv_params",
            skullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    skull_petra_pipe.connect(skullmask_pipe, "petra_mesh_skull.stl_file",
                             outputnode, "petra_skull_stl")

    skull_petra_pipe.connect(skullmask_pipe, "petra_skull_erode.out_file",
                             outputnode, "petra_skull_mask")

    if "petra_skull_fov" in params["skullmask_petra_pipe"].keys():

        skull_petra_pipe.connect(
            skullmask_pipe, "petra_skull_fov.out_roi",
            outputnode, "robustpetra_skull_mask")

        skull_petra_pipe.connect(
            skullmask_pipe, "petra_mesh_robustskull.stl_file",
            outputnode, "robustpetra_skull_stl")

    # ## skull mask
    if "fullskullmask_petra_pipe" in params:

        fullskullmask_pipe = _create_fullskull_mask(
            name="fullskullmask_petra_pipe",
            params=params["fullskullmask_petra_pipe"],
            prefix="petra_")

        skull_petra_pipe.connect(
            skullmask_pipe, "petra_skull_erode.out_file",
            fullskullmask_pipe, "inputnode.skullmask")

        skull_petra_pipe.connect(
            inputnode, "segmented_brain_mask",
            fullskullmask_pipe, "inputnode.segmented_brain_mask")

        skull_petra_pipe.connect(
            inputnode, "indiv_params",
            fullskullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_petra_pipe

    # outputnode
    skull_petra_pipe.connect(fullskullmask_pipe,
                             "petra_fullskull_erode.out_file",
                             outputnode, "petra_fullskull_mask")

    skull_petra_pipe.connect(fullskullmask_pipe,
                             "petra_mesh_fullskull.stl_file",
                             outputnode, "petra_fullskull_stl")

    skull_petra_pipe.connect(fullskullmask_pipe,
                             "petra_fullskull_crop.out_file",
                             outputnode, "petra_fullskull_crop_mask")

    skull_petra_pipe.connect(fullskullmask_pipe,
                             "petra_mesh_fullskull_crop.stl_file",
                             outputnode, "petra_fullskull_crop_stl")

    return skull_petra_pipe


##############################################################################
# #################################  MEGRE  ##################################
##############################################################################

def create_skull_megre_pipe(name="skull_megre_pipe", params={}):

    # Creating pipeline
    skull_megre_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=[
            'list_megre', 'stereo_T1', 'native_T1',
            'segmented_brain_mask',
            'native_to_stereo_trans', 'indiv_params']),
        name='inputnode'
    )

    # creating outputnode #######
    outputnode = pe.Node(
        niu.IdentityInterface(
            fields=["stereo_megre",
                    "megre_head_mask",
                    "megre_head_stl",
                    "megre_skull_stl",
                    "megre_skull_mask",
                    "megre_fullskull_stl",
                    "megre_fullskull_mask",
                    "megre_fullskull_crop_stl",
                    "megre_fullskull_crop_mask",
                    "robustmegre_skull_mask",
                    "robustmegre_skull_stl"]),
        name='outputnode')

    print("Using average_align for av_MEGRE")
    print(params)

    av_MEGRE = pe.Node(
        niu.Function(input_names=['list_img', "reorient", "max_index"],
                     output_names=['avg_img'],
                     function=average_align),
        name="av_MEGRE")

    av_MEGRE.inputs.max_index = 3

    skull_megre_pipe.connect(
        inputnode, 'list_megre',
        av_MEGRE, "list_img")

    # align_megre_on_T1
    align_megre_on_T1 = pe.Node(
        interface=RegAladin(),
        name="align_megre_on_T1")

    align_megre_on_T1.inputs.rig_only_flag = True

    skull_megre_pipe.connect(
        av_MEGRE, 'avg_img',
        align_megre_on_T1, "flo_file")

    skull_megre_pipe.connect(
        inputnode, "native_T1",
        align_megre_on_T1, "ref_file")

    if "align_megre_on_T1_2" in params:

        # align_megre_on_T1_2
        align_megre_on_T1_2 = pe.Node(
            interface=RegAladin(),
            name="align_megre_on_T1_2")

        align_megre_on_T1_2.inputs.rig_only_flag = True

        skull_megre_pipe.connect(
            align_megre_on_T1, 'res_file',
            align_megre_on_T1_2, "flo_file")

        skull_megre_pipe.connect(
            inputnode, "native_T1",
            align_megre_on_T1_2, "ref_file")

    # align_megre_on_stereo_T1
    align_megre_on_stereo_T1 = pe.Node(
        interface=RegResample(pad_val=0.0),
        name="align_megre_on_stereo_T1")

    if "align_megre_on_T1_2" in params:
        skull_megre_pipe.connect(
            align_megre_on_T1_2, 'res_file',
            align_megre_on_stereo_T1, "flo_file")

    else:
        skull_megre_pipe.connect(
            align_megre_on_T1, 'res_file',
            align_megre_on_stereo_T1, "flo_file")

    skull_megre_pipe.connect(
        inputnode, 'native_to_stereo_trans',
        align_megre_on_stereo_T1, "trans_file")

    skull_megre_pipe.connect(
        inputnode, "stereo_T1",
        align_megre_on_stereo_T1, "ref_file")
    # output node
    skull_megre_pipe.connect(
        align_megre_on_stereo_T1, "out_file",
        outputnode, "stereo_megre")

    # ## headmask
    if "headmask_megre_pipe" in params:

        headmask_pipe = _create_head_mask(
            name="headmask_megre_pipe",
            params=params["headmask_megre_pipe"],
            prefix="megre_")

        skull_megre_pipe.connect(
            align_megre_on_stereo_T1,  "out_file",
            headmask_pipe, "inputnode.stereo_img")

        skull_megre_pipe.connect(inputnode, "indiv_params",
                                 headmask_pipe, "inputnode.indiv_params")

    else:
        return skull_megre_pipe

    skull_megre_pipe.connect(headmask_pipe, "megre_head_erode.out_file",
                             outputnode, "megre_head_mask")

    skull_megre_pipe.connect(headmask_pipe, "megre_mesh_head.stl_file",
                             outputnode, "megre_head_stl")

    # ## skull mask
    if "skullmask_megre_pipe" in params:

        skullmask_pipe = _create_skull_mask(
            name="skullmask_megre_pipe",
            params=params["skullmask_megre_pipe"],
            prefix="megre_")

        skull_megre_pipe.connect(
            headmask_pipe, "megre_hmasked.out_file",
            skullmask_pipe, "inputnode.headmasked_img")

        skull_megre_pipe.connect(
            headmask_pipe, "megre_head_erode.out_file",
            skullmask_pipe, "inputnode.headmask")

        skull_megre_pipe.connect(
            inputnode, "indiv_params",
            skullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_megre_pipe

    skull_megre_pipe.connect(skullmask_pipe, "megre_skull_erode.out_file",
                             outputnode, "megre_skull_mask")

    skull_megre_pipe.connect(skullmask_pipe, "megre_mesh_skull.stl_file",
                             outputnode, "megre_skull_stl")

    if "megre_skull_fov" in params["skullmask_megre_pipe"].keys():

        skull_megre_pipe.connect(
            skullmask_pipe, "megre_skull_fov.out_roi",
            outputnode, "robustmegre_skull_mask")

        skull_megre_pipe.connect(
            skullmask_pipe, "megre_mesh_robustskull.stl_file",
            outputnode, "robustmegre_skull_stl")

    # ## skull mask
    if "fullskullmask_megre_pipe" in params:

        fullskullmask_pipe = _create_fullskull_mask(
            name="fullskullmask_megre_pipe",
            params=params["fullskullmask_megre_pipe"], prefix="megre_")

        skull_megre_pipe.connect(
            skullmask_pipe, "megre_skull_erode.out_file",
            fullskullmask_pipe, "inputnode.skullmask")

        skull_megre_pipe.connect(
            inputnode, "segmented_brain_mask",
            fullskullmask_pipe, "inputnode.segmented_brain_mask")

        skull_megre_pipe.connect(
            inputnode, "indiv_params",
            fullskullmask_pipe, "inputnode.indiv_params")

    else:
        return skull_megre_pipe

    # outputnode
    skull_megre_pipe.connect(fullskullmask_pipe,
                             "megre_fullskull_erode.out_file",
                             outputnode, "megre_fullskull_mask")

    skull_megre_pipe.connect(fullskullmask_pipe,
                             "megre_mesh_fullskull.stl_file",
                             outputnode, "megre_fullskull_stl")

    skull_megre_pipe.connect(fullskullmask_pipe,
                             "megre_fullskull_crop.out_file",
                             outputnode, "megre_fullskull_crop_mask")

    skull_megre_pipe.connect(fullskullmask_pipe,
                             "megre_mesh_fullskull_crop.stl_file",
                             outputnode, "megre_fullskull_crop_stl")

    return skull_megre_pipe

##############################################################################
# ####################################  CT  ##################################
##############################################################################


def create_skull_ct_pipe(name="skull_ct_pipe", params={}):

    # Creating pipeline
    skull_ct_pipe = pe.Workflow(name=name)

    # Creating input node
    inputnode = pe.Node(
        niu.IdentityInterface(fields=['ct', 'stereo_T1', 'native_T1',
                                      'native_to_stereo_trans',
                                      'indiv_params']),
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

        if "aladin_CT_on_T1" in params:

            # align_ct_on_T1
            aladin_CT_on_T1 = pe.Node(
                interface=RegAladin(),
                name="aladin_CT_on_T1")

            aladin_CT_on_T1.inputs.rig_only_flag = True

            skull_ct_pipe.connect(
                crop_CT, "roi_file",
                aladin_CT_on_T1, "flo_file")

            skull_ct_pipe.connect(
                inputnode, "stereo_T1",
                aladin_CT_on_T1, "ref_file")

            # aladin_CT_on_T1_2
            aladin_CT_on_T1_2 = pe.Node(
                interface=RegAladin(),
                name="aladin_CT_on_T1_2")

            aladin_CT_on_T1_2.inputs.rig_only_flag = True

            skull_ct_pipe.connect(
                aladin_CT_on_T1, "res_file",
                aladin_CT_on_T1_2, "flo_file")

            skull_ct_pipe.connect(
                inputnode, "stereo_T1",
                aladin_CT_on_T1_2, "ref_file")

            # aladin_CT_on_T1_3
            aladin_CT_on_T1_3 = pe.Node(
                interface=RegAladin(),
                name="aladin_CT_on_T1_3")

            aladin_CT_on_T1_3.inputs.rig_only_flag = True

            skull_ct_pipe.connect(
                aladin_CT_on_T1_2, "res_file",
                aladin_CT_on_T1_3, "flo_file")

            skull_ct_pipe.connect(
                inputnode, "stereo_T1",
                aladin_CT_on_T1_3, "ref_file")

        else:

            align_ct_on_T1 = pe.Node(fsl.FLIRT(), name="align_ct_on_T1")
            align_ct_on_T1.inputs.dof = 6

            align_ct_on_T1.inputs.cost = 'normmi'

            skull_ct_pipe.connect(
                crop_CT, "roi_file",
                align_ct_on_T1, 'in_file')

            skull_ct_pipe.connect(
                inputnode, "stereo_T1",
                align_ct_on_T1, 'reference')

            if "align_ct_on_T1_2" in params:

                align_ct_on_T1_2 = pe.Node(fsl.FLIRT(),
                                           name="align_ct_on_T1_2")
                align_ct_on_T1_2.inputs.dof = 6

                align_ct_on_T1_2.inputs.cost = 'normmi'

                skull_ct_pipe.connect(
                    crop_CT, "roi_file",
                    align_ct_on_T1_2, 'in_file')

                skull_ct_pipe.connect(
                    inputnode, "stereo_T1",
                    align_ct_on_T1_2, 'reference')

                # initial matrix
                skull_ct_pipe.connect(
                    align_ct_on_T1, "out_matrix_file",
                    align_ct_on_T1_2, 'in_matrix_file')

        if "aladin_CT_on_T1" in params:
            skull_ct_pipe.connect(
                aladin_CT_on_T1_3, 'res_file',
                outputnode, "stereo_ct")
        else:

            if "align_ct_on_T1_2" in params:
                skull_ct_pipe.connect(
                    align_ct_on_T1_2, 'out_file',
                    outputnode, "stereo_ct")

            else:
                skull_ct_pipe.connect(
                    align_ct_on_T1, 'out_file',
                    outputnode, "stereo_ct")

    else:

        # align_ct_on_T1
        align_ct_on_T1 = pe.Node(
            interface=RegAladin(),
            name="align_ct_on_T1")

        align_ct_on_T1.inputs.rig_only_flag = True

        skull_ct_pipe.connect(
            inputnode, 'ct',
            align_ct_on_T1, "flo_file")

        skull_ct_pipe.connect(
            inputnode, "native_T1",
            align_ct_on_T1, "ref_file")

        if "align_ct_on_T1_2" in params:

            # align_ct_on_T1
            align_ct_on_T1_2 = pe.Node(
                interface=RegAladin(),
                name="align_ct_on_T1_2")

            align_ct_on_T1_2.inputs.rig_only_flag = True

            skull_ct_pipe.connect(
                align_ct_on_T1, 'res_file',
                align_ct_on_T1_2, "flo_file")

            skull_ct_pipe.connect(
                inputnode, "native_T1",
                align_ct_on_T1_2, "ref_file")

        # align_ct_on_stereo_T1
        align_ct_on_stereo_T1 = pe.Node(
            interface=RegResample(pad_val=0.0),
            name="align_ct_on_stereo_T1")

        if "align_ct_on_T1_2" in params:
            skull_ct_pipe.connect(
                align_ct_on_T1_2, 'res_file',
                align_ct_on_stereo_T1, "flo_file")

        else:
            skull_ct_pipe.connect(
                align_ct_on_T1, 'res_file',
                align_ct_on_stereo_T1, "flo_file")

        skull_ct_pipe.connect(
            inputnode, 'native_to_stereo_trans',
            align_ct_on_stereo_T1, "trans_file")

        skull_ct_pipe.connect(
            inputnode, "stereo_T1",
            align_ct_on_stereo_T1, "ref_file")

        # output node
        skull_ct_pipe.connect(
            align_ct_on_stereo_T1, "out_file",
            outputnode, "stereo_ct")

    if "skullmask_ct_pipe" in params:

        skullmask_ct_pipe = _create_skullmask_ct_pipe(
            name="skullmask_ct_pipe",
            params=params["skullmask_ct_pipe"])

        if "crop_CT" in params:

            if "aladin_CT_on_T1" in params:

                skull_ct_pipe.connect(
                    aladin_CT_on_T1_3, 'res_file',
                    skullmask_ct_pipe, "inputnode.realigned_ct")
            else:
                if "align_ct_on_T1_2" in params:
                    skull_ct_pipe.connect(
                        align_ct_on_T1_2, 'out_file',
                        skullmask_ct_pipe, "inputnode.realigned_ct")

                else:
                    skull_ct_pipe.connect(
                        align_ct_on_T1, 'out_file',
                        skullmask_ct_pipe, "inputnode.realigned_ct")
        else:

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

    if "ct_skull_fov" in params["skullmask_ct_pipe"].keys():

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
