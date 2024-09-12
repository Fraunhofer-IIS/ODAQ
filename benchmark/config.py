"""
A configuration file to control paths and objective metrics to be run.
"""
# objective metric to be run
# eval = 'PESQ'
eval = 'SI-SDR'


paths = dict(
    # path to the main ODAQ_listening_test folder containing audio files
    audio_folder = './ODAQ/ODAQ_listening_test/',

    # path to the result folders containing the xml files
    LT_results_folders = {'./ODAQ/ODAQ_listening_test/', './ODAQ_v1_BSU/Cohort_B1', './ODAQ_v1_BSU/Cohort_B2'},
    
    # path to an output folder where to store results (it's created if it does not exist)
    output_dir = './output/'
)