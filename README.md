# Motor-unit manifold analysis

Jupyter notebooks for tracked motor-unit PCA90, global canonical correlation analysis (CCA), and visual alignment controls.

| Notebook | Function |
| --- | --- |
| [PCA90_Alignment_Controls.ipynb](PCA90_Alignment_Controls.ipynb) | Run preprocessing, PCA, alignment and controls on your recordings. |
| [PCA90_Alignment_Controls_Example.ipynb](PCA90_Alignment_Controls_Example.ipynb) | View a completed real-data analysis with PCA90 and CCA tables and six comparison figures. |

## Getting started

```sh
python -m pip install -r requirements.txt
python -m jupyterlab PCA90_Alignment_Controls.ipynb
```

In Module 1, enter `DATA_ROOT` and `DICTIONARY_ROOT`, then configure `SUBJECTS`, `ANGLES`, `SOURCE` and `TARGET`. Run the cells from top to bottom. Both notebooks contain all required analysis functions.

## Inputs

- **Edited recordings:** MATLAB v7.3/HDF5 files containing `signal.fs` or `signal.fsamp`, `edition.Pulsetrainclean{1}` and `edition.Distimeclean{1}`. Discharge events use one-based sample indices. The reader uses the first grid.
- **MU tracking dictionaries:** one CSV per subject, location and angle, containing `unique_mu`, `task` and `mu_index0`. The index is the zero-based MU row in the edited recording.

Module 1 includes the directory layout, filename pattern and dictionary format.

## Modules

| Module | Function |
| --- | --- |
| 1. Configuration | Select inputs, conditions and the source–target comparison. |
| 2. Preprocessing and PCA | Smooth discharge activity, filter and normalize signals, assemble shared MU columns, and calculate PCA90. |
| 3. Plotting conventions | Assign task colors and source/target line styles. |
| 4. Global CCA | Align the pooled latent spaces and display before/after trajectories and canonical correlations. |
| 5. Temporal-block control | Shuffle time blocks within tasks, refit PCA and CCA, and compare the results. |
| 6. Task-correspondence control | Compare correct and incorrect task pairings using one global CCA per pooled comparison. |
| 7. Results | Display tables and figures, with optional PNG/CSV export. |

## Analysis outputs

**PCA90:** the number of principal components explaining at least 90% of variance, with the retained alignment dimension shown separately. Tracked appearances of the same MU occupy one feature column before PCA; missing task memberships are zero-filled.

**Alignment:** 2D and 3D trajectory comparisons, canonical correlations for every fitted mode, and their top-three mean. Colors identify tasks; solid and dashed lines distinguish source and target.

**Controls:** observed versus temporal-block-shuffled activity, and correct versus incorrect task correspondence. The task-correspondence control keeps the pooled PCA spaces fixed, fits each global alignment on matched-length sample sets across all three tasks, and projects the complete trajectories while retaining true task colors.

Results appear inline. To export figures and summary tables, set `SAVE_OUTPUTS = True` and specify `OUTPUT_DIR`.
