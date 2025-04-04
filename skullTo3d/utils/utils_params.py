
def update_indiv_params(params=None, indiv_params=None,
                        subjects=None, sessions=None,
                        extra_wf_name=""):

    if not indiv_params:
        # empty indiv
        return params, indiv_params, extra_wf_name

    if "skull_ct_pipe" not in params.keys():

        print("skull_ct_pipe not found in params, \
            not modifying preparation pipe")

    else:

        count_all_sessions = 0
        count_CT_crops = 0

        if subjects is None:
            print("For whole BIDS dir, \
                unable to assess if the indiv_params is correct")
            print("Running by default skull_ct_pipe and crop_CT")

        else:

            print("Will modify params if necessary, \
                given specified subjects and sessions;\n")

            for sub in indiv_params.keys():

                if sub.split('-')[1] not in subjects:
                    print('could not find subject {} in {}'.format(
                        sub.split('-')[1], subjects))
                    continue

                if all([key.split('-')[0] == "ses"
                        for key in indiv_params[sub].keys()]):

                    for ses in indiv_params[sub].keys():

                        if ses.split('-')[1] not in sessions:

                            print('could not find session {} in {}'.format(
                                ses.split('-')[1], sessions))
                            continue

                        count_all_sessions += 1

                        indiv = indiv_params[sub][ses]

                        print(indiv.keys())

                        if "skull_ct_pipe" in indiv.keys():
                            count_CT_crops += 1

                else:
                    count_all_sessions += 1

                    indiv = indiv_params[sub]

                    print(indiv.keys())

                    if "skull_ct_pipe" in indiv.keys():
                        count_CT_crops += 1

            print("count_all_sessions {}".format(count_all_sessions))
            print("count_CT_crops {}".format(count_CT_crops))

            if count_all_sessions:
                if count_CT_crops == count_all_sessions:

                    print("**** Found crop for CT for all \
                        sub/ses in indiv \
                        -> keeping skull_ct_pipe")

                    extra_wf_name += "_crop_CT"

                    print("Adding skull_ct_pipe")
                    params["skull_ct_pipe"]["crop_CT"] = \
                        {"args": "should be defined in indiv"}

                else:
                    print("**** not all sub/ses have CT crops,\
                        using autocrop ")

        return params, indiv_params, extra_wf_name
