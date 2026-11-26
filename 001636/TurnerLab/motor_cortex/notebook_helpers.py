"""
Helper functions for antidromic detection tutorial notebook.
"""
import numpy as np


def get_sweep_waveforms(sweep_row):
    """
    Extract neural response and stimulation waveforms from an antidromic sweep.

    Parameters
    ----------
    sweep_row : pd.Series
        A row from the AntidromicSweepsIntervals table

    Returns
    -------
    time_ms : np.ndarray
        Time axis in milliseconds (0 = stimulation onset)
    response_uv : np.ndarray
        Neural response in microvolts
    stim_ua : np.ndarray
        Stimulation current in microamperes
    """
    # Extract response data
    response_ref = sweep_row['response']
    index_start, count, response_series = response_ref
    response_uv = response_series.data[index_start:index_start + count].flatten() * response_series.conversion * 1e6

    # Extract stimulation data
    stim_ref = sweep_row['stimulation']
    index_start_s, count_s, stim_series = stim_ref
    stim_ua = stim_series.data[index_start_s:index_start_s + count_s].flatten() * stim_series.conversion * 1e6

    # Create time axis: sweeps are 50ms, centered on stimulation (t=0 at 25ms)
    sampling_rate = response_series.rate
    time_ms = (np.arange(count) / sampling_rate - 0.025) * 1000

    return time_ms, response_uv, stim_ua


def measure_response_latency(time_ms, response_uv, expected_latency, window_ms=2.0):
    """
    Measure actual response latency by finding the peak near expected latency.

    Parameters
    ----------
    time_ms : np.ndarray
        Time axis in milliseconds
    response_uv : np.ndarray
        Neural response in microvolts
    expected_latency : float
        Expected latency in ms
    window_ms : float
        Search window size (default 2.0 ms)

    Returns
    -------
    float
        Measured latency in ms, or NaN if no clear peak found
    """
    from scipy.signal import find_peaks

    mask = (time_ms >= expected_latency - window_ms) & (time_ms <= expected_latency + window_ms)
    if not mask.any():
        return np.nan

    window_response = np.abs(response_uv[mask])
    window_time = time_ms[mask]

    peaks, properties = find_peaks(window_response, height=np.percentile(window_response, 70))
    if len(peaks) == 0:
        return np.nan

    highest_peak_idx = peaks[np.argmax(properties['peak_heights'])]
    return window_time[highest_peak_idx]


def measure_response_amplitude(time_ms, response_uv, latency, window_ms=1.5):
    """
    Measure peak-to-peak amplitude near expected latency.

    Parameters
    ----------
    time_ms : np.ndarray
        Time axis in milliseconds
    response_uv : np.ndarray
        Neural response in microvolts
    latency : float
        Expected latency in ms
    window_ms : float
        Window size for amplitude measurement (default 1.5 ms)

    Returns
    -------
    float
        Peak-to-peak amplitude in microvolts
    """
    mask = (time_ms >= latency - window_ms) & (time_ms <= latency + window_ms)
    if mask.any():
        window = response_uv[mask]
        return np.max(window) - np.min(window)
    return 0


def detect_spontaneous_activity(time_ms, response_uv, critical_window_ms, threshold_std=3.0):
    """
    Detect spontaneous spike activity in the critical collision window.

    For collision to occur, a spontaneous spike must be traveling down the axon
    when the antidromic spike is traveling up. This function detects threshold
    crossings in the critical window before stimulation.

    Parameters
    ----------
    time_ms : np.ndarray
        Time axis in milliseconds (t=0 is stimulation)
    response_uv : np.ndarray
        Neural response in microvolts
    critical_window_ms : float
        Size of the critical window before stimulation (latency + refractory period)
    threshold_std : float
        Threshold for spike detection (standard deviations above baseline)

    Returns
    -------
    has_activity : bool
        Whether spontaneous activity was detected in critical window
    activity_amplitude : float
        Peak-to-peak amplitude in critical window (uV)
    spike_time : float or None
        Time of detected spike (if any), in ms
    """
    # Define baseline window (well before critical window)
    baseline_mask = (time_ms >= -20) & (time_ms <= -critical_window_ms - 2)
    # Define critical window (avoid artifact at t=0)
    critical_mask = (time_ms >= -critical_window_ms) & (time_ms < -0.5)

    # Calculate baseline statistics
    baseline_data = response_uv[baseline_mask]
    baseline_std = np.std(baseline_data)
    baseline_mean = np.mean(baseline_data)

    # Check critical window for threshold crossings
    critical_data = response_uv[critical_mask]
    critical_time = time_ms[critical_mask]

    # Peak-to-peak amplitude in critical window
    activity_amplitude = np.max(critical_data) - np.min(critical_data)

    # Detect threshold crossing
    above_threshold = np.abs(critical_data - baseline_mean) > threshold_std * baseline_std
    has_activity = np.any(above_threshold)

    spike_time = None
    if has_activity:
        # Find the time of the largest deflection
        peak_idx = np.argmax(np.abs(critical_data - baseline_mean))
        spike_time = critical_time[peak_idx]

    return has_activity, activity_amplitude, spike_time
