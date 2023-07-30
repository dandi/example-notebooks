
import datajoint as dj
import numpy as np

from . import lab
from . import get_schema_name

schema = dj.schema(get_schema_name('experiment'))


@schema
class Session(dj.Manual):
    definition = """
    -> lab.Subject
    session : smallint 		# session number
    ---
    session_date  : date
    -> lab.Person
    -> [nullable] lab.Rig
    """


@schema
class Task(dj.Lookup):
    definition = """
    # Type of tasks
    task            : varchar(12)                  # task type
    ----
    task_description : varchar(4000)
    """
    contents = [
         ('audio delay', 'auditory delayed response task (2AFC)'),
         ('audio mem', 'auditory working memory task'),
         ('s1 stim', 'S1 photostimulation task (2AFC)')
         ]


@schema
class TaskProtocol(dj.Lookup):
    definition = """
    # SessionType
    -> Task
    task_protocol : tinyint # task protocol
    ---
    task_protocol_description : varchar(4000)
    """
    contents = [
         ('audio delay', 1, 'high tone vs. low tone'),
         ('s1 stim', 2, 'mini-distractors'),
         ('s1 stim', 3, 'full distractors, with 2 distractors (at different times) on some of the left trials'),
         ('s1 stim', 4, 'full distractors'),
         ('s1 stim', 5, 'mini-distractors, with different levels of the mini-stim during sample period'),
         ('s1 stim', 6, 'full distractors; same as protocol 4 but with a no-chirp trial-type'),
         ('s1 stim', 7, 'mini-distractors and full distractors (only at late delay)'),
         ('s1 stim', 8, 'mini-distractors and full distractors (only at late delay), with different levels of the mini-stim and the full-stim during sample period'),
         ('s1 stim', 9, 'mini-distractors and full distractors (only at late delay), with different levels of the mini-stim and the full-stim during sample period')
         ]



@schema
class Photostim(dj.Manual):
    definition = """
    -> Session
    photo_stim :  smallint 
    ---
    -> lab.PhotostimDevice
    waveform=null:  longblob       # normalized to maximal power. The value of the maximal power is specified for each PhotostimTrialEvent individually
    frequency=null: float  # (Hz) 
    """

    class PhotostimLocation(dj.Part):
        definition = """
        -> master
        -> lab.SkullReference
        ap_location: decimal(6, 2) # (um) from ref; anterior is positive; based on manipulator coordinates/reconstructed track
        ml_location: decimal(6, 2) # (um) from ref ; right is positive; based on manipulator coordinates/reconstructed track
        dv_location: decimal(6, 2) # (um) from dura to first site of the probe; ventral is negative; based on manipulator coordinates/reconstructed track
        ---
        theta=null:       decimal(5, 2) # (degree)  rotation about the ml-axis 
        phi=null:         decimal(5, 2) # (degree)  rotation about the dv-axis
        -> lab.BrainArea
        """


@schema
class PhotostimBrainRegion(dj.Computed):
    definition = """
    -> Photostim
    ---
    -> lab.BrainArea.proj(stim_brain_area='brain_area')
    stim_laterality: enum('left', 'right', 'bilateral')
    """

    def make(self, key):
        brain_areas, ml_locations = (Photostim.PhotostimLocation & key).fetch('brain_area', 'ml_location')
        if len(set(brain_areas)) > 1:
            raise ValueError('Multiple different brain areas for one photostim protocol is unsupported')
        if (ml_locations > 0).any() and (ml_locations < 0).any():
            lat = 'bilateral'
        elif (ml_locations > 0).all():
            lat = 'right'
        elif (ml_locations < 0).all():
            lat = 'left'
        else:
            assert (ml_locations == 0).all()  # sanity check
            raise ValueError('Ambiguous hemisphere: ML locations are all 0...')

        self.insert1(dict(key, stim_brain_area=brain_areas[0], stim_laterality=lat))


@schema
class SessionTrial(dj.Imported):
    definition = """
    -> Session
    trial : smallint 		# trial number
    ---
    trial_uid=null : int  # unique across sessions/animals
    start_time : decimal(8, 4)  # (s) relative to session beginning 
    stop_time=null: decimal(8, 4)  # (s) relative to session beginning 
    """


@schema 
class TrialNoteType(dj.Lookup):
    definition = """
    trial_note_type : varchar(12)
    """
    contents = zip(('autolearn', 'protocol #', 'bad', 'bitcode'))


@schema
class TrialNote(dj.Imported):
    definition = """
    -> SessionTrial
    -> TrialNoteType
    ---
    trial_note  : varchar(255) 
    """


@schema
class TrainingType(dj.Lookup):
    definition = """
    # Mouse training
    training_type : varchar(100) # mouse training
    ---
    training_type_description : varchar(2000) # description
    """
    contents = [
         ('regular', ''),
         ('regular + distractor', 'mice were first trained on the regular S1 photostimulation task  without distractors, then the training continued in the presence of distractors'),
         ('regular or regular + distractor', 'includes both training options')
         ]


@schema
class SessionTraining(dj.Manual):
    definition = """
    -> Session
    -> TrainingType
    """


@schema
class SessionTask(dj.Manual):
    definition = """
    -> Session
    -> TaskProtocol
    """


@schema
class SessionComment(dj.Manual):
    definition = """
    -> Session
    ---
    session_comment : varchar(767)
    """


# ---- behavioral trials ----

@schema
class TrialInstruction(dj.Lookup):
    definition = """
    # Instruction to mouse 
    trial_instruction  : varchar(16) 
    """
    contents = zip(('left', 'right', 'non-performing'))


@schema
class Outcome(dj.Lookup):
    definition = """
    outcome : varchar(32)
    """
    contents = zip(('hit', 'miss', 'ignore', 'non-performing'))


@schema
class EarlyLick(dj.Lookup):
    definition = """
    early_lick  :  varchar(32)
    ---
    early_lick_description : varchar(4000)
    """
    contents = [
        ('early', 'early lick during sample and/or delay'),
        ('early, presample only', 'early lick in the presample period, after the onset of the scheduled wave but before the sample period'),
        ('no early', '')]


@schema
class BehaviorTrial(dj.Imported):
    definition = """
    -> SessionTrial
    ----
    -> TaskProtocol
    -> TrialInstruction
    -> EarlyLick
    -> Outcome
    """


@schema
class TrialEventType(dj.Lookup):
    definition = """
    trial_event_type  : varchar(12)  
    """
    contents = zip(('delay', 'go', 'sample', 'presample', 'trialend'))


@schema
class TrialEvent(dj.Imported):
    definition = """
    -> BehaviorTrial 
    trial_event_id: smallint
    ---
    -> TrialEventType
    trial_event_time : decimal(8, 4)   # (s) from trial start, not session start
    duration=null: decimal(8,4)  #  (s)  
    """


@schema
class ActionEventType(dj.Lookup):
    definition = """
    action_event_type : varchar(32)
    ----
    action_event_description : varchar(1000)
    """
    contents =[  
       ('left lick', ''), 
       ('right lick', '')]


@schema
class ActionEvent(dj.Imported):
    definition = """
    -> BehaviorTrial
    action_event_id: smallint
    ---
    -> ActionEventType
    action_event_time : decimal(8,4)  # (s) from trial start
    """

# ---- Photostim trials ----

@schema
class PhotostimTrial(dj.Imported):
    definition = """
    -> SessionTrial
    """


@schema
class PhotostimPeriod(dj.Lookup):
    definition = """
    photostim_period: varchar(16)
    """

    contents = zip(['sample', 'early_delay', 'middle_delay'])


@schema
class PhotostimEvent(dj.Imported):
    definition = """
    -> PhotostimTrial
    photostim_event_id: smallint
    ---
    -> Photostim
    photostim_event_time=null: float    # (s) relative to trial start
    power=null : float                  # (mW) Maximal power 
    duration=null: Decimal(6, 2)                # (s)
    stim_spot_count=null: int           # number of laser spot of photostimulation
    -> [nullable] PhotostimPeriod 
    """


@schema
class PhotostimTrace(dj.Imported):
    definition = """
    -> SessionTrial
    ---
    aom_input_trace: longblob  # voltage input to AOM
    laser_power: longblob  # (mW) laser power delivered to tissue 
    photostim_timestamps: longblob
    """

# ----


@schema
class EventPeriod(dj.Lookup):
    definition = """  # time period between any two TrialEvent (eg the delay period is between delay and go)
    period: varchar(12)
    ---
    -> TrialEventType.proj(start_event_type='trial_event_type')
    start_time_shift: float  # (s) any time-shift amount with respect to the start_event_type
    -> TrialEventType.proj(end_event_type='trial_event_type')
    end_time_shift: float    # (s) any time-shift amount with respect to the end_event_type
    """

    contents = [('sample', 'sample', 0, 'delay', 0),
                ('delay', 'delay', 0, 'go', 0),
                ('response', 'go', 0, 'go', 1.3)]


# ============================= PROJECTS ==================================================


@schema
class Project(dj.Manual):
    definition = """
    project_name: varchar(128)
    ---
    project_desc='': varchar(1000) 
    publication='': varchar(256)  # e.g. publication doi    
    """


@schema
class ProjectSession(dj.Manual):
    definition = """
    -> Project
    -> Session
    """