
def pad_zero_mri(img_file, pad_val=10):

    import os
    import nibabel as nib
    import numpy as np

    from nipype.utils.filemanip import split_filename as split_f

    img = nib.load(img_file)
    img_arr = np.array(img.dataobj)
    img_arr_copy = np.copy(img_arr)

    img_arr_copy_padded = np.pad(
        img_arr_copy,
        pad_width=[(pad_val, pad_val), (pad_val, pad_val), (pad_val, pad_val)],
        mode='constant',
        constant_values=[(0, 0), (0, 0), (0, 0)])

    img_padded = nib.Nifti1Image(img_arr_copy_padded,
                                 header=img.header,
                                 affine=img.affine)

    path, fname, ext = split_f(img_file)

    img_padded_file = os.path.abspath("padded_" + fname + ext)

    nib.save(img_padded, img_padded_file)

    return img_padded_file


def keep_gcc(nii_file):

    import os
    import nibabel as nib
    import numpy as np

    from nipype.utils.filemanip import split_filename as split_f

    def getLargestCC(segmentation):

        from skimage.measure import label

        labels = label(segmentation)
        assert labels.max() != 0  # assume at least 1 CC
        largestCC = labels == np.argmax(np.bincount(labels.flat)[1:])+1
        return largestCC

    # nibabel (nifti -> np.array)
    img = nib.load(nii_file)
    data = img.get_fdata().astype("int32")
    print(data.shape)

    # numpy
    data[data > 0] = 1
    binary = np.array(data, dtype="bool")

    # skimage

    # skimage GCC
    new_data = getLargestCC(binary)

    # nibabel (np.array -> nifti)
    new_img = nib.Nifti1Image(dataobj=new_data,
                              header=img.header,
                              affine=img.affine)

    path, fname, ext = split_f(nii_file)

    gcc_nii_file = os.path.abspath("GCC_" + fname + ext)

    nib.save(new_img, gcc_nii_file)
    return gcc_nii_file



def wrap_nii2mesh_old(nii_file):

    import os
    from nipype.utils.filemanip import split_filename as split_f

    path, fname, ext = split_f(nii_file)

    stl_file = os.path.abspath(fname + ".stl")

    cmd = "nii2mesh_old_gcc {} {}".format(nii_file, stl_file)

    ret = os.system(cmd)

    print(ret)

    assert ret == 0, "Error, cmd {} did not work".format(cmd)
    return stl_file

def wrap_nii2mesh(nii_file):

    import os
    from nipype.utils.filemanip import split_filename as split_f

    path, fname, ext = split_f(nii_file)

    stl_file = os.path.abspath(fname + ".stl")

    cmd = "nii2mesh {} {}".format(nii_file, stl_file)

    ret = os.system(cmd)

    print(ret)

    assert ret == 0, "Error, cmd {} did not work".format(cmd)
    return stl_file

