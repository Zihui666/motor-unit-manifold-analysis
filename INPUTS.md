### Required input files

Fill in `DATA_ROOT` and `DICTIONARY_ROOT` in the configuration cell. Both are intentionally empty in the distributed notebook. Absolute paths or paths relative to the notebook's working directory are accepted. On Windows, use forward slashes or a raw string when entering a path.

#### 1. Edited motor-unit recordings (`DATA_ROOT`)

The input directory must contain the following structure (the subject below is an example):

```text
<DATA_ROOT>/
  wrist_muedit_new/
    sub1/
      sub1_staircase_flx_1_index_15MVC_wrist_decomp_0deg_muedit.mat_edited.mat
      sub1_staircase_flx_1_middle_15MVC_wrist_decomp_0deg_muedit.mat_edited.mat
      sub1_staircase_flx_1_index-middle_15MVC_wrist_decomp_0deg_muedit.mat_edited.mat
      ...
  forearm_muedit_new/
    sub1/
      sub1_staircase_flx_1_index_15MVC_forearm_decomp_0deg_muedit.mat_edited.mat
      ...
```

Use your actual subject names, such as `sub1`, in both the folders and filenames. The current reader expects this naming pattern; task names are exactly `index`, `middle`, and `index-middle`. Angles are nonnegative integers followed by `deg`. Each configured subject and angle needs one recording for each of the three tasks at **both** locations, wrist and forearm.

With the default `SUBJECTS = ('sub1', 'sub2')` and `ANGLES = (0, 10, 20, 30, 40)`, this means **60 recordings and 20 condition dictionaries**. Edit `SUBJECTS`, `ANGLES`, `SOURCE`, and `TARGET` to match your dataset. Source and target must belong to the configured cohort. The current reader always includes both locations.

Files must be **MATLAB v7.3 / HDF5** files with these fields:

| MATLAB field | Required content | Use in this notebook |
| --- | --- | --- |
| `signal.fs` (or `signal.fsamp`) | A finite, positive sampling rate in Hz | Convert discharge events into firing-rate signals; all recordings must have the same sampling rate |
| `edition.Pulsetrainclean{1}` | A two-dimensional matrix, MUs × samples in MATLAB | Determine the number of MUs and samples |
| `edition.Distimeclean{1}` | A cell array with one discharge-event vector per MU, in the same MU order as the pulse matrix | Reconstruct binary spike trains |

Discharge events must be **one-based sample indices**, not times in seconds. Empty event vectors are allowed. The reader uses the **first grid only** (`{1}`), and handles MATLAB/HDF5 dimension reversal internally. Other MAT formats require conversion to v7.3 before loading. Raw EMG, force traces, `edition.time`, MUAP templates, and precomputed PCA or alignment results are not required by this notebook. MATLAB is not needed to run the Python analysis once these inputs are available.

#### 2. Existing MU tracking dictionaries (`DICTIONARY_ROOT`)

Place one CSV per subject, location and angle directly in the dictionary directory:

```text
<DICTIONARY_ROOT>/
  unique_mu_dictionary_sub1_wrist_0deg.csv
  unique_mu_dictionary_sub1_forearm_0deg.csv
  ...
```

Required CSV columns:

| Column | Meaning |
| --- | --- |
| `unique_mu` | Stable MU identity shared by all tracked appearances of that MU across tasks within this condition |
| `task` | Exactly `index`, `middle`, or `index-middle` |
| `mu_index0` | Zero-based MU row index in that task's edited pulse matrix; this must refer to the current edited file |

For example, the following illustrates the schema only; it is not a complete dataset:

```csv
unique_mu,task,mu_index0
UMU001,index,0
UMU001,middle,2
UMU002,index-middle,0
```

Here, row 1 of the Index recording and row 3 of the Middle recording are tracked as the same MU, `UMU001`. Their activity is placed in the **same feature column**, in their respective task time blocks, before PCA. `UMU002` occupies a separate column. If an identity has no entry for a task, that task's block for that column is filled with zero.

The notebook **consumes existing tracking results; it does not perform MU tracking or infer which units match**. Identity scope is one subject × location × angle across the three tasks. Dictionaries do not establish shared identities across subjects, locations or angles.

Every task must have dictionary entries. Required values must be nonempty; indices must be integers within the corresponding recording's MU range. Each `(unique_mu, task)` and each `(task, mu_index0)` combination must be unique. Give untracked MUs distinct identities and include every MU that should participate in PCA: MUs omitted from the dictionary are excluded. If optional `subject`, `location`, or `angle_deg` columns are present, they must match the dictionary filename. Additional tracking-quality columns are allowed but do not affect the analysis.

#### 3. Optional output directory

`SAVE_OUTPUTS = False` and `OUTPUT_DIR = ""` are the defaults. Results appear inline; the analysis does not export separate files or create an output folder. Jupyter may still save the notebook itself and its displayed outputs.

To export results, set `SAVE_OUTPUTS = True` and enter a directory in `OUTPUT_DIR`. The notebook then writes PNG figures, CSV tables, an NPZ audit file and a JSON settings record there. The settings record includes the input paths you configured. Before committing a notebook that you have run locally, clear its outputs and reset its path settings to empty strings if you want to keep the published copy portable.
