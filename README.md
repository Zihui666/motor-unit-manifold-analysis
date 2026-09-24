# Motor-unit manifold analysis

Two self-contained Jupyter notebooks for tracked-MU PCA90, global CCA alignment and whole-space controls.
All instructions, plots and tables are in English.

| File | Purpose |
| --- | --- |
| [PCA90_Alignment_Controls.ipynb](PCA90_Alignment_Controls.ipynb) | Run the analysis on your own recordings. All code and input requirements are inside the notebook. Paths and outputs are blank. |
| [PCA90_Alignment_Controls_Example.ipynb](PCA90_Alignment_Controls_Example.ipynb) | View a completed run on real recordings, including PCA90/CCA tables and six comparison figures. The original inputs are not included. |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Excludes common local data and output files |

## View the real-data example

Open the example notebook to view its saved tables and images. These results were computed from real
recordings; they are not synthetic. Only aggregate result tables and raster plots are embedded.
The example contains no raw EMG, individual MU discharge events or traces, tracking dictionary entries,
activity matrices, latent-coordinate arrays, or fitted model arrays. Dataset labels are generic and all paths are blank.

Viewing requires no inputs. Rerunning requires your own compatible inputs; the private configuration and
original recordings used to produce the displayed results are not distributed.

## Run on your data

```sh
python -m pip install -r requirements.txt
python -m jupyterlab PCA90_Alignment_Controls.ipynb
```

In Module 1, fill in `DATA_ROOT` and `DICTIONARY_ROOT`, then set `SUBJECTS`, `ANGLES`, `SOURCE` and
`TARGET`. The supplied `sub1` and `sub2` values are placeholders. Both notebooks contain all required
Python functions; no separate helper script is needed. Python 3.13 was used for the verified run.

Input requirements and a directory/CSV example are included in Module 1:

- Edited MATLAB v7.3/HDF5 recordings containing `signal.fs` or `signal.fsamp`, `edition.Pulsetrainclean{1}`
  and `edition.Distimeclean{1}`. Discharge events must be one-based sample indices. The first grid is used.
- One existing tracking dictionary per subject, location and angle, with `unique_mu`, `task`, and
  `mu_index0`. `mu_index0` is the zero-based row in the edited recording. Tracking must be supplied;
  the notebook does not infer MU matches.

## Modules and outputs

1. Configure inputs and the comparison.
2. Preprocess discharge events, assemble shared MU identities, and calculate the PCA90 table.
3. Define task colors and source/target trajectory conventions.
4. Compare the pooled latent spaces before and after global CCA, with canonical correlation tables.
5. Compare observed and temporal-block-shuffled activity in 2D/3D.
6. Compare correct and incorrect task correspondences using one global CCA per pooled comparison.
7. Finish inline or optionally export summary tables and figures.

There is no downsampling or phase interpolation before PCA. Task-specific native-length cropping precedes
stacking. The dictionary places tracked appearances in the same MU column before PCA; missing memberships
are zero-filled. PCA retains at least three dimensions for alignment, while the PCA90 table reports the
minimum dimension explaining at least 90% variance.

The wrong-task control keeps the pooled PCA spaces fixed, fits each correspondence on the same matched-length
sample sets across all three tasks, and projects the full original trajectories. Plot colors retain true task
identity. High canonical correlation under an incorrect pairing does not establish correct task alignment.
Reported correlations describe the fitted data, not held-out generalization.

`SAVE_OUTPUTS = False` keeps results inline; optional PNG/CSV exports require an explicit `OUTPUT_DIR`.
Jupyter may save displayed results inside the notebook. Before sharing a new run, clear any outputs or paths
you do not intend to publish. No raw data exports are implemented in these notebooks.
