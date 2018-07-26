import optparse
import numpy as np
import h5py

import frbkeras
import reader
import plot_tools

if __name__=="__main__":
    parser = optparse.OptionParser(prog="classify.py", \
                        version="", \
                        usage="%prog FN_DATA FN_MODEL [OPTIONS]", \
                        description="Apply DNN model to FRB candidates")

    parser.add_option('--pthresh', dest='prob_threshold', type='float', \
                        help="probability treshold", default=0.5)

    parser.add_option('--save_ranked', dest='save_ranked', action='store_true', \
                        help="save FRB events + probabilities", default=False)

    parser.add_option('--plot_ranked', dest='plot_ranked', action='store_true',\
                        help="plot triggers", default=False)

    parser.add_option('--twindow', dest='twindow', type='int', \
                        help="time width, default 64", default=64)

    parser.add_option('--fnout', dest='fnout', type='str', \
                        help="beginning of figure names", default='ranked_trig')

    options, args = parser.parse_args()

    assert len(args)==2, "Arguments are FN_DATA FN_MODEL [OPTIONS]"

    fn_data = args[0]
    fn_model = args[1]

    print("Using datafile %s" % fn_data)
    print("Using keras model in %s" % fn_model)

    data_freq, y, data_dm, data_mb = reader.read_hdf5(fn_data)

    NFREQ = data_freq.shape[1]
    NTIME = data_freq.shape[2]
    WIDTH = options.twindow

    # low time index, high time index
    tl, th = NTIME//2-WIDTH//2, NTIME//2+WIDTH//2

    if data_freq.shape[-1] > (th-tl):
        data_freq = data_freq[..., tl:th]

    dshape = data_freq.shape

    # normalize data
    data_freq = data_freq.reshape(len(data_freq), -1)
    data_freq -= np.median(data_freq, axis=-1)[:, None]
    data_freq /= np.std(data_freq, axis=-1)[:, None]

    # zero out nans
    data_freq[data_freq!=data_freq] = 0.0
    data_freq = data_freq.reshape(dshape)

    if data_freq.shape[-1]!=1:
        data_freq = data_freq[..., None]

    model = frbkeras.load_model(fn_model)

    if len(model.input.shape)==3:
        data_freq = data_freq.mean(1)
        
    y_pred_prob = model.predict(data_freq)
    y_pred_prob = y_pred_prob[:,1]

    ind_frb = np.where(y_pred_prob>options.prob_threshold)[0]

    print("\n%d out of %d events with probability > %.2f:\n %s" % 
            (len(ind_frb), len(y_pred_prob), 
                options.prob_threshold, ind_frb))

    low_to_high_ind = np.argsort(y_pred_prob)

    if options.save_ranked is True:
        fnout_ranked = fn_data.rstrip('.hdf5') + 'freq_time_candidates.hdf5'

        g = h5py.File(fnout_ranked, 'w')
        g.create_dataset('data_frb_candidate', data=data_freq[ind_frb])
        g.create_dataset('frb_index', data=ind_frb)
        g.create_dataset('probability', data=y_pred_prob)
        g.close()
        print("\nSaved them and all probabilities to: \n%s" % fnout_ranked)

    if options.plot_ranked is True:
        if options.save_ranked is False:
            argtup = (data_freq[ind_frb], ind_frb, y_pred_prob)
            plot_tools.plot_multiple_ranked(argtup, nside=5, fnfigout=options.fnout)
        else:
            plot_tools.plot_multiple_ranked(fnout_ranked, nside=5, fnfigout=options.fnout)
            
        # print(data_freq.shape)
        # plot_tools.plot_ranked_trigger(data_freq[..., 0], 
        #         y_pred_prob, h=5, w=5, ascending=False, 
        #         outname='out')
