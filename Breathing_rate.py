import IPython.display
import wave
import numpy as np
from scipy.signal import butter, lfilter, freqz
import matplotlib.pyplot as plt
import numpy as np
import scipy.io.wavfile
from pydub import AudioSegment


class Breathing_rate:
    """
    This class was created in order to measure the breathing rate from a given audio file.
    """

    def __init__(self, audio_path: str):
        """

        Parameters
        ----------
        audio_path : str
            The path of the audio file
        """
        self._read_audio(audio_path)

    def _read_audio(self, path: str):
        """
        Tries to read an audio file stored in the path and calculates the properties original_rate,
        audio and audio duration]

        Parameters
        ----------
        path : str
            The path of the audio file
        """
        try:
            extension = path.split('.')[-1]
            sound = AudioSegment.from_file(path)
            self.audio = np.array(sound.get_array_of_samples())
            self.original_rate = sound.frame_rate
            if len(self.audio.shape) != 1:
                self.audio = self.audio[:, 0]

            self.audio_duration = len(self.audio) / self.original_rate

        except Exception as e:
            print('please insert a valid audio file')
            print(e)
            raise ValueError('please insert a valid audio file')

    def get_breathing_rate(self, method: str = 'abs', filter_name: str = 'lowpass',
                           parameter=1.2, get_rate_method='count') -> dict:
        """
        It first preprocesseses the self.audio signal, to get the self.preprocessed_signal, then applies
        the method provided in filter name to the signal and finally gets the breathing rate according to the
        method provided in the get_rate_method parameter.

        Parameters
        ----------
        method : str, optional
            The method to transform the signal. It could be 'abs' abs() or 'logabs' log(abs()) depending on the preferences, by default 'abs'
        filter_name : str, optional
            The name of the filter to apply to the signal, it could be 'lowpass', 'moving_average' or 'None' , by default 'lowpass'
        parameter : float, optional
            The parameter of the preprocessing filter depending on the filter_name it could be the lowpass cutoff frecuency or the 'n' for
             the moving average, by default 1.2
        get_rate_method : str, optional
            The respiration rate can be obtained either by counting the peaks in the preprocessed signal 'count' or by frecuency corresponding
            to the peak of the power spectral density 'PSD' , by default 'count'

        Returns
        -------
        dict
            The key of the dict is the rate and the value is the breathing rate obtained using the methods provided to the function
        """

        self.preprocessed_signal = self._preprocessing(method=method,
                                                       filter_name=filter_name,
                                                       parameter=parameter)

        if get_rate_method == 'count':
            self.n_exhalations, self.n_inhalations, status = self._count_respiration()
            rate = self.n_exhalations / self.audio_duration

        elif get_rate_method == 'PSD':
            freqs, psd = scipy.signal.welch(self.preprocessed_signal, fs=self.preprocessing_rate)
            idx_max = np.argmax(psd)
            rate = freqs[idx_max]

            # psd can't be verified
            status = True
        else:
            raise ValueError('invalid get_rate_method')

        rate *= 60
        if rate > 150 or rate < 2:
            status = False

        if self.audio_duration < 3:
            status = False

        return {'rate': rate, 'status': status}

    def _preprocessing(self, method, filter_name, parameter):
        """
        Method to preprocess the audio file.

        Parameters
        ----------
        method :
            The method to transform the signal. It could be 'abs' abs() or 'logabs' log(abs()) depending on the preferences, by default 'abs'
        filter_name :
            The name of the filter to apply to the signal, it could be 'lowpass', 'moving_average' or 'None' , by default 'lowpass'
        parameter :
            The parameter of the preprocessing filter depending on the filter_name it could be the lowpass cutoff frecuency or the 'n' for the
            moving average,

        Returns
        -------
        [type]
            The audio after applying preprocessing
        """

        if method == 'abs':
            data_abs = abs(self.audio)
        elif method == 'logabs':
            data_abs = abs(self.audio)
            data_abs = 1000 * np.log10(data_abs + 1)
        else:
            raise ValueError('invalid method')

        self.preprocessing_rate = 3.3
        subsampled_data = self._subsample_audio(data_abs, self.original_rate,
                                                self.preprocessing_rate)

        if filter_name == 'lowpass':
            # Filter requirements.
            order = 6
            fs = self.preprocessing_rate
            cutoff = parameter  # desired cutoff frequency of the filter, Hz
            filtered_audio = self._butter_lowpass_filter(subsampled_data, cutoff, fs, order)

        elif filter_name == 'moving_average':
            moving_average_n = parameter
            filtered_audio = np.convolve(subsampled_data,
                                         np.ones((moving_average_n,)) / moving_average_n,
                                         mode='same')

        elif filter_name == 'None':
            filtered_audio = subsampled_data

        else:
            raise ValueError('invalid filter_name')

        return filtered_audio

    def _count_respiration(self):
        """
        This functions gets the number of times the preprocessed_signal
        crosses its mean value either going up (exhalation) or down (inhalation)

        Returns
        -------
        tuple
            first value is the number of exhalations (crossing-up lines) and the second is the number of
            inhalations (crossing-down lines)
        """

        indices_crosses_up = []
        indices_crosses_down = []
        start = False
        greater = True

        array = self.preprocessed_signal
        mean = np.ma.masked_invalid(array[1:-1]).mean()
        for i in range(1, len(array)):
            if (not np.isinf(array[i]) and not np.isnan(array[i])):  # if the current val is valid
                if start:  # if I had started
                    if greater:
                        if array[i] < mean:
                            indices_crosses_down.append(i)
                    else:
                        if array[i] > mean:
                            indices_crosses_up.append(i)
                start = True
                greater = True if array[i] > mean else False

        status = self._count_respiration_validation(indices_crosses_up)

        return len(indices_crosses_up), len(indices_crosses_down), status

    def _count_respiration_validation(self, indices_crossing, percentage_extreme=0.4):
        """A method to verify the validation of the method count_respirations when the argument 'count' is provided
        to get the breathing rate.


        Parameters
        ----------
        indices_crossing : np.array
            An array with the indices of the array self.preprocessed_signal where the exhalations were detected.
        percentage_extreme : float, optional
            If no exhalations are detected in the start or end segments of length 'percentage_extreme*len(self.preprocessed_signal)',
            the audio count is flagged as invalid.
        Returns
        -------
        boolean
            A boolean that is true only if the results make sense. If there are no exhalations in
            the beggining of the audio or in the last part, the result is False.
        """

        array_length = len(self.preprocessed_signal)
        if len(indices_crossing) == 0:
            return False
        elif indices_crossing[0] > percentage_extreme * array_length:
            return False
        elif indices_crossing[-1] < (1 - percentage_extreme) * array_length:
            return False
        else:
            return True

    def _subsample_audio(self, audio, original_rate: int, desired_rate: int):
        """
        This function subsamples a audio given at some rate to another desired rate

        Parameters
        ----------
        audio :
            The audio file as a list or 1-d array
        original_rate : int
            The original sampling rate of the audio
        desired_rate : int
            The desired sampling rate after the subsampling

        Returns
        -------
        [type]
            Subsampled audio
        """

        secs = len(audio) / original_rate
        samps = int((secs * desired_rate))  # Number of samples to downsample
        intervals = list(map(int, np.linspace(0, len(audio), samps + 1)))

        subsampled_data = []

        for i in range(1, len(intervals)):
            data_slice = audio[intervals[i - 1]:intervals[i]]
            agg_val = np.nanmean(data_slice)
            agg_val = np.ma.masked_invalid(data_slice).mean()
            subsampled_data.append(agg_val)
        return subsampled_data

    def _butter_lowpass(self, cutoff, fs, order=5):
        """
        Computes the coefficients of the filter

        Parameters
        ----------
        cutoff : int
            The desired cutoff frecuency
        fs : int
            The sampling rate of the audio to be filtered
        order : int, optional
            The order of the filter, by default 5

        Returns
        -------
        tuple
            coefficients b and a for the lfilter
        """
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a

    def _butter_lowpass_filter(self, data, cutoff, fs, order=5):
        """
        Applies the butter filter to the data

        Parameters
        ----------
        data : list or np.array 1D
            The audio to be filtered
        cutoff : int
            The desired cutoff frecuency
        fs : int
            The sampling rate of the audio to be filtered
        order : int, optional
            the order of the filter, by default 5

        Returns
        -------
        np.array
            filtered audio
        """
        b, a = self._butter_lowpass(cutoff, fs, order=order)
        y = lfilter(b, a, data)
        return y