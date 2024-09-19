from typing import Optional

import matplotlib.pyplot
import numpy
import pynwb
import scipy.signal
import scipy.optimize

def plot_waterfall(
    *,
    segmentation_nwbfile: pynwb.NWBFile,
    exclude_labels: Optional[list] = None,
    suppress_deviations: bool = True,
    suppress_deviations_threshold: float = 40.0,
) -> None:
    """
    Recreate the waterfall similar to Fig 1d. from "Neural signal propagation atlas of Caenorhabditis elegans".

    Parameters
    ----------
    imaging_nwbfile : pynwb.NWBFile
        The NWBFile containing the imaging data.
    segmentation_nwbfile : pynwb.NWBFile
        The NWBFile containing the segmentation data.
    exclude_labels : list, optional
        A list of NeuroPAL lables to exclude from plotting.
        For example, Fig 1d from the paper (which used session "20211104-163944" of subject 26)
        excluded ["AMsoL", "AMsoR", "AMso", "AMSoL", "AMSoR", "AmSo"].
    suppress_deviations : bool, default: True
        FOr unknown reasons, about 10 traces in the figure reproduction do not match the original figure from the paper.
        If True, suppresses the plotting of lines with deviations greater than the threshold.
    suppress_deviations_threshold : float, default: 40.0
        The threshold for the deviation of a line to be suppressed.
    """
    exclude_labels = exclude_labels or []

    # Always exclude unlabelled ROIs
    excluded_labels = ["", " "] + exclude_labels

    # Actual parameters values as inferred from the fig1_commands.txt record
    savgol_filter_size = 13
    savgol_shift = (savgol_filter_size - 1) // 2
    savgol_poly = 1
    savgol_filter = scipy.signal.savgol_coeffs(savgol_filter_size, savgol_poly, pos=savgol_filter_size - 1)

    # Hardcoded parameters from the original plot function
    Delta = 5.0

    # Fetch data from NWB source
    green_signal = segmentation_nwbfile.processing["ophys"]["GreenSignals"].microscopy_response_series["GreenSignal"]
    time = green_signal.timestamps[:]

    neuropal_rois = segmentation_nwbfile.processing["ophys"]["NeuroPALSegmentations"].microscopy_plane_segmentations["NeuroPALPlaneSegmentation"]
    green_rois = segmentation_nwbfile.processing["ophys"]["PumpProbeGreenSegmentations"]

    coregistered_neuropal_id_to_green_ids = {
        int(coregistered_neuropal_id): green_id
        for coregistered_neuropal_id, green_id in zip(
            green_rois.microscopy_plane_segmentations["PumpProbeGreenPlaneSegmentation"].neuropal_ids[:],
            green_rois.microscopy_plane_segmentations["PumpProbeGreenPlaneSegmentation"].id[:],
        )
        if coregistered_neuropal_id != ""
    }

    neuropal_labels = neuropal_rois.labels.data[:]
    alphabetized_valid_neuropal_labels_with_ids = [
        (label, neuropal_id)
        for neuropal_id in numpy.argsort(neuropal_labels)[::-1]
        if (
            (label := neuropal_labels[neuropal_id]) not in excluded_labels
            and neuropal_id in coregistered_neuropal_id_to_green_ids
        )
    ]

    number_of_rois = green_signal.data.shape[1]
    max_normalized_fluorescence = numpy.zeros(shape=number_of_rois)
    all_photobleaching_coefficients = numpy.zeros(shape=(number_of_rois, 5))

    frame_vector = numpy.arange(green_signal.data.shape[0])

    for k in range(number_of_rois):
        P = numpy.array([1., 0.006, 1., 0.001, 0.2])

        data = green_signal.data[:, k]

        max_normalized_fluorescence[k] = numpy.max(data)
        Y = numpy.copy(data) / max_normalized_fluorescence[k]
        mask = numpy.ones_like(Y, dtype=bool)

        max_iterations = 100
        iteration = 0
        while iteration < max_iterations:
            R = scipy.optimize.minimize(_get_photobleach_error, P, args=(frame_vector[mask], Y[mask]))
            if numpy.sum(numpy.absolute((P - R.x) / P)) < 1e-2:
                break
            P = R.x

            std = numpy.std(_get_photobleach_fit(frame_vector=frame_vector[mask], coefficients=P) - Y[mask])
            mask[:] = numpy.absolute(_get_photobleach_fit(frame_vector=frame_vector, coefficients=P) - Y) < 2.0 * std
            iteration += 1

        all_photobleaching_coefficients[k, :] = P

    # Make plot
    fig = matplotlib.pyplot.figure(1, figsize=(12, 7))
    ax = fig.add_subplot(111)

    matplotlib.pyplot.rc("xtick", labelsize=8)

    plotted_neuropal_ids = []
    colors = []
    baseline = []
    for plot_index, (label, neuropal_id) in enumerate(alphabetized_valid_neuropal_labels_with_ids):
        green_id = coregistered_neuropal_id_to_green_ids[neuropal_id]

        roi_response = green_signal.data[:, green_id]

        # Remove spikes by replacing them with last non-spike data value
        spikes_corrected = numpy.copy(roi_response)
        mean = numpy.average(roi_response)
        std = numpy.nanstd(roi_response)

        spikes = numpy.where(roi_response - mean > std * 5)[0]
        for spike in spikes:
            spikes_corrected[spike] = roi_response[spike - 1]

        # Apply photobleaching correction
        photobleach_corrected = numpy.copy(spikes_corrected)

        scaled_photobleach_fit = _get_photobleach_fit(frame_vector=frame_vector, coefficients=all_photobleaching_coefficients[green_id, :]) * max_normalized_fluorescence[green_id]
        if numpy.any(numpy.abs(scaled_photobleach_fit) >= 1e-2):
            photobleach_corrected /= scaled_photobleach_fit
            photobleach_corrected *= scaled_photobleach_fit[0]

        localized_standard_deviation = numpy.sqrt(numpy.nanmedian(numpy.nanvar(_rolling_window(photobleach_corrected, 8), axis=-1)))

        # Smooth using Savitzky-Golay filter
        smoothed = numpy.copy(photobleach_corrected)
        smoothed[savgol_shift:] = numpy.convolve(smoothed, savgol_filter, mode="same")[:-savgol_shift]

        # Scale by localized standard deviation and clip filter window out
        smoothed /= localized_standard_deviation
        smoothed[:savgol_filter_size] = numpy.nan

        # Numerous lines were excluded to match the Nature paper as closely as possible.
        # In particular, the "M5", "AWAR", "RIMR", and "I3" traces all had massive deviations
        # from the figure in the paper that were not smoothed by any of the previous steps
        # (spike removal, photobleaching correction, or Savitzky-Golay filtering).
        smoothed_deviations = max(smoothed[13:]) - min(smoothed[13:])
        if suppress_deviations is True and smoothed_deviations > suppress_deviations_threshold:
            line, = ax.plot([], [], lw=0.8)  # Still plotting an empty line to increment coloration to match

            color = line.get_color()
            colors.append(color)
            continue

        # There are a few other lines in the plot that don't precisely match the figure from the paper
        # but this is assumed to just be subtle differences in the filtering steps above, or possibly
        # post-hoc label corrections that weren't saved back to the source data

        # Add artificial visual shift to stagger lines
        DD = plot_index * Delta - numpy.median(numpy.sort(smoothed)[:100])

        plotted_neuropal_ids.append(neuropal_id)
        baseline.append(DD)

        plot = smoothed + DD
        line, = ax.plot(time[13:], plot[13:], lw=0.8)

        color = line.get_color()
        colors.append(color)

        ax.annotate(label, (-150 - 120 * (plot_index % 2), plot_index * Delta), c=color, fontsize=8)

    ax.set_xlim(-270, time[-1])
    ax.set_ylim(-Delta, Delta * (plot_index + 6))
    ax.set_yticks([])
    ax.set_xlabel("Time (s)", fontsize=10)
    ax.set_ylabel("Responding neuron", fontsize=10)

    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)

    return None


def _get_photobleach_fit(frame_vector: numpy.ndarray, coefficients: numpy.ndarray) -> numpy.ndarray:
    """
    Adapted from
    https://github.com/leiferlab/wormdatamodel/blob/2ab956199e3931de41a190d2b9985e961df3810c/wormdatamodel/signal/signal.py#L748C21-L748C24
    """
    photobleach_fit = coefficients[0] * numpy.exp(-frame_vector * numpy.abs(coefficients[1]))
    photobleach_fit += coefficients[2] * numpy.exp(-frame_vector * numpy.abs(coefficients[3]))
    photobleach_fit += numpy.abs(coefficients[-1])
    return photobleach_fit


def _get_photobleach_error(coefficients:  numpy.ndarray, frame_vector: numpy.ndarray, Y) -> float:
    """
    Adapted from
    https://github.com/leiferlab/wormdatamodel/blob/2ab956199e3931de41a190d2b9985e961df3810c/wormdatamodel/signal/signal.py#L754C1-L756C41
    """
    error = numpy.sum(numpy.power(_get_photobleach_fit(frame_vector=frame_vector, coefficients=coefficients) - Y, 2))
    return error


def _rolling_window(a, window) -> numpy.ndarray:
    pad = numpy.ones(len(a.shape), dtype=numpy.int32)
    pad[-1] = window - 1
    pad = list(zip(pad, numpy.zeros(len(a.shape), dtype=numpy.int32)))
    a = numpy.pad(a, pad, mode='reflect')
    shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
    strides = a.strides + (a.strides[-1],)
    return numpy.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)
