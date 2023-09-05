﻿"""
    Gather all full pipelines

"""
import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe


def rename_all_skull_derivatives(params, main_workflow, skull_petra_pipe,
                                 skull_ct_pipe, skull_t1_pipe, datasink,
                                 pref_deriv, parse_str, space, pad, ssoft):

    # Rename in skull_petra_pipe
    if "skull_petra_pipe" in params.keys() and "petra" in ssoft:

        # rename petra_skull_stl
        rename_petra_skull_stl = pe.Node(niu.Rename(),
                                         name="rename_petra_skull_stl")
        rename_petra_skull_stl.inputs.format_string = \
            pref_deriv + "_space-stereo_desc-petra_skullmask"
        rename_petra_skull_stl.inputs.parse_string = parse_str
        rename_petra_skull_stl.inputs.keep_ext = True

        main_workflow.connect(
            skull_petra_pipe, 'outputnode.petra_skull_stl',
            rename_petra_skull_stl, 'in_file')

        main_workflow.connect(
            rename_petra_skull_stl, 'out_file',
            datasink, '@petra_skull_stl')

        # rename robustpetra_skull_stl
        rename_robustpetra_skull_stl = pe.Node(
            niu.Rename(), name="rename_robustpetra_skull_stl")

        rename_robustpetra_skull_stl.inputs.format_string = \
            pref_deriv + "_space-stereo_desc-robustpetra_skullmask"
        rename_robustpetra_skull_stl.inputs.parse_string = parse_str
        rename_robustpetra_skull_stl.inputs.keep_ext = True

        main_workflow.connect(
            skull_petra_pipe, 'outputnode.robustpetra_skull_stl',
            rename_robustpetra_skull_stl, 'in_file')

        main_workflow.connect(
            rename_robustpetra_skull_stl, 'out_file',
            datasink, '@robustpetra_skull_stl')

        # rename stereo_petra_skull_mask
        rename_stereo_petra_skull_mask = pe.Node(
            niu.Rename(), name="rename_stereo_petra_skull_mask")

        rename_stereo_petra_skull_mask.inputs.format_string =\
            pref_deriv + "_space-stereo_desc-petra_skullmask"
        rename_stereo_petra_skull_mask.inputs.parse_string = parse_str
        rename_stereo_petra_skull_mask.inputs.keep_ext = True

        main_workflow.connect(
            skull_petra_pipe, 'outputnode.petra_skull_mask',
            rename_stereo_petra_skull_mask, 'in_file')

        main_workflow.connect(
            rename_stereo_petra_skull_mask, 'out_file',
            datasink, '@stereo_petra_skull_mask')

        # rename stereo_robustpetra_skull_mask
        rename_stereo_robustpetra_skull_mask = pe.Node(
            niu.Rename(), name="rename_stereo_robustpetra_skullmask")

        rename_stereo_robustpetra_skull_mask.inputs.format_string = \
            pref_deriv + "_space-stereo_desc-robustpetra_skullmask"

        rename_stereo_robustpetra_skull_mask.inputs.parse_string = \
            parse_str

        rename_stereo_robustpetra_skull_mask.inputs.keep_ext = True

        main_workflow.connect(
            skull_petra_pipe, 'outputnode.robustpetra_skull_mask',
            rename_stereo_robustpetra_skull_mask, 'in_file')

        main_workflow.connect(
            rename_stereo_robustpetra_skull_mask, 'out_file',
            datasink, '@stereo_robustpetra_skullmask')

        # rename stereo_petra_head_mask
        rename_stereo_petra_head_mask = pe.Node(
            niu.Rename(), name="rename_stereo_petra_head_mask")

        rename_stereo_petra_head_mask.inputs.format_string =\
            pref_deriv + "_space-stereo_desc-petra_headmask"
        rename_stereo_petra_head_mask.inputs.parse_string = parse_str
        rename_stereo_petra_head_mask.inputs.keep_ext = True

        main_workflow.connect(
            skull_petra_pipe, 'outputnode.petra_head_mask',
            rename_stereo_petra_head_mask, 'in_file')

        main_workflow.connect(
            rename_stereo_petra_head_mask, 'out_file',
            datasink, '@stereo_petra_head_mask')

        if pad and space == "native":

            # rename petra_skull_mask
            rename_petra_skull_mask = pe.Node(niu.Rename(),
                                              name="rename_petra_skull_mask")
            rename_petra_skull_mask.inputs.format_string = \
                pref_deriv + "_space-{}_desc-petra_skullmask".format(space)
            rename_petra_skull_mask.inputs.parse_string = parse_str
            rename_petra_skull_mask.inputs.keep_ext = True

            main_workflow.connect(
                pad_petra_skull_mask, "out_file",
                rename_petra_skull_mask, 'in_file')

            main_workflow.connect(
                rename_petra_skull_mask, 'out_file',
                datasink, '@petra_skull_mask')

            # rename robustpetra_skull_mask
            rename_robustpetra_skull_mask = pe.Node(
                niu.Rename(), name="rename_robustpetra_skull_mask")
            rename_robustpetra_skull_mask.inputs.format_string = \
                pref_deriv + "_space-{}_desc-robustpetra_skullmask".format(
                    space)
            rename_robustpetra_skull_mask.inputs.parse_string = parse_str
            rename_robustpetra_skull_mask.inputs.keep_ext = True

            main_workflow.connect(
                pad_robustpetra_skull_mask, "out_file",
                rename_robustpetra_skull_mask, 'in_file')

            main_workflow.connect(
                rename_robustpetra_skull_mask, 'out_file',
                datasink, '@robustpetra_skull_mask')

            # rename petra_head_mask
            rename_petra_head_mask = pe.Node(
                niu.Rename(), name="rename_petra_head_mask")
            rename_petra_head_mask.inputs.format_string = \
                pref_deriv + "_space-{}_desc-petra_headmask".format(space)
            rename_petra_head_mask.inputs.parse_string = parse_str
            rename_petra_head_mask.inputs.keep_ext = True

            main_workflow.connect(
                pad_petra_head_mask, 'out_file',
                rename_petra_head_mask, 'in_file')

            main_workflow.connect(
                rename_petra_head_mask, 'out_file',
                datasink, '@petra_head_mask')

    # Rename in skull_ct_pipe
    if "skull_ct_pipe" in params.keys() and "ct" in ssoft:

        # rename ct_skull_mask
        rename_ct_skull_mask = pe.Node(niu.Rename(),
                                       name="rename_ct_skull_mask")
        rename_ct_skull_mask.inputs.format_string = \
            pref_deriv + "_space-stereo_desc-ct_skullmask"
        rename_ct_skull_mask.inputs.parse_string = parse_str
        rename_ct_skull_mask.inputs.keep_ext = True

        main_workflow.connect(
                skull_ct_pipe, "outputnode.stereo_ct_skull_mask",
                rename_ct_skull_mask, 'in_file')

        main_workflow.connect(
            rename_ct_skull_mask, 'out_file',
            datasink, '@ct_skull_mask')

        # rename ct_skull_stl
        rename_ct_skull_stl = pe.Node(niu.Rename(),
                                      name="rename_ct_skull_stl")
        rename_ct_skull_stl.inputs.format_string = \
            pref_deriv + "_space-stereo_desc-ct_skullmask"
        rename_ct_skull_stl.inputs.parse_string = parse_str
        rename_ct_skull_stl.inputs.keep_ext = True

        main_workflow.connect(
            skull_ct_pipe, 'outputnode.ct_skull_stl',
            rename_ct_skull_stl, 'in_file')

        main_workflow.connect(
            rename_ct_skull_stl, 'out_file',
            datasink, '@ct_skull_stl')

    # Rename in skull_t1_pipe
    if "skull_t1_pipe" in params.keys():

        # rename t1_skull_mask
        rename_t1_skull_mask = pe.Node(niu.Rename(),
                                       name="rename_t1_skull_mask")
        rename_t1_skull_mask.inputs.format_string = \
            pref_deriv + "_space-stereo_desc-t1_skullmask"
        rename_t1_skull_mask.inputs.parse_string = parse_str
        rename_t1_skull_mask.inputs.keep_ext = True

        main_workflow.connect(
                skull_t1_pipe, "outputnode.t1_skull_mask",
                rename_t1_skull_mask, 'in_file')

        main_workflow.connect(
            rename_t1_skull_mask, 'out_file',
            datasink, '@t1_skull_mask')

        # rename t1_skull_stl
        rename_t1_skull_stl = pe.Node(niu.Rename(),
                                      name="rename_t1_skull_stl")
        rename_t1_skull_stl.inputs.format_string = \
            pref_deriv + "_space-stereo_desc-t1_skullmask"
        rename_t1_skull_stl.inputs.parse_string = parse_str
        rename_t1_skull_stl.inputs.keep_ext = True

        main_workflow.connect(
            skull_t1_pipe, 'outputnode.t1_skull_stl',
            rename_t1_skull_stl, 'in_file')

        main_workflow.connect(
            rename_t1_skull_stl, 'out_file',
            datasink, '@t1_skull_stl')

        # rename t1_head_mask
        rename_t1_head_mask = pe.Node(niu.Rename(),
                                      name="rename_t1_head_mask")
        rename_t1_head_mask.inputs.format_string = \
            pref_deriv + "_space-{}_desc-t1_headmask".format(space)
        rename_t1_head_mask.inputs.parse_string = parse_str
        rename_t1_head_mask.inputs.keep_ext = True

        main_workflow.connect(
            skull_t1_pipe, 'outputnode.t1_head_mask',
            rename_t1_head_mask, 'in_file')

        main_workflow.connect(
            rename_t1_head_mask, 'out_file',
            datasink, '@t1_head_mask')
