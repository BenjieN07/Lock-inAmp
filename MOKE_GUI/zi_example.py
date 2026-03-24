# -*- coding: utf-8 -*-
#THE REAL EXAMPLE IS IN FOUND IN THIS PATH:
#C:\Users\MOKE\AppData\Local\Programs\Python\Python36\Lib\site-packages\zhinst\examples\common\example_data_acquisition_continuous.py
#
#THIS EXAMPLE HAS BEEN MODIFIED TO SHOW 3 DEMODULATOR SIGNALS AND STORE DATA IN LISTS

"""
Zurich Instruments LabOne Python API Example

Python API Example for the Data Acquisition Module. This example demonstrates
how to record data from an instrument continuously (without triggering).

Note: This example does not perform any device configuration. If the streaming
nodes corresponding to the signal_paths are not enabled, no data will be
recorded.
"""

# Copyright 2018 Zurich Instruments AG

import time
import numpy as np
import zhinst.ziPython as ziPython

time_data = [[],[],[]]
value_data = [[],[],[]]

def run_example(device_id, do_plot=False):
    """
    Run the example: Record data continuously in 0.2 s chunks for 5 seconds
    using the Data Acquisition Module.

    Arguments:

      device_id (str): The ID of the device to run the example with. For
        example, `dev2006` or `uhf-dev2006`.

      do_plot (bool, optional): Specify whether to plot the recorded
        data. Default is no plot output.

    Returns:

      data (dict): A dictionary whose keys are the subscribed signal paths. Each
        value is a list which contains all the signal bursts for the signal path
        as returned by the Data Acquisition Module's read() function. Note: Do
        not increase TOTAL_DURATION without removing this continuous save.

    Raises:

      RuntimeError: If the device is not "discoverable" from the API.

    See the "LabOne Programing Manual" for further help, available:
      - On Windows via the Start-Menu:
        Programs -> Zurich Instruments -> Documentation
      - On Linux in the LabOne .tar.gz archive in the "Documentation"
        sub-folder.
    """

    api_level = 6  # The API level supported by this example.
    # Call a zhinst utility function that returns:
    # - an API session `daq` in order to communicate with devices via the data server.
    # - the device ID string that specifies the device branch in the server's node hierarchy.
    # - the device's discovery properties.
    daq = ziPython.ziDAQServer('192.168.1.10',8004,api_level)
#    zhinst.utils.api_server_version_check(daq)

    # The list of signal paths that we would like to record in the module.
#    demod_path = '/{}/demods/0/sample'.format(device_id)
    signal_paths = []
    for i in range(3):
        signal_paths.append('/{}/demods/{}/sample.x'.format(device_id, i))
#    signal_paths.append(demod_path + '.x')  # The demodulator X output.
#    signal_paths.append(demod_path + '.y')  # The demodulator Y output.
    # It's also possible to add signals from other node paths:
    # signal_paths.append('/%s/demods/1/sample.r' % (device))


    # Defined the total time we would like to record data for and its sampling rate.
    # Defined the total time we would like to record data for and its sampling rate.
    # total_duration: Time in seconds: This examples stores all the acquired data in the `data` dict - remove this
    # continuous storing in read_data_update_plot before increasing the size of total_duration!

    module_sampling_rate = 600  # Number of points/second
    burst_duration = 0.2  # Time in seconds for each data burst/segment.
    num_cols = int(np.ceil(module_sampling_rate*burst_duration)) 

    # Create an instance of the Data Acquisition Module.
    h = daq.dataAcquisitionModule()

    # Configure the Data Acquisition Module.
    # Set the device that will be used for the trigger - this parameter must be set.
    h.set("dataAcquisitionModule/device", device_id)

    # Specify continuous acquisition (type=0).
    h.set("dataAcquisitionModule/type", 0)

    # 'dataAcquisitionModule/grid/mode' - Specify the interpolation method of
    #   the returned data samples.
    #
    # 1 = Nearest. If the interval between samples on the grid does not match
    #     the interval between samples sent from the device exactly, the nearest
    #     sample (in time) is taken.
    #
    # 2 = Linear interpolation. If the interval between samples on the grid does
    #     not match the interval between samples sent from the device exactly,
    #     linear interpolation is performed between the two neighbouring
    #     samples.
    #
    # 4 = Exact. The subscribed signal with the highest sampling rate (as sent
    #     from the device) defines the interval between samples on the DAQ
    #     Module's grid. If multiple signals are subscribed, these are
    #     interpolated onto the grid (defined by the signal with the highest
    #     rate, "highest_rate"). In this mode, dataAcquisitionModule/duration is
    #     read-only and is defined as num_cols/highest_rate.
    h.set("dataAcquisitionModule/grid/mode", 2)
    # 'dataAcquisitionModule/count' - Specify the number of bursts of data the
    #   module should return (if dataAcquisitionModule/endless=0). The
    #   total duration of data returned by the module will be
    #   dataAcquisitionModule/count*dataAcquisitionModule/duration.
    h.set("dataAcquisitionModule/endless", 1)
    # 'dataAcquisitionModule/duration' - Burst duration in seconds.
    #   If the data is interpolated linearly or using nearest neighbout, specify
    #   the duration of each burst of data that is returned by the DAQ Module.
    h.set("dataAcquisitionModule/duration", burst_duration)
    # 'dataAcquisitionModule/grid/cols' - The number of points within each duration.
    #   This parameter specifies the number of points to return within each
    #   burst (dataAcquisitionModule/duration seconds worth of data) that is
    #   returned by the DAQ Module.
    h.set("dataAcquisitionModule/grid/cols", num_cols)

    data = {}
    # A dictionary to store all the acquired data.
    for signal_path in signal_paths:
        print("Subscribing to", signal_path)
        h.subscribe(signal_path)
        data[signal_path] = []

    clockbase = daq.getInt("/{}/clockbase".format(device_id))
    if do_plot:
        import matplotlib.pyplot as plt
        fig = plt.figure(1)
#        fig.clf()
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)
        global axes
        axes = [ax1, ax2, ax3]
#        plt.xlabel('Time ($s$)')
#        plt.ylabel('Subscribed signals')
#        plt.xlim([0, total_duration])
#        plt.ion()

    ts0 = np.nan
#    read_count = 0
    

    def read_data_update_plot(data, timestamp0):
        """
        Read the acquired data out from the module and plot it. Raise an
        AssertionError if no data is returned.
        """
        data_read = h.read(True)
        returned_signal_paths = [signal_path.lower() for signal_path in data_read.keys()]
        progress = h.progress()[0]
        # Loop over all the subscribed signals:
        i = 0
        
        for signal_path in signal_paths:
            if signal_path.lower() in returned_signal_paths:
                # Loop over all the bursts for the subscribed signal. More than
                # one burst may be returned at a time, in particular if we call
                # read() less frequently than the burst_duration.
                for index, signal_burst in enumerate(data_read[signal_path.lower()]):
                    if np.any(np.isnan(timestamp0)):
                        # Set our first timestamp to the first timestamp we obtain.
                        timestamp0 = signal_burst['timestamp'][0, 0]
                    # Convert from device ticks to time in seconds.
                    t = (signal_burst['timestamp'][0, :] - timestamp0)/clockbase
                    value = signal_burst['value'][0, :]
                    
                    
#                    print(t)
#                    print(value)
                    global time_data
                    global value_data
                    time_data[i] = np.append(time_data[i], t)
                    value_data[i] = np.append(value_data[i], value)
#                    print(i)
#                    print(signal_path)
#                    print(time_data[i])
#                    print(value_data[i])
                    if do_plot:
#                        print('plot')
#                        fig.clf()
                        global axes
                        axes[i].clear()
                        axes[i].plot(time_data[i][-3000:], value_data[i][-3000:])
#                    num_samples = len(signal_burst['value'][0, :])
#                    dt = (signal_burst['timestamp'][0, -1] - signal_burst['timestamp'][0, 0])/clockbase
                    data[signal_path].append(signal_burst)
#                    print("Read: ", read_count, ", progress: {0:.2f}%".format(100*progress), ". Burst ", index, ": ",
#                          signal_path, " contains ", num_samples, " spanning {0:.2f} s.".format(dt), sep="")
            else:
                # Note: If we read before the next burst has finished, there may be no new data.
                # No action required.
                pass
            
            i += 1

        # Update the plot.
        if do_plot:
#            plt.title("Progress of data acquisition: {0:.2f}%.".format(100*progress))
            plt.pause(0.01)
            fig.canvas.draw()
        return data, timestamp0

    # Start recording data.
    h.execute()

    # Record data in a loop with timeout.
#    timeout = 1.5*total_duration
#    t0_measurement = time.time()
    # The maximum time to wait before reading out new data.
#    t_update = 0.9*burst_duration
    while True:
        time.sleep(1)
#        t0_loop = time.time()
#        if time.time() - t0_measurement > timeout:
#            raise Exception("Timeout after {} s - recording not complete. Are the streaming nodes enabled? "
#                            "Has a valid signal_path been specified?".format(timeout))
        data, ts0 = read_data_update_plot(data, ts0)
#        read_count += 1
        # We don't need to update too quickly.
#        time.sleep(max(0, t_update - (time.time() - t0_loop)))

    # There may be new data between the last read() and calling finished().
#    data, _ = read_data_update_plot(data, ts0)

    if not do_plot:
        print("Please run with `do_plot=True` to see dynamic plotting of the acquired signals.")

#    return data


run_example('dev3436', do_plot=True)