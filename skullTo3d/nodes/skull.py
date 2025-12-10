def mask_auto_img(img_file, operation, index, sample_bins=30, num_clusters=3):

    import os
    import numpy as np
    import nibabel as nib
    import matplotlib.pyplot as plt

    from sklearn.cluster import KMeans

    from nipype.utils.filemanip import split_filename as split_f

    img_nii = nib.load(img_file)
    img_arr = np.array(img_nii.dataobj)

    print("nb nan: ", np.sum(np.isnan(img_arr)))
    img_arr[np.isnan(img_arr)] = 0

    # Reshape data to a 1D array (required by k-means)
    X = np.copy(img_arr).flatten().reshape(-1, 1)

    print("X: ", X)
    print("X shape : ", X.shape)
    print("X max : ", np.max(X))

    print("Round X max : ", np.round(np.max(X)))
    nb_bins = (np.rint((np.max(X) - np.min(X))/sample_bins)).astype(int)
    print("Nb bins: ", nb_bins)

    # Create a histogram
    hist, bins, _ = plt.hist(X, bins=nb_bins,
                             alpha=0.5, color='b', label='Histogram')

    # Add labels and a legend
    plt.xlabel('Value')
    plt.ylabel('Probability')

    # Save the figure as a PNG file
    plt.savefig(os.path.abspath('histogram.png'))
    plt.clf()

    # filtering
    new_mask_data = np.zeros(img_arr.shape, dtype=img_arr.dtype)

    assert operation in ["higher", "interval", "lower"], \
        "Error in operation {}".format(operation)

    with open(os.path.abspath("kmeans.log"), "w+") as g:

        g.write("Running Kmeans with : {} {} {}\n".format(
            operation, index, num_clusters))

        # Reshape data to a 1D array (required by k-means)
        X = np.copy(img_arr).flatten().reshape(-1, 1)

        kmeans = KMeans(n_clusters=num_clusters, random_state=0)

        # Fit the model to the data and predict cluster labels
        cluster_labels = kmeans.fit_predict(X)

        # Split data into groups based on cluster labels
        groups = [X[cluster_labels == i].flatten()
                  for i in range(num_clusters)]

        avail_operations = ["lower", "interval", "higher"]

        assert operation in avail_operations, "Error, \
            {} is not in {}".format(operation, avail_operations)

        assert 0 <= index and index < num_clusters, "Error \
            with index {}".format(index)

        # We must define : the minimum of the second group for the headmask
        # we create minimums array, we sort and then take the middle value
        minimums_array = np.array([np.amin(group) for group in groups])
        min_sorted = np.sort(minimums_array)

        g.write("Cluster Min : {}\n".format(
            " ".join(str(val) for val in min_sorted)))

        # We must define : the maximum of the second group for the headmask
        # we create maximums array, we sort and then take the middle value
        maximums_array = np.array([np.amax(group) for group in groups])
        max_sorted = np.sort(maximums_array)

        g.write("Cluster Max : {}\n".format(
            " ".join(str(val) for val in max_sorted)))

        # We must define :  mean of the second group for the skull extraction
        # we create means array, we sort and then take the middle value
        means_array = np.array([sum(group)/len(group) for group in groups])
        mean_sorted = np.sort(means_array)

        index_sorted = np.argsort(means_array)

        g.write("Cluster Mean : {}\n".format(
            " ".join(str(int(val)) for val in mean_sorted)))

        g.write("Cluster Indexes = {}\n".format(
            " ".join(str(int(val)) for val in index_sorted)))

        g.write("Indexed cluster ({}): {}\n".format(
            index, index_sorted[index]))

        min_thresh = np.amin(groups[index_sorted[index]])
        max_thresh = np.amax(groups[index_sorted[index]])

        g.write("Min/max mid group : {} {}\n".format(
            min_thresh, max_thresh))

        if operation == "lower":
            g.write("Filtering with lower threshold {}\n".format(min_thresh))
            fiter_array = min_thresh < img_arr

        elif operation == "higher":
            g.write("Filtering with higher threshold {}\n".format(max_thresh))
            fiter_array = img_arr < max_thresh

        elif operation == "interval":
            g.write(
                "Filtering between lower {} and higher {}\n".format(
                    min_thresh, max_thresh))

            fiter_array = np.logical_and(min_thresh < img_arr,
                                         img_arr < max_thresh)

    new_mask_data[fiter_array] = img_arr[fiter_array]

    print("Before filter: ", np.sum(img_arr != 0.0),
          "After filter: ", np.sum(new_mask_data != 0.0))

    # saving mask as nii
    path, fname, ext = split_f(img_file)

    mask_img_file = os.path.abspath(fname + "_autothresh" + ext)

    mask_img = nib.Nifti1Image(dataobj=new_mask_data,
                               header=img_nii.header,
                               affine=img_nii.affine)
    nib.save(mask_img, mask_img_file)

    return mask_img_file
