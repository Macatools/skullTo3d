def mask_auto_threshold(img_file, operation, index):
    import numpy as np
    import nibabel as nib
    from sklearn.cluster import KMeans

    # Mean function
    def calculate_mean(data):
        total = sum(data)
        count = len(data)
        mean = total / count
        return mean

    img_nii = nib.load(img_file)
    img_arr = np.array(img_nii.dataobj)

    # Reshape data to a 1D array (required by k-means)
    X = np.copy(img_arr).flatten().reshape(-1, 1)

    print("X shape : ", X.shape)

    # Create a k-means clustering model with 3 clusters
    # using k-means++ initialization

    num_clusters = 3

    kmeans = KMeans(n_clusters=num_clusters, random_state=0)

    # Fit the model to the data and predict cluster labels
    cluster_labels = kmeans.fit_predict(X)

    # Split data into groups based on cluster labels
    groups = [X[cluster_labels == i].flatten() for i in range(num_clusters)]

    avail_operations = ["min", "mean", "max"]

    assert operation in avail_operations, "Error, \
        {} is not in {}".format(operation, avail_operations)

    assert 0 <= index and index < num_clusters, "Error \
        with index {}".format(index)

    # We must define : the minimum of the second group for the headmask
    # we create minimums array, we sort and then take the middle value
    minimums_array = np.array([np.amin(group) for group in groups])
    min_sorted = np.sort(minimums_array)

    print("Min : {}".format(" ".join(str(val) for val in min_sorted)))

    # We must define :  mean of the second group for the skull extraction
    # we create means array, we sort and then take the middle value
    means_array = np.array([calculate_mean(group) for group in groups])
    mean_sorted = np.sort(means_array)

    index_sorted = np.argsort(means_array)

    print("Mean : {}".format(" ".join(str(int(val)) for val in mean_sorted)))

    print("Index = {}".format(" ".join(str(int(val)) for val in index_sorted)))

    print("Index mid group : ", index_sorted[index])
    print("Min/max mid group : ", np.amin(groups[index_sorted[index]]),
          np.amax(groups[index_sorted[index]]))

    maximums_array = np.array([np.amax(group) for group in groups])
    max_sorted = np.sort(maximums_array)

    print("Max : {}".format(" ".join(str(val) for val in max_sorted)))

    if operation == "min":  # for head mask
        mask_threshold = min_sorted[index]
        print("headmask_threshold : ", mask_threshold)

    elif operation == "mean":  # for skull mask

        mask_threshold = mean_sorted[index]
        print("skull_extraction_threshold : ", mask_threshold)

    elif operation == "max":  # unused

        mask_threshold = max_sorted[index]
        print("max threshold : ", mask_threshold)

    return mask_threshold


def mask_auto_img(img_file, operation, index,
                  sample_bins, distance, kmeans):

    import os
    import numpy as np
    import nibabel as nib
    import matplotlib.pyplot as plt

    from scipy.signal import find_peaks

    from nipype.utils.filemanip import split_filename as split_f

    def compute_Kmeans(img_arr, operation, index=1, num_clusters=3):
        import os
        import numpy as np
        from sklearn.cluster import KMeans
        # Mean function

        def calculate_mean(data):
            total = sum(data)
            count = len(data)
            mean = total / count
            return mean

        g = open(os.path.abspath("kmeans.log"), "w+")

        print("Running Kmeans with : ", operation, index, num_clusters)

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

        print("Cluster Min : {}".format(
            " ".join(str(val) for val in min_sorted)))
        g.write("Cluster Min : {}\n".format(
            " ".join(str(val) for val in min_sorted)))

        # We must define : the maximum of the second group for the headmask
        # we create maximums array, we sort and then take the middle value
        maximums_array = np.array([np.amax(group) for group in groups])
        max_sorted = np.sort(maximums_array)

        print("Cluster Max : {}".format(
            " ".join(str(val) for val in max_sorted)))
        g.write("Cluster Max : {}\n".format(
            " ".join(str(val) for val in max_sorted)))

        # We must define :  mean of the second group for the skull extraction
        # we create means array, we sort and then take the middle value
        means_array = np.array([calculate_mean(group) for group in groups])
        mean_sorted = np.sort(means_array)

        index_sorted = np.argsort(means_array)

        print("Cluster Mean : {}".format(
            " ".join(str(int(val)) for val in mean_sorted)))
        g.write("Cluster Mean : {}\n".format(
            " ".join(str(int(val)) for val in mean_sorted)))

        print("Cluster Indexes = {}".format(
            " ".join(str(int(val)) for val in index_sorted)))
        g.write("Cluster Indexes = {}\n".format(
            " ".join(str(int(val)) for val in index_sorted)))

        print("Indexed cluster ({}): {}".format(
            index, index_sorted[index]))
        g.write("Indexed cluster ({}): {}\n".format(
            index, index_sorted[index]))

        min_thresh = np.amin(groups[index_sorted[index]])
        max_thresh = np.amax(groups[index_sorted[index]])

        print("Min/max mid group : {} {}".format(min_thresh,
                                                 max_thresh))
        g.write("Min/max mid group : {} {}\n".format(min_thresh,
                                                     max_thresh))

        if operation == "lower":
            print("Filtering with lower threshold {}".format(min_thresh))
            g.write("Filtering with lower threshold {}\n".format(min_thresh))
            fiter_array = min_thresh < img_arr

        elif operation == "higher":
            print("Filtering with higher threshold {}".format(max_thresh))
            g.write("Filtering with higher threshold {}\n".format(max_thresh))
            fiter_array = img_arr < max_thresh

        elif operation == "interval":
            print(
                "Filtering between lower {} and higher {}".format(
                    min_thresh, max_thresh))
            g.write(
                "Filtering between lower {} and higher {}\n".format(
                    min_thresh, max_thresh))

            fiter_array = np.logical_and(min_thresh < img_arr,
                                         img_arr < max_thresh)

        g.close()

        return fiter_array

    log_file = os.path.abspath("local_minima.log")

    f = open(log_file, "w+")

    print("Running local minimas with : kmeans=",
          kmeans, operation, index, sample_bins, distance)

    f.write("Running local minimas with : kmeans={} {} {} {} {}\n".format(
        kmeans, operation, index, sample_bins, distance))

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
    nb_bins = (np.rint(np.max(X)/sample_bins)).astype(int)
    print("Nb bins: ", nb_bins)

    f.write("X shape : {}\n".format(X.shape))
    f.write("X max : {}\n".format(np.round(np.max(X))))
    f.write("Nb bins: {}\n".format(nb_bins))

    # Create a histogram
    hist, bins, _ = plt.hist(X, bins=nb_bins,
                             alpha=0.5, color='b', label='Histogram')

    # Add labels and a legend
    plt.xlabel('Value')
    plt.ylabel('Probability')

    # Save the figure as a PNG file
    plt.savefig(os.path.abspath('histogram.png'))
    plt.clf()

    # Find local minima in the histogram
    peaks, _ = find_peaks(-hist, distance=distance)
    # Use negative histogram for minima

    print("peaks indexes :", peaks)

    print("peak_hist :", hist[peaks])
    print("peak_bins :", bins[peaks])

    f.write("peaks indexes : {}\n".format(peaks))
    f.write("peak_hist : {}\n".format(hist[peaks]))
    f.write("peak_bins : {}\n".format(bins[peaks]))

    # filtering
    new_mask_data = np.zeros(img_arr.shape, dtype=img_arr.dtype)

    assert operation in ["higher", "interval", "lower"], \
        "Error in operation {}".format(operation)

    if kmeans:
        print("kmeans=True, Skipping local minima")
        f.write("kmeans=True, Skipping local minima\n")

        proceed = False
    else:

        print("Running local minima, then Kmeans if failing")
        f.write("Running local minima, then Kmeans if failing\n")
        proceed = True

    if operation == "interval":
        if not (isinstance(index, list) and len(index) == 2):
            print("Error, index {} should be a list for interval".format(
                index))
            proceed = False

        if not (peaks.shape[0] > 1):
            print("Error, could not find at least two local minima")
            proceed = False

        if index[0] < 0 or len(bins[peaks]) <= index[0]:
            print("Error, index 0 {} out of peak indexes ".format(index[0]))
            proceed = False

        if index[1] < index[0] or len(bins[peaks]) <= index[1]:
            print("Error, index 1 {} out of peak indexes ".format(index[1]))
            proceed = False

        if proceed:
            index_peak_min = bins[peaks][index[0]]
            index_peak_max = bins[peaks][index[1]]

            print("Keeping interval between {} and {}".format(
                index_peak_min,
                index_peak_max))

            f.write("Keeping interval between {} and {}\n".format(
                index_peak_min, index_peak_max))

            filter_arr = np.logical_and(
                index_peak_min < img_arr,
                img_arr < index_peak_max)

        else:

            print("Running Kmeans with interval index {}\n".format(index))
            f.write("Running Kmeans with interval index {}\n".format(index))
            filter_arr = compute_Kmeans(img_arr, operation="interval", index=1)

    elif operation == "higher":
        if not isinstance(index, int):
            print("Error, index {} should be a integer for higher".format(
                index))
            proceed = False

        if index < 0 or len(bins[peaks]) <= index:

            print("Error, {} out of peak indexes ".format(index))
            proceed = False

        if proceed:
            index_peak_max = bins[peaks][index]

            f.write("Filtering with higher threshold {}\n".format(
                index_peak_max))
            print("Filtering with higher threshold {}\n".format(
                index_peak_max))

            filter_arr = img_arr < index_peak_max

        else:

            print("Running Kmeans with higher index {}\n".format(index))
            f.write("Running Kmeans with higher index {}\n".format(index))
            filter_arr = compute_Kmeans(
                img_arr, operation="higher", index=index)

    elif operation == "lower":
        if not isinstance(index, int):
            print("Error, index {} should be a integer for lower".format(
                index))
            proceed = False

        if index < 0 or len(bins[peaks]) <= index:

            print("Error, {} out of peak indexes ".format(index))
            proceed = False

        if proceed:
            index_peak_min = bins[peaks][index]

            f.write("Filtering with lower threshold {}\n".format(
                index_peak_min))
            print("Filtering with lower threshold {}\n".format(
                index_peak_min))

            filter_arr = index_peak_min < img_arr
        else:
            print("Running Kmeans with lower index {}\n".format(index))
            f.write("Running Kmeans with lower index {}\n".format(index))
            filter_arr = compute_Kmeans(
                img_arr, operation="lower", index=index)

    new_mask_data[filter_arr] = img_arr[filter_arr]

    print("Before filter: ", np.sum(img_arr != 0.0),
          "After filter: ", np.sum(new_mask_data != 0.0))

    # saving mask as nii

    path, fname, ext = split_f(img_file)

    mask_img_file = os.path.abspath(fname + "_autothresh" + ext)

    mask_img = nib.Nifti1Image(dataobj=new_mask_data,
                               header=img_nii.header,
                               affine=img_nii.affine)
    nib.save(mask_img, mask_img_file)

    f.close()

    return mask_img_file
