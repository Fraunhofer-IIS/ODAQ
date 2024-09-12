"""
An example evaluation pipeline using ODAQ

Please configure this script by changing paths and metrics to be run in config.py
"""

import os
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import pearsonr
import matplotlib.pyplot as plt
import config

from BringYourOwnMetric import calculate_pesq, calculate_sisdr

# ==============================================================
# =================== import your metric here ==================
# ==============================================================
def call_metric(ref_file, test_file):
    """
    To evaluate your own metric, please import your own method here
    :param ref_file: str, filepath to a reference signal
    :param test_file: str, filepath to a test signal
    :return: float, objective quality score
    """

    if config.eval == 'PESQ':
        obj_score = calculate_pesq(ref_file, test_file)
    elif config.eval == 'SI-SDR':
        obj_score = calculate_sisdr(ref_file, test_file)
    else:
        raise ValueError(config.eval + ' does not seem to be implemented!')

    return obj_score
# =============================================================
# ==============================================================
# ==============================================================

def summarize_correlations(df):

    correlation_results = []
    unique_experiments = df['ExperimentName'].unique()

    for experiment_name in unique_experiments:
        df_filtered = df[df['ExperimentName'] == experiment_name]
        df_filtered = df_filtered.dropna(subset=['MeanScore', 'ObjectiveScore'])

        if not df_filtered.empty:
            correlation, _ = pearsonr(df_filtered['MeanScore'], df_filtered['ObjectiveScore'])
            correlation = round(correlation, 3)
        else:
            correlation = float('nan')

        correlation_results.append({
            'ExperimentName': experiment_name,
            'Correlation': correlation
        })

    # compute the mean performance via Z-transform
    all_corr = [result["Correlation"] for result in correlation_results]
    all_z = np.arctanh(np.abs(all_corr))
    avg_corr = np.tanh(np.mean(all_z))
    print("Aggregated correlation = %f" % avg_corr)
    correlation_results.append({
        'ExperimentName': "Aggregated",
        'Correlation': avg_corr
    })
    correlation_df = pd.DataFrame(correlation_results)
    return correlation_df


def plot_scatter_with_correlation(df, experiment_name=None):

    if experiment_name:
        df_filtered = df[df['ExperimentName'] == experiment_name]
        if df_filtered.empty:
            print(f"No data found for ExperimentName: {experiment_name}")
            return
        plot_and_correlate(df_filtered, experiment_name)
    
    else:
        unique_experiments = df['ExperimentName'].unique()
        for exp in unique_experiments:
            df_filtered = df[df['ExperimentName'] == exp]
            plot_and_correlate(df_filtered, exp)
            
def plot_and_correlate(df_filtered, experiment_name):

    df_filtered = df_filtered.dropna(subset=['MeanScore', 'ObjectiveScore'])
    correlation, _ = pearsonr(df_filtered['MeanScore'], df_filtered['ObjectiveScore'])
    
    # Scatter plot
    plt.figure(figsize=(8, 6))
    plt.scatter(df_filtered['MeanScore'], df_filtered['ObjectiveScore'], alpha=0.7)
    plt.title(f'Scatter Plot of MeanScore vs ObjectiveScore for {experiment_name}\nPearson Correlation: {correlation:.2f}')
    plt.xlabel('MeanScore')
    plt.ylabel('ObjectiveScore')
    plt.grid(True)
    plt.legend([f'Pearson Correlation: {correlation:.2f}'], loc='upper left')
    plt.show()

def calculate_objective_score(result_table, folder_path):

    objective_scores = []
    
    for index, row in result_table.iterrows():
        trial_name = row['TrialName']
        file_name = row['FileName']
        
        trial_path = os.path.join(folder_path, trial_name)
        
        # Find the reference file in the subdirectory
        ref_file = None
        test_files = []
        
        for file in os.listdir(trial_path):
            full_path = os.path.join(trial_path, file)
            if os.path.isfile(full_path):
                if "reference" in file.lower():
                    ref_file = full_path
                elif file == file_name and 'lp35' not in file.lower() and 'lp70' not in file.lower():  # ignore anchors
                    test_files.append(full_path)
        
        if ref_file is None:
            print(f"No reference file found in {trial_path}")
            continue
        
        for test_file in test_files:
            score = call_metric(ref_file, test_file)
            # Store the score in the list with the index to align with the pooled_df later
            objective_scores.append((index, score))
    
    return objective_scores

def add_objective_score_to_pooled_df(pooled_df, objective_scores):
    # Initialize with NaN
    pooled_df['ObjectiveScore'] = np.nan
    
    # Update the ObjectiveScore column based on the objective_scores list
    for index, score in objective_scores:
        pooled_df.at[index, 'ObjectiveScore'] = score
    
    return pooled_df

def parseMUSHRAxmlODAQ(folder_paths):

    columns = ['LtType', 'SubjectName', 'TestName', 'StimuliDirectory', 'TrialsPerSession', 
               'TestStatus', 'TrialName', 'TrialSeconds', 'ReferencePlays', 
               'FileName', 'Plays', 'Score']
    result_table = pd.DataFrame(columns=columns)
    
    for f in folder_paths:

        # Get list of all XML files in the specified folder
        xml_files = [f for f in os.listdir(f) if f.endswith('.xml')]
        
        for xml_file in xml_files:
            # Construct the full file name
            file_path = os.path.join(f, xml_file)
            
            # Read and parse the XML file
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Get the root element (MUSHRA)
            MUSHRA = root
            
            # Initialize variables
            LtType = MUSHRA.tag
            info = MUSHRA.find('info')
            
            subject_name = info.get('subjectName')
            test_name = info.get('testName')
            stimuli_directory = info.get('stimuliDirectory')
            trials_per_session = float(info.get('trialsPerSession'))
            test_status = info.get('testStatus')
            
            trials = MUSHRA.findall('.//trial')
            
            for trial in trials:
                trial_name = trial.get('trialName')
                trial_seconds = float(trial.get('trialSeconds'))
                reference_plays = float(trial.get('referencePlays'))
                
                test_files = trial.findall('testFile')
                
                for test_file in test_files:
                    file_name = test_file.get('fileName')
                    plays = float(test_file.get('plays'))
                    score = float(test_file.get('score'))
                    
                    # Create a new row and add it to the DataFrame
                    new_row = pd.DataFrame([[LtType, subject_name, test_name, stimuli_directory, trials_per_session, 
                                            test_status, trial_name, trial_seconds, reference_plays, 
                                            file_name, plays, score]], columns=columns)
                    result_table = pd.concat([result_table, new_row], ignore_index=True)
    
    # Extract ExperimentName and Condition
    result_table['ExperimentName'] = result_table['TrialName'].str.split('_', expand=True)[0]
    result_table['Condition'] = result_table['FileName'].str.split('.wav', expand=True)[0]
    
    return result_table

def calculate_confidence_interval(data):
    """
    Calculate the 95% confidence interval for a dataset.
    """
    n = len(data)
    mean = np.mean(data)
    stderr = stats.sem(data)
    h = stderr * stats.t.ppf((1 + 0.95) / 2., n-1)  # 95% confidence interval
    return h

def pool_table(dataframe):
    """
    Pools the DataFrame into a new table with calculated mean, confidence interval, and standard deviation.
    """
    pooled_data = []

    grouped = dataframe.groupby(['TrialName', 'Condition'])
    
    for (trial_name, condition), group in grouped:
        lt_type = group['LtType'].iloc[0]
        experiment_name = group['ExperimentName'].iloc[0]
        test_name = group['TestName'].iloc[0]
        stimuli_directory = group['StimuliDirectory'].iloc[0]
        trials_per_session = group['TrialsPerSession'].iloc[0]
        test_status = group['TestStatus'].iloc[0]
        file_name = group['FileName'].iloc[0]

        mean_score = group['Score'].mean()
        score_stddev = group['Score'].std()
        score_confint = calculate_confidence_interval(group['Score'])

        new_row = {
            'LtType': lt_type,
            'ExperimentName': experiment_name,
            'TestName': test_name,
            'StimuliDirectory': stimuli_directory,
            'TrialsPerSession': trials_per_session,
            'TestStatus': test_status,
            'TrialName': trial_name,
            'Condition': condition,
            'FileName': file_name,
            'MeanScore': mean_score,
            'ScoreConfInt': score_confint,
            'ScoreStdDev': score_stddev
        }

        pooled_data.append(new_row)
    
    pooled_df = pd.DataFrame(pooled_data)
    return pooled_df

def check_output_path(output_dir):
    if not os.path.isdir(output_dir):
        print("%s does not exist, creating..." % output_dir)
        os.makedirs(output_dir)


def main():
    # Please change the paths and metrics to be run in config.py
    # To import your own metric, please see call_metric() above!
    out_dir = os.path.join(config.paths['output_dir'], config.eval)
    print("Checking output directory: %s" % out_dir)
    check_output_path(out_dir)

    # Parse result directory to table with listener and experiment data
    print("Parsing LT directory: " + str(config.paths['LT_results_folders']))
    subjective_scores_per_listener = parseMUSHRAxmlODAQ(config.paths['LT_results_folders'])
    filename_subj_per_listener = os.path.join(out_dir, 'subjective_output.csv')
    subjective_scores_per_listener.to_csv(filename_subj_per_listener, index=False) # Write to csv table
    print("Table parsed listener scores has been exported to: " + filename_subj_per_listener)

    # Calculate pooled table for all listeners with LT statistics 
    print("Pooling listener data... ")
    df = pd.read_csv(filename_subj_per_listener)
    mean_subj_scores = pool_table(df)
    filename_mean_subj = os.path.join(out_dir, 'pooled_output.csv')
    mean_subj_scores.to_csv(filename_mean_subj, index=False)
    print("Table with pooled scores has been exported to: " + filename_mean_subj)

    # Calculate objective scores on pooled table
    print("Calculating objective scores... ")
    objective_scores = calculate_objective_score(mean_subj_scores, config.paths['audio_folder'])
    objective_score_table = add_objective_score_to_pooled_df(mean_subj_scores, objective_scores)
    objective_score_table_filename = os.path.join(out_dir, 'pooled_output_with_scores.csv')
    objective_score_table.to_csv(objective_score_table_filename, index=False)
    print("Table with objective scores has been exported to:" + objective_score_table_filename)

    # Summarizing correlation values for each experiment name
    correlation_table_filename = os.path.join(out_dir, 'summarized_table.csv')
    correlation_table = summarize_correlations(objective_score_table)
    correlation_table.to_csv(correlation_table_filename, index=False)
    print("Table with summarized correlation scores has been exported to: " + correlation_table_filename)

    # Plot subjective and objective score correlation
    plot_scatter_with_correlation(objective_score_table)


if __name__ == "__main__":
    main()
