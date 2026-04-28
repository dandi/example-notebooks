"""
Visualize trial temporal structure as a stacked horizontal bar chart.

Each row represents a trial, with colored segments showing the different phases:
- Baseline (start to center target appearance)
- Center hold (center target to lateral target appearance / go cue)
- Time to react (go cue to cursor departure from center zone)
- Movement (cursor departure to derived movement end)
- Target hold (movement end to reward)
- Post-reward (reward to stop)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# Shared color scheme for trial phases
PHASE_COLORS = {
    'baseline': '#E8E8E8',        # Light gray - pre-task
    'center_hold': '#4ECDC4',      # Teal - holding at center
    'reaction_time': '#FFE66D',    # Yellow - planning/reaction
    'movement': '#FF6B6B',         # Coral/red - movement execution
    'target_hold': '#9B59B6',      # Purple - holding at target
    'post_reward': '#87CEEB',      # Sky blue - post-reward
}


def plot_trial_structure(trials_df, ax=None, max_trials=None):
    """
    Plot trial temporal structure as horizontal stacked bars.

    Shows all trial phases from baseline through post-reward, giving an overview
    of the complete trial timing structure.

    Parameters
    ----------
    trials_df : pd.DataFrame
        DataFrame from nwbfile.trials.to_dataframe()
    ax : matplotlib.axes.Axes, optional
        Axes to plot on. If None, creates new figure.
    max_trials : int, optional
        Maximum number of trials to display. If None, shows all.

    Returns
    -------
    fig, ax : tuple
        Figure and axes objects
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 8))
    else:
        fig = ax.figure

    # Limit trials if requested
    if max_trials is not None:
        trials_df = trials_df.head(max_trials)

    n_trials = len(trials_df)

    for idx, (trial_idx, trial) in enumerate(trials_df.iterrows()):
        y = n_trials - idx - 1  # Flip so trial 0 is at top

        # Get times relative to trial start
        t_start = 0
        t_center = trial['center_target_appearance_time'] - trial['start_time']
        t_lateral = trial['lateral_target_appearance_time'] - trial['start_time']
        t_departure = trial['cursor_departure_time'] - trial['start_time']
        t_move_end = trial['derived_movement_end_time'] - trial['start_time']
        t_reward = trial['reward_time'] - trial['start_time']
        t_stop = trial['stop_time'] - trial['start_time']

        # Check for aborted trials (missing go cue or reward)
        if np.isnan(t_lateral) or np.isnan(t_reward):
            ax.barh(y, t_center - t_start, left=t_start, height=0.8,
                    color=PHASE_COLORS['baseline'], edgecolor='none')
            ax.barh(y, t_stop - t_center, left=t_center, height=0.8,
                    color=PHASE_COLORS['center_hold'], edgecolor='none', alpha=0.5)
            ax.text(t_stop + 0.1, y, 'Aborted',
                    va='center', ha='left', fontsize=8, fontstyle='italic',
                    color='gray')
            continue

        # Baseline (start to center target)
        ax.barh(y, t_center - t_start, left=t_start, height=0.8,
                color=PHASE_COLORS['baseline'], edgecolor='none')

        # Center hold (center target to lateral target / go cue)
        ax.barh(y, t_lateral - t_center, left=t_center, height=0.8,
                color=PHASE_COLORS['center_hold'], edgecolor='none')

        # Reaction time (go cue to cursor departure)
        ax.barh(y, t_departure - t_lateral, left=t_lateral, height=0.8,
                color=PHASE_COLORS['reaction_time'], edgecolor='none')

        # Handle trials with missing kinematic data
        has_kinematics = not np.isnan(t_move_end)

        if not has_kinematics:
            # No kinematic data - show movement as cursor departure to reward
            ax.barh(y, t_reward - t_departure, left=t_departure, height=0.8,
                    color=PHASE_COLORS['movement'], edgecolor='none')
        else:
            # Movement execution (cursor departure to movement end)
            ax.barh(y, t_move_end - t_departure, left=t_departure, height=0.8,
                    color=PHASE_COLORS['movement'], edgecolor='none')

            # Target hold (movement end to reward)
            ax.barh(y, t_reward - t_move_end, left=t_move_end, height=0.8,
                    color=PHASE_COLORS['target_hold'], edgecolor='none')

        # Post-reward (reward to stop)
        ax.barh(y, t_stop - t_reward, left=t_reward, height=0.8,
                color=PHASE_COLORS['post_reward'], edgecolor='none')

        # Add movement type label at the end
        movement_type = trial['movement_type']
        ax.text(t_stop + 0.1, y, movement_type.capitalize(),
                va='center', ha='left', fontsize=8, fontweight='bold',
                color='black')

    # Create legend
    legend_patches = [
        mpatches.Patch(color=PHASE_COLORS['baseline'], label='Baseline'),
        mpatches.Patch(color=PHASE_COLORS['center_hold'], label='Holding at Center'),
        mpatches.Patch(color=PHASE_COLORS['reaction_time'], label='Time to React'),
        mpatches.Patch(color=PHASE_COLORS['movement'], label='Movement'),
        mpatches.Patch(color=PHASE_COLORS['target_hold'], label='Holding at Target'),
        mpatches.Patch(color=PHASE_COLORS['post_reward'], label='Post-Reward'),
    ]

    ax.legend(handles=legend_patches, loc='upper right', fontsize=9)

    # Labels and formatting
    ax.set_xlabel('Time relative to trial start (seconds)', fontsize=11)
    ax.set_ylabel('Trial', fontsize=11)
    ax.set_title('Trial Temporal Structure', fontsize=13, fontweight='bold')

    # Set y-axis ticks
    ax.set_yticks(np.arange(0, n_trials, max(1, n_trials // 10)))
    ax.set_yticklabels([str(n_trials - 1 - t) for t in ax.get_yticks().astype(int)])

    ax.set_ylim(-0.5, n_trials - 0.5)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    return fig, ax


def plot_movement_kinematics(trials_df, ax=None, max_trials=None):
    """
    Plot movement phase with kinematic event markers.

    Focuses on the movement-related phases (Time to React, Movement, Holding at Target)
    and overlays derived kinematic markers: movement onset, peak velocity, and movement end.

    Parameters
    ----------
    trials_df : pd.DataFrame
        DataFrame from nwbfile.trials.to_dataframe()
    ax : matplotlib.axes.Axes, optional
        Axes to plot on. If None, creates new figure.
    max_trials : int, optional
        Maximum number of trials to display. If None, shows all.

    Returns
    -------
    fig, ax : tuple
        Figure and axes objects
    """
    from matplotlib.lines import Line2D

    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 8))
    else:
        fig = ax.figure

    # Limit trials if requested
    if max_trials is not None:
        trials_df = trials_df.head(max_trials)

    # Filter to only complete trials with kinematic data
    complete_trials = trials_df.dropna(subset=['derived_movement_end_time'])
    n_trials = len(complete_trials)

    if n_trials == 0:
        ax.text(0.5, 0.5, 'No trials with complete kinematic data',
                ha='center', va='center', transform=ax.transAxes)
        return fig, ax

    for idx, (trial_idx, trial) in enumerate(complete_trials.iterrows()):
        y = n_trials - idx - 1  # Flip so trial 0 is at top

        # Get times relative to go cue (lateral target appearance)
        t_lateral = trial['lateral_target_appearance_time']
        t_departure = trial['cursor_departure_time'] - t_lateral
        t_move_onset = trial['derived_movement_onset_time'] - t_lateral
        t_peak_vel = trial['derived_peak_velocity_time'] - t_lateral
        t_move_end = trial['derived_movement_end_time'] - t_lateral
        t_reward = trial['reward_time'] - t_lateral

        # Reaction time (go cue to cursor departure)
        ax.barh(y, t_departure, left=0, height=0.8,
                color=PHASE_COLORS['reaction_time'], edgecolor='none')

        # Movement (cursor departure to movement end)
        ax.barh(y, t_move_end - t_departure, left=t_departure, height=0.8,
                color=PHASE_COLORS['movement'], edgecolor='none')

        # Target hold (movement end to reward)
        ax.barh(y, t_reward - t_move_end, left=t_move_end, height=0.8,
                color=PHASE_COLORS['target_hold'], edgecolor='none')

        # Add kinematic markers
        marker_y = y

        # Movement onset marker (|)
        if not np.isnan(t_move_onset):
            ax.plot([t_move_onset, t_move_onset], [marker_y - 0.4, marker_y + 0.4],
                    color='black', linewidth=1.5, zorder=5)

        # Peak velocity marker (*)
        if not np.isnan(t_peak_vel):
            ax.plot(t_peak_vel, marker_y, marker='*', color='black',
                    markersize=8, zorder=5)

        # Movement end marker (|)
        if not np.isnan(t_move_end):
            ax.plot([t_move_end, t_move_end], [marker_y - 0.4, marker_y + 0.4],
                    color='black', linewidth=1.5, zorder=5)

        # Add movement type label at the end
        movement_type = trial['movement_type']
        ax.text(t_reward + 0.05, y, movement_type.capitalize(),
                va='center', ha='left', fontsize=8, fontweight='bold',
                color='black')

    # Create legend
    legend_patches = [
        mpatches.Patch(color=PHASE_COLORS['reaction_time'], label='Time to React'),
        mpatches.Patch(color=PHASE_COLORS['movement'], label='Movement'),
        mpatches.Patch(color=PHASE_COLORS['target_hold'], label='Holding at Target'),
        Line2D([0], [0], color='black', linewidth=1.5, label='Movement onset/end'),
        Line2D([0], [0], marker='*', color='black', linestyle='None',
               markersize=8, label='Peak velocity'),
    ]

    ax.legend(handles=legend_patches, loc='upper right', fontsize=9)

    # Labels and formatting
    ax.set_xlabel('Time relative to go cue (seconds)', fontsize=11)
    ax.set_ylabel('Trial', fontsize=11)
    ax.set_title('Movement Kinematics', fontsize=13, fontweight='bold')

    # Set y-axis ticks
    ax.set_yticks(np.arange(0, n_trials, max(1, n_trials // 10)))
    ax.set_yticklabels([str(n_trials - 1 - t) for t in ax.get_yticks().astype(int)])

    ax.set_ylim(-0.5, n_trials - 0.5)
    ax.axvline(0, color='gray', linestyle='--', alpha=0.5, label='Go cue')
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    return fig, ax
