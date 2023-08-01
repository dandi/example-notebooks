import datajoint as dj
from . import get_schema_name
from . import experiment
import scipy.stats as ss
import numpy as np

schema = dj.schema(get_schema_name('imaging'))


@schema
class CellType(dj.Lookup):
    definition = """
    #
    cell_type  :  varchar(100)
    ---
    cell_type_description :  varchar(4000)
    """
    contents = [
        ('Pyr', 'putative pyramidal neuron'),
        ('interneuron', 'interneuron'),
        ('PT', 'pyramidal tract neuron'),
        ('IT', 'intratelecephalic neuron'),
        ('FS', 'fast spiking'),
        ('N/A', 'unknown')
    ]


@schema
class Scan(dj.Imported):
    definition = """
    -> experiment.Session
    ---
    image_gcamp:       longblob # 512 x 512, a summary image of GCaMP at 940nm, obj-images-value1
    image_ctb:         longblob # 512 x 512, a summary image of CTB-647, obj-images-value2
    image_beads=null:  longblob # 512 x 512, a summary image of Beads, obj-images-value3
    frame_time:        longblob # obj-timeSeriesArrayHash-value(1, 1)-time, aligned to the first trial start
    """

    class Roi(dj.Part):
        definition = """
        -> master
        roi_idx:   int
        ---
        -> CellType
        roi_trace:          longblob        # average fluorescence of roi obj-timeSeriesArrayHash-value(1, 1)-valueMatrix
        neuropil_trace:     longblob        # average fluorescence of neuopil surounding each ROI, obj-timeSeriesArrayHash-value(1, 1)-valueMatrix
        roi_pixel_list:     longblob        # pixel list of this roi
        neuropil_pixel_list:longblob        # pixel list of the neuropil surrounding the roi
        inc:                bool            # whether included (criteria - cells > 1.05 times brighter than neuropil)
        """

@schema
class TrialTrace(dj.Imported):
    definition = """
    -> Scan.Roi
    -> experiment.SessionTrial
    ---
    original_time:      longblob  # original time cut for this trial
    aligned_time:       longblob  # 0 is go cue time
    aligned_trace:      longblob  # aligned trace relative to the go cue time
    dff:                longblob  # dff, normalized with f[0:5]
    """


@schema
class RoiAnalyses(dj.Computed):
    definition = """
    -> Scan.Roi
    ---
    dff_m_l:        longblob    # median dff across trials, for correct left
    dff_m_r:        longblob    # median dff across trials, for correct right
    dff_int_l:      float       # integral dff over task period for left trials
    dff_int_r:      float       # integral dff over task period for right trials
    dff_diff:       float       # dff_int_r - dff_int_l
    p_selective:    float       # p value for trial type selectivity
    is_selective:   bool        # whether is trial type selective p < 0.05
    selectivity:    enum('Contra', 'Ipsi', 'Non selective')  # contra or ipsi
    p_responsive_l: float       # p value for task relevance in left trials
    p_responsive_r: float       # p value for task relevance in right trials
    is_responsive:  bool        # whether is responsive to left/right trials, True if either responsive to left or right
    mean_amp:       float       # peak amplitude of mean activity
    frame_peak:     int         # frame number for the peak activity
    frame_rise_half:int         # frame number of the half peak activity
    """

    key_source = Scan()

    def make(self, key):
        # selected samples
        task_range = range(6, 90)

        roi_info = []
        for roi in (Scan.Roi & key).fetch('KEY'):

            # calculate median dff for each trial type (dff_m)
            dff_r, f_r = ((TrialTrace & roi) &
                    (experiment.BehaviorTrial &
                    'trial_instruction="right"' &
                    'outcome="hit"')).fetch('dff', 'aligned_trace')
            dff_l, f_l = ((TrialTrace & roi) &
                    (experiment.BehaviorTrial &
                    'trial_instruction="left"' &
                    'outcome="hit"')).fetch('dff', 'aligned_trace')
            dff_r = np.array([f for f in dff_r])
            dff_l = np.array([f for f in dff_l])
            f_r = np.array([f for f in f_r])
            f_l = np.array([f for f in f_l])

            dff_m_r = np.nanmedian(dff_r, axis=0)
            dff_m_l = np.nanmedian(dff_l, axis=0)

            # calculate trial type selectivity (p_selective)
            dff_int_l = np.mean(dff_l[:, task_range], axis=1)
            dff_int_r = np.mean(dff_r[:, task_range], axis=1)

            _, p_selective = ss.ranksums(dff_int_r, dff_int_l)
            dff_diff = np.nanmean(dff_int_r) - np.nanmean(dff_int_l)
            is_selective = bool(p_selective < 0.05)

            # calculate task selectivity (p_task)
            nbin=5
            ntgroup=18
            f_r = np.mean(f_r.reshape([-1, nbin, ntgroup]), axis=1)
            f_l = np.mean(f_l.reshape([-1, nbin, ntgroup]), axis=1)
            _, p_responsive_r = ss.mstats.kruskalwallis([f for f in f_r])
            _, p_responsive_l = ss.mstats.kruskalwallis([f for f in f_l])
            is_responsive = bool((p_responsive_l < 0.01) + (p_responsive_r < 0.01))

            # identify selectivity
            if dff_diff > 0 and is_responsive and is_selective:
                selectivity = 'Contra'
            elif dff_diff < 0 and is_responsive and is_selective:
                selectivity = 'Ipsi'
            else:
                selectivity = 'Non selective'

            # calculate peak amp and frame for peak amp and half rise
            base_ids = range(0, 6)
            dff_m = np.array([dff_m_r[6:], dff_m_l[6:]])
            dff_mean = np.mean(dff_m, axis=1)
            idx = np.abs(dff_mean).argmax()
            trace = dff_m[idx] * np.sign(dff_mean[idx])
            trace[base_ids] = 0

            frame_peak = trace.argmax()
            peak = trace[frame_peak]
            frame_rise_half = np.where((trace - peak/2) > 0)[0][0]

            # populate output structure
            roi_info.append(
                dict(
                    **roi,
                    dff_m_l=dff_m_l,
                    dff_m_r=dff_m_r,
                    dff_diff= dff_diff,
                    p_selective=p_selective,
                    is_selective=is_selective,
                    dff_int_l=np.nanmean(dff_int_l),
                    dff_int_r=np.nanmean(dff_int_r),
                    p_responsive_l=p_responsive_l,
                    p_responsive_r=p_responsive_r,
                    is_responsive=is_responsive,
                    selectivity=selectivity,
                    mean_amp=peak,
                    frame_peak=frame_peak,
                    frame_rise_half=frame_rise_half
                )
            )

        self.insert(roi_info)


@schema
class PreferenceMap(dj.Computed):
    definition = """
    -> Scan
    ---
    preference_map:         longblob    # 512 x 512 x 3 matrix of RGB
    """

    def make(self, key):
        im = np.ones([512, 512, 3])

        # mark the non-selective cells
        pl_non_sel = (Scan.Roi & key &
                     (RoiAnalyses & 'selectivity="Non selective"')).fetch('roi_pixel_list')
        if len(pl_non_sel):
            pl_non_sel = np.unravel_index(np.hstack(pl_non_sel), [512, 512])
            im[pl_non_sel[0], pl_non_sel[1], :] = 211/255

        # mark the contra-selective cells
        pl_contra = (Scan.Roi & key &
                     (RoiAnalyses & 'selectivity="Contra"')).fetch('roi_pixel_list')
        if len(pl_contra):
            pl_contra = np.unravel_index(np.hstack(pl_contra), [512, 512])
            im[pl_contra[0], pl_contra[1], :] = np.array([0, 0, 1])

        # mark the ipsi-selective cells
        pl_ipsi = (Scan.Roi & key &
                   (RoiAnalyses & 'selectivity="Ipsi"')).fetch('roi_pixel_list')
        if len(pl_ipsi):
            pl_ipsi = np.unravel_index(np.hstack(pl_ipsi), [512, 512])
            im[pl_ipsi[0], pl_ipsi[1], :] = np.array([1, 0, 0])

        self.insert1(dict(**key, preference_map=im))
