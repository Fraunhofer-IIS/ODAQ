# ODAQ Figures

This folder contains figures related to the ODAQ dataset.

## results_overview.png

This figure provides an overview of the quality scores contained in the ODAQ dataset, showing the distribution of Basic Audio Quality (BAQ) ratings across different processing methods and quality levels.

### How to Reproduce

The ODAQ package contains raw results from the listening test stored as `.xml` files (as output by [the listening test app](https://github.com/Netflix-Skunkworks/listening-test-app)). For convenience, the raw results are also aggregated in `ODAQ_results.csv`.

To reproduce a version of this figure, use the following Python code:

```python
import pandas
import seaborn
import matplotlib.pyplot as plt

# Load the ODAQ results
# Adjust the path to point to your local ODAQ download
ODAQ_results = pandas.read_csv('./ODAQ/ODAQ_listening_test/ODAQ_results.csv')

# Create the plot
seaborn.pointplot(
    data=ODAQ_results, 
    x='condition', 
    y='score', 
    hue='method', 
    linestyle='none', 
    dodge=True, 
    capsize=.1
)
plt.grid()
plt.title('ODAQ')
plt.xlabel('Quality Levels')
plt.ylabel('BAQ [MUSHRA points]')
plt.tight_layout()
plt.savefig('results_overview.png', dpi=150)
plt.show()
```

### Requirements

```
pandas
seaborn
matplotlib
```

### Notes

- The figure shows results from the initial ODAQ release (2024-icassp)
- Each point represents the mean score across all listeners for a given method and quality level
- Error bars indicate the 95% confidence interval
- For more detailed analysis and additional visualizations, see the [benchmark](../benchmark/) subfolder
