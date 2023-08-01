import datajoint as dj
from . import get_schema_name
from . import experiment
import numpy as np
import pandas as pd

from statsmodels.formula.api import ols

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
    image_ctb=null:    longblob # 512 x 512, a summary image of CTB-647, obj-images-value2
    image_beads=null:  longblob # 512 x 512, a summary image of Beads, obj-images-value3
    frame_time:        longblob # obj-timeSeriesArrayHash-value(1, 1)-time, aligned to the first trial start
    """

    class Roi(dj.Part):
        definition = """
        -> master
        roi_idx:   int
        ---
        -> CellType
        roi_trace:          longblob        # average fluorescence of roi
        neuropil_trace:     longblob        # average fluorescence of neuopil surounding each ROI
        roi_trace_corrected:longblob        # average fluorescence of roi substracting neuropil * 0.7
        roi_pixel_list:     longblob        # pixel list of this roi
        ap_position:        float           # in um, relative to bregma
        ml_position:        float           # in um, relative to bregma
        inc:                bool            # whether included (criteria - cells > 1.05 times brighter than neuropil)
        """

@schema
class TrialTrace(dj.Imported):
    definition = """
    -> Scan.Roi
    -> experiment.SessionTrial
    ---
    original_time:              longblob  # original time cut for this trial
    aligned_time:               longblob  # 0 is go cue time
    aligned_trace:              longblob  # aligned trace relative to the go cue time
    aligned_trace_corrected:    longblob  # aligned trace
    dff:                        longblob  # dff of corrected, normalized with f[0:6]
    """


@schema
class RoiAnalyses(dj.Computed):
    definition = """
    -> Scan.Roi
    ---
    panova  :   longblob    # matrix of nFrames x 4, p values of alpha, beta, gamma and incerpt
    alpha   :   longblob    # vector with length nFrames, coefficient of instruction
    beta    :   longblob    # vector with length nFrames, coefficient of lick
    gamma   :   longblob    # vector with length nFrames, coefficient of outcome
    mu      :   longblob    # vector with length nFrames, coefficient of intercept
    """

    key_source = Scan()

    def make(self, key):

        roi_info = []
        for roi in (Scan.Roi & key & {'inc': True}).fetch('KEY'):

            print(roi)

            # fetch trial info from the table
            dff, instruction, outcome  = \
                (TrialTrace * experiment.BehaviorTrial &
                 roi & 'outcome in ("hit", "miss")').fetch(
                     'dff','trial_instruction', 'outcome')

            dff_dict = {i:f for i, f in enumerate(dff) if len(f)}
            dff = np.array(list(dff_dict.values()))

            instruction = instruction[list(dff_dict.keys())]
            outcome = outcome[list(dff_dict.keys())]
            lick = np.array(['right']*len(instruction))
            left = np.logical_or(
                np.logical_and(np.array(instruction)=='left', np.array(outcome)=='hit'),
                np.logical_and(np.array(instruction)=='right', np.array(outcome)=='miss'))
            lick[left]=np.array(['left'] * sum(left))

            df = pd.DataFrame()
            df['instruction'] = instruction
            df['lick'] = lick
            df['outcome'] = outcome

            panova = []
            alpha = []
            beta = []
            gamma = []
            mu = []
            for t in range(np.shape(dff)[1]):
                df['dff'] = dff[:, t]
                model = ols('dff ~ C(instruction)+C(lick)+C(outcome)', df).fit()
                panova.append([
                    model.pvalues['C(instruction)[T.right]'],
                    model.pvalues['C(lick)[T.right]'],
                    model.pvalues['C(outcome)[T.miss]'],
                    model.pvalues['Intercept']
                ])
                cl = df[df['lick']=='left'][df['instruction']=='left']['dff'].mean()
                cr = df[df['lick']=='right'][df['instruction']=='right']['dff'].mean()
                el = df[df['lick']=='left'][df['instruction']=='right']['dff'].mean()
                er = df[df['lick']=='right'][df['instruction']=='left']['dff'].mean()

                alpha.append((er-cl+cr-el)/2)
                beta.append((el-cl+cr-er)/2)
                gamma.append((cr+cl-er-el)/2)
                mu.append((cl-cr+er+el)/2)

            # populate output structure
            roi_info.append(
                dict(
                    **roi,
                    panova=panova,
                    alpha=alpha,
                    beta=beta,
                    gamma=gamma,
                    mu=mu
                )
            )

        self.insert(roi_info)
