# sampling a sine wave programmatically
import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
# !/usr/bin/env python
# Implementation of algorithm from https://stackoverflow.com/a/22640362/6029703
import os
from matplotlib.backends.backend_pdf import PdfPages
import datetime

# -*- coding: utf-8 -*-
"""
Created on Wed Nov 14 15:19:40 2018

@author: elind
"""
import os
import wave
import contextlib
import numpy as np


def make_compilation(directories, outfile, ext='.wav'):
    """
    directories: list of directories that contain all of the files you want to join
    outfile:
    """

    event_dict = {0: 'nothing',
                  2: 'car_crash',
                  1: 'crash',
                  3: 'train',
                  4: 'car passing',
                  5: 'plane flying',
                  9: 'miscellaneous'}

    infiles = []
    event_times = []
    event_ids = []
    files = []
    durations = []

    for dir_string in directories:
        directory = os.fsencode(dir_string)
        for file in os.listdir(directory):
            filename = os.fsdecode(file)

            if filename.endswith(ext):
                infile = os.path.join(dir_string, filename)
                infiles += infile
                event_info = filename.replace(ext, '').replace('b', '').strip()
                event_time = event_info.split(' at ')[-1]
                event_time = event_time.split('-')
                event_times += [float(event_time[0]) * 60 + float(event_time[1])]
                files += [filename]

                # get duration of files
                with contextlib.closing(wave.open(infile, 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    duration = frames / float(rate)
                    durations += [duration]

                # classify each .wav by event
                for keycode in event_dict:
                    if event_dict[keycode] in event_info:
                        event_ids += [keycode]
                        break
                    else:
                        pass

            else:
                continue

    # create array for event times with ending value of 0
    event_times = np.array(event_times + [0])
    # create cumulative sum of durations to add to event_times with first value 0
    durations_cum_sum = np.cumsum([0] + durations)
    # create cumulative sum of event times to identify time in compilation
    # without last value
    event_times_cum_sum = (event_times + durations_cum_sum)[:-1]

    print(durations_cum_sum[-1])

    return event_ids, event_times_cum_sum, files


def peak_detect(x, t, lag, threshold, influence):
    '''
    iterative smoothed z-score algorithm
    Implementation of algorithm from https://stackoverflow.com/a/22640362/6029703
    '''
    import numpy as np
    labels = np.zeros(len(x))
    filtered_y = np.array(x)
    avg_filter = np.zeros(len(x))
    std_filter = np.zeros(len(x))
    var_filter = np.zeros(len(x))
    crashes = []

    avg_filter[lag - 1] = np.mean(x[0:lag])
    std_filter[lag - 1] = np.std(x[0:lag])
    var_filter[lag - 1] = np.var(x[0:lag])
    for i in range(lag, len(x)):
        if abs(x[i] - avg_filter[i - 1]) > threshold * std_filter[i - 1]:
            if x[i] > avg_filter[i - 1]:
                labels[i] = 1
                if not 1 in labels[int(i - (5 / t)):i]:
                    crashes += [i]
            else:
                labels[i] = 0
            filtered_y[i] = influence * x[i] + (1 - influence) * filtered_y[i - 1]
        else:
            labels[i] = 0
            filtered_y[i] = x[i]
        # update avg, var, std
        avg_filter[i] = avg_filter[i - 1] + 1. / lag * (filtered_y[i] - filtered_y[i - lag])
        var_filter[i] = var_filter[i - 1] + 1. / lag * ((filtered_y[i] - avg_filter[i - 1]) ** 2 - (
                filtered_y[i - lag] - avg_filter[i - 1]) ** 2 - (filtered_y[i] - filtered_y[i - lag]) ** 2 / lag)
        std_filter[i] = np.sqrt(var_filter[i])

    return dict(signals=labels,
                avgFilter=avg_filter,
                stdFilter=std_filter,
                crashes=crashes)


def detect_peak(file_name, t=0.1, start_t=0, lag=30, threshold=6,
                influence=0.5, print_pdf=None, tick_dist=60.0):
    fs, data = wavfile.read(file_name)
    try:
        data = (np.delete(data, (1), axis=1)).transpose()[0]  # delete second channel
    except:
        pass
        # print("Error processing multiple audio channels")

    x_time = int(fs * start_t)
    """
    convert start time (s) to x scale time 
    e.g. if the frequency rate is 44100Hz: x_time = 4410 would correspond to the data point at data[4410]
    x_time = 88200 also represents time = 2 seconds in real time
    """
    N = int(fs * t)  # total points in chunk

    total_time = len(data) / fs  # total time in seconds
    curr_time = 0.0  # temporary value for loop (s)
    energies = []  # normal array to store squared sum of each 1 sec chunk

    # loop through entire data set (not in real time)
    # every .1 seconds, square and sum amplitudes in clip chunk
    while curr_time < total_time:
        clip = data[x_time:x_time + N]
        energies.append(np.sum(np.square(clip, dtype='int64')))
        x_time += N
        curr_time += t

    energy_times = np.arange(len(energies)) * t  # prepare x values for energies array

    crash_id = file_name.split('/')[-1].replace('.wav', '')
    crash_id = crash_id.split('\\')[-1]

    fig, [ax1, ax2, ax3, ax4] = plt.subplots(4, 1, sharex=True)

    fig.suptitle(crash_id)
    ax1.plot(energy_times, energies, color='k', linewidth="0.5")
    ax4.set_xlabel('Time (s)')
    ax4.set_xticks(np.arange(min(energy_times), max(energy_times) + 1, tick_dist))
    ax3.set_xlim(0, len(energies) * t)

    ax1.set_ylabel('Energy')
    ax1.set_yticks([])
    ax2.set_ylabel('Threshold')
    ax2.set_yticks([])
    ax3.set_ylabel('Detection')
    ax3.set_yticks([])
    ax4.set_ylabel('Z-score')
    ax4.set_yticks(np.arange(0, 13, 2))
    ax4.set_ylim(0, 12)

    # Run algo with settings from above
    result = peak_detect(energies,
                         t=t,
                         lag=lag,
                         threshold=threshold,
                         influence=influence)

    ax2.plot(energy_times, energies)
    ax2.plot(np.arange(lag, len(energies)) * t,
             result["avgFilter"][lag:], color="cyan", lw=2)
    ax2.plot(np.arange(lag, len(energies)) * t,
             result["avgFilter"][lag:] + threshold * result["stdFilter"][lag:],
             color="green", lw=2)
    ax3.step(np.arange(lag, len(energies)) * t,
             result["signals"][lag:],
             color="red",
             lw=2)
    ax4.plot(np.arange(lag, len(energies)) * t,
             (energies[lag:] - result["avgFilter"][lag:]) / result["stdFilter"][lag:],
             color='cyan',
             lw=3)

    if print_pdf != None:
        print_pdf.savefig()  # save to pdf
        plt.close(fig)  # do not display figures
        pp.close()  # close pdf

    crashes = result['crashes']
    crashes_secs = list(map(lambda x: np.round(x * t, 2), crashes))

    crash_times_mins = list(map(lambda x: str(datetime.timedelta(seconds=round(x))),
                                crashes_secs))
    return data, crashes, crashes_secs, crash_times_mins, N, fs


def make_fft(N, fs, crash, data, print_pdf=None):
    # for future reference
    # https://stackoverflow.com/questions/31120043/python-creating-multiple-plots-in-one-figure-with-for-loop

    clip = data[crash:crash+N]
    Y_k = np.fft.fft(clip)[0:int(N / 2)] / N  # FFT function from numpy
    Y_k[1:] = 2 * Y_k[1:]  # need to take the single-sided spectrum only
    Pxx = np.abs(Y_k)  # be sure to get rid of imaginary part
    f = fs * np.arange((N / 2)) / N  # frequency vector

    fig, ax1 = plt.subplots()
    ax1.plot(f, Pxx, color='k', linewidth="0.5")
    ax1.set_ylabel('Amplitude')
    ax1.set_xlabel('Frequency [Hz]')
    ax1.set_title(str(crash*N/fs))

    if print_pdf != None:
        print_pdf.savefig()  # save to pdf
        plt.close(fig)  # do not display figures


if __name__ == "__main__":
    t = 0.1
    lag = 1500
    threshold = 6
    influence = 0.75

    pdf_name = '../Data/compilation_threshold_graphs.pdf'
    pp = PdfPages(pdf_name)

    data, crashes, crashes_secs, crash_times_mins, N, fs = detect_peak(
        "C://Users/edj9/Box/11Foot8/Data/Compilations/full_crash_compilation.wav",
        t=t,
        lag=lag,
        threshold=threshold,
        influence=influence,
        print_pdf=pp,
        tick_dist=2400.0)

    fft_pdf_name = '../Data/fft_graphs.pdf'
    pp_fft = PdfPages(fft_pdf_name)
    for crash in crashes:
        make_fft(N,
                 fs,
                 crash,
                 data,
                 print_pdf=pp_fft)
    pp_fft.close()

    """print('Potential crashes at windows:')
    print(result['crashes'])"""
    print('Potential crashes at times:')
    print(crash_times_mins)
    print('Potential crashes at times (in secs):')
    print(crashes_secs)

    """ #iterate over files in a directory
        pdf_name='../Data/threshold_graphs.pdf'
        pp = PdfPages(pdf_name)

        directories = ["C://Users/edj9/Box/11Foot8/Data/Full_Crashes/Audio",
                       "C://Users/edj9/Box/11Foot8/Data/Trains/Audio"]
        for dir_string in directories:
            directory = os.fsencode(dir_string)
            for file in os.listdir(directory):
                filename = os.fsdecode(file)
                if filename.endswith(".wav"):
                    detect_peak(os.path.join(dir_string, filename),
                            t=t,
                            lag=lag,
                            threshold=threshold,
                            influence=influence,
                            print_pdf=pp)
                    continue
                else:
                    continue
        """  # Close PDF
    # create compilation and return statistics
    directories = ["C://Users/edj9/Box/11Foot8/Data/Full_Crashes/Audio",
                   "C://Users/edj9/Box/11Foot8/Data/Trains/Audio"]
    output = "C:/Users/edj9/Box/11Foot8/Data/Compilations/full_crash_compilation.wav"
    ext = '.wav'
    event_ids, event_times_cum_sum, files = make_compilation(directories, output, ext)
