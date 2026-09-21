"""Transparent Python port of the inspected tracked-MU MATLAB workflow.

No original script is executed and no source directory is written.
See the notebook and INPUTS.md for interpretation and input requirements.
"""
from pathlib import Path
from dataclasses import dataclass
import re
import numpy as np
import pandas as pd
import h5py
from scipy import signal, ndimage
from scipy.linalg import svd

TASKS = ('index', 'middle', 'index-middle')
LOCATIONS = {'wrist': 'wrist_muedit_new', 'forearm': 'forearm_muedit_new'}
RIDGE = 1e-6


@dataclass
class Recording:
    path: Path
    subject: str
    location: str
    angle: int
    task: str
    fs: float
    n_samples: int
    n_mu: int
    times: list


def read_recording(path, metadata_only=False):
    path = Path(path)
    match = re.search(r'(sub\d+)_staircase_flx_1_(.*?)_15MVC_(wrist|forearm)_decomp_(\d+)deg', path.name)
    if not match:
        raise ValueError(f'Unrecognized file identity: {path}')
    subject, task, location, angle = match.groups()
    if task not in TASKS:
        raise ValueError(f'Unexpected task: {task}')
    if not h5py.is_hdf5(path):
        raise ValueError(f'{path}: this reader expects the verified MATLAB v7.3 format. Convert a copy with MATLAB save -v7.3.')
    with h5py.File(path, 'r') as f:
        fs = next((float(f[k][()].squeeze()) for k in ['signal/fs', 'signal/fsamp']
                   if k in f and np.isfinite(f[k][()].squeeze())), np.nan)
        if not np.isfinite(fs) or fs <= 0:
            raise ValueError(f'Missing sampling rate: {path}')
        pulse = f[f['edition/Pulsetrainclean'][0, 0]]
        n_samples, n_mu = pulse.shape  # MATLAB dimensions are reversed in HDF5.
        times = []
        if not metadata_only:
            refs = f[f['edition/Distimeclean'][0, 0]][()].ravel()
            for mu in range(n_mu):
                d = f[refs[mu]] if mu < len(refs) else None
                # MATLAB encodes empty matrices with a MATLAB_empty attribute.
                a = np.array([]) if d is None or d.attrs.get('MATLAB_empty', 0) else d[()].ravel()
                a = a[np.isfinite(a)]
                # MATLAB round ties away from zero; indices are one-based.
                idx = np.unique((np.sign(a) * np.floor(np.abs(a) + .5)).astype(int))
                times.append(idx[(idx >= 1) & (idx <= n_samples)] - 1)
    return Recording(path, subject, location, int(angle), task, fs, n_samples, n_mu, times)


def inventory(data_root, subjects=('sub1', 'sub2'), angles=(0, 10, 20, 30, 40)):
    rows = []
    for location, directory in LOCATIONS.items():
        for subject in subjects:
            for p in sorted((Path(data_root) / directory / subject).glob('*muedit.mat_edited.mat')):
                r = read_recording(p, metadata_only=True)
                if r.angle not in angles:
                    continue
                if (r.subject, r.location) != (subject, location):
                    raise ValueError(f'Folder/file identity mismatch: {p}')
                rows.append(dict(subject=r.subject, location=r.location, angle=r.angle,
                                 task=r.task, fs=r.fs, n_samples=r.n_samples, n_mu=r.n_mu, path=str(p)))
    df = pd.DataFrame(rows)
    expected = len(subjects) * len(LOCATIONS) * len(angles) * len(TASKS)
    if len(df) != expected or df.duplicated(['subject', 'location', 'angle', 'task']).any():
        raise ValueError(f'Expected {expected} unique recordings, found {len(df)}. Check missing/duplicate files.')
    if df.fs.nunique() != 1:
        raise ValueError('Native row matching requires equal sampling rates; do not crop mixed rates blindly.')
    return df


def binary_spikes(recording):
    spikes = np.zeros((recording.n_samples, recording.n_mu))
    for mu, indices in enumerate(recording.times):
        spikes[indices, mu] = 1
    return spikes


def preprocess(recording, mode='tracked_hann'):
    spikes = binary_spikes(recording)
    fs = recording.fs
    if mode == 'legacy_isomap_gaussian':
        smooth = ndimage.gaussian_filter1d(spikes, sigma=max(1., .1 * fs), axis=0,
                                          mode='constant', truncate=3.) * fs
        return dict(spikes=spikes, smooth=smooth, highpass=smooth.copy(), rate=smooth.copy())
    if mode != 'tracked_hann':
        raise ValueError(mode)
    length = max(3, int(np.floor(.4 * fs + .5)))
    kernel = signal.windows.hann(length, sym=False)
    kernel /= kernel.sum()
    # MATLAB conv2(...,'same') starts at floor(kernel_length/2), also for even lengths.
    full = signal.convolve(spikes, kernel[:, None], mode='full', method='direct')
    smooth = full[length // 2:length // 2 + recording.n_samples] * fs
    b, a = signal.butter(2, .75 / (fs / 2), btype='highpass')
    padlen = 3 * (max(len(a), len(b)) - 1)
    highpass = signal.filtfilt(b, a, smooth, axis=0, padtype='odd', padlen=padlen)
    span = np.ptp(highpass, axis=0)
    span[span == 0] = 1
    rate = (highpass - highpass.min(axis=0)) / span
    if not np.isfinite(rate).all():
        raise ValueError(f'Non-finite rates in {recording.path}')
    return dict(spikes=spikes, smooth=smooth, highpass=highpass, rate=rate)


def read_dictionary(dictionary_root, key, recordings):
    subject, location, angle = key
    path = Path(dictionary_root) / f'unique_mu_dictionary_{subject}_{location}_{angle}deg.csv'
    df = pd.read_csv(path)
    required = {'unique_mu', 'task', 'mu_index0'}
    if df.empty or not required.issubset(df.columns):
        raise ValueError(f'Invalid dictionary: {path}')
    if df[['unique_mu', 'task', 'mu_index0']].isna().any().any():
        raise ValueError(f'Missing MU identity: {path}')
    if df.duplicated(['unique_mu', 'task']).any() or df.duplicated(['task', 'mu_index0']).any():
        raise ValueError(f'Duplicate task-MU membership: {path}')
    for task in TASKS:
        rows = df[df.task == task]
        indices = rows.mu_index0.to_numpy()
        if len(indices) == 0 or not np.all(indices == np.floor(indices)):
            raise ValueError(f'Empty task/noninteger MU indices: {path}, {task}')
        if np.any(indices < 0) or np.any(indices >= recordings[task].n_mu):
            raise ValueError(f'Out-of-range MU indices: {path}, {task}')
    if set(df.task) != set(TASKS):
        raise ValueError(f'Unexpected task in {path}')
    for column, value in [('subject', subject), ('location', location), ('angle_deg', angle)]:
        if column in df and not df[column].eq(value).all():
            raise ValueError(f'Dictionary identity mismatch: {path}')
    return df


def phase_resample(x, n=200):
    old, new = np.linspace(0, 1, len(x)), np.linspace(0, 1, n)
    return np.column_stack([np.interp(new, old, x[:, j]) for j in range(x.shape[1])])


def load_features(manifest, dictionary_root, key, crop_counts, mode='tracked_hann'):
    subject, location, angle = key
    rows = manifest[(manifest.subject == subject) & (manifest.location == location) & (manifest.angle == angle)]
    if len(rows) != 3:
        raise ValueError(f'Expected three tasks for {key}')
    recordings = {row.task: read_recording(row.path) for row in rows.itertuples()}
    stages = {task: preprocess(recordings[task], mode=mode) for task in TASKS}
    dictionary = read_dictionary(dictionary_root, key, recordings)
    labels = list(pd.unique(dictionary.unique_mu))
    blocks, ys = [], []
    for i, task in enumerate(TASKS, 1):
        rate = stages[task]['rate']
        if mode == 'legacy_isomap_gaussian':
            rate = phase_resample(rate, 200)  # Full recording, before stacking, as in original Python.
        else:
            rate = rate[:int(crop_counts[task])]
            if len(rate) != crop_counts[task]:
                raise ValueError(f'Cannot crop {key}/{task} to {crop_counts[task]}')
        block = np.zeros((len(rate), len(labels)))
        for row in dictionary[dictionary.task == task].itertuples():
            block[:, labels.index(row.unique_mu)] = rate[:, int(row.mu_index0)]
        blocks.append(block)
        ys.append(np.full(len(block), i, dtype=int))
    return dict(key=tuple(key), F=np.vstack(blocks), y=np.concatenate(ys), labels=labels,
                dictionary=dictionary, recordings=recordings, stages=stages)


def pca_fit(F):
    F = np.asarray(F, dtype=float)
    mean = F.mean(axis=0)
    u, s, vt = svd(F - mean, full_matrices=False)
    if s[0] <= 0:
        raise ValueError('PCA needs nonconstant data')
    explained = 100 * s ** 2 / np.sum(s ** 2)
    k90 = min(len(s), int(np.searchsorted(np.cumsum(explained), 90) + 1))
    dims = max(3, k90)
    scores = u * s
    X = np.pad(scores[:, :dims], ((0, 0), (0, max(0, dims - scores.shape[1]))))
    return dict(X=X, mean=mean, coeff=vt.T, explained=explained, k90=k90)


def invsqrt(S):
    d, v = np.linalg.eigh((S + S.T) / 2)
    return (v * (1 / np.sqrt(np.maximum(d, np.finfo(float).eps)))) @ v.T


def cca_fit(source, target, ridge=RIDGE):
    if source.shape[0] != target.shape[0]:
        raise ValueError('CCA requires paired rows')
    sm, tm = source.mean(axis=0), target.mean(axis=0)
    S, T = source - sm, target - tm
    n = max(1, len(S) - 1)
    ws = invsqrt(S.T @ S / n + ridge * np.eye(S.shape[1]))
    wt = invsqrt(T.T @ T / n + ridge * np.eye(T.shape[1]))
    u, r, vt = svd(wt @ (T.T @ S / n) @ ws, full_matrices=False)
    A, B = wt @ u, ws @ vt.T
    source_can = S @ B
    cm, sd = source_can.mean(axis=0), source_can.std(axis=0, ddof=1)
    sd[sd == 0] = 1
    return dict(A=A, B=B, r=np.clip(r, 0, 1), sm=sm, tm=tm, cm=cm, sd=sd)


def cca_transform(mapping, source, target):
    m = mapping
    source_can = ((source - m['sm']) @ m['B'] - m['cm']) / m['sd']
    # Original MATLAB maps target U through diag(r), then source standardization.
    target_can = (((target - m['tm']) @ m['A']) * m['r'] - m['cm']) / m['sd']
    return source_can, target_can


def lda_fit(X, y, ridge=RIDGE):
    classes = np.unique(y)
    centroids = np.array([X[y == c].mean(axis=0) for c in classes])
    priors = np.array([np.mean(y == c) for c in classes])
    covariance = np.zeros((X.shape[1], X.shape[1]))
    for c, centroid in zip(classes, centroids):
        residual = X[y == c] - centroid
        covariance += residual.T @ residual
    covariance /= max(1, len(y) - len(classes))
    inverse = np.linalg.pinv(covariance + ridge * np.eye(X.shape[1]))
    weights = inverse @ centroids.T
    offset = -.5 * np.sum(centroids.T * weights, axis=0) + np.log(priors + np.finfo(float).eps)
    return classes, weights, offset


def lda_predict(model, X):
    classes, weights, offset = model
    return classes[np.argmax(X @ weights + offset, axis=1)]


def transfer(source, target, y, use_cca=True, n_modes=None, train=None, test=None):
    train = np.arange(len(y)) if train is None else np.asarray(train)
    test = np.arange(len(y)) if test is None else np.asarray(test)
    mapping = None
    if use_cca:
        mapping = cca_fit(source[train], target[train])
        S, _ = cca_transform(mapping, source[train], target[train])
        _, T = cca_transform(mapping, source[test], target[test])
    else:
        dims = min(source.shape[1], target.shape[1])
        S, T = source[train, :dims], target[test, :dims]
    if n_modes is not None:
        S, T = S[:, :n_modes], T[:, :n_modes]
    prediction = lda_predict(lda_fit(S, y[train]), T)
    return dict(accuracy=float(np.mean(prediction == y[test])), prediction=prediction,
                meanTop3CCA=float(np.mean(mapping['r'][:3])) if mapping else np.nan,
                mapping=mapping)


def original_folds(y, n_folds=5):
    folds = np.zeros(len(y), dtype=int)
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        # MATLAB uses one-based global row indices in its deterministic permutation.
        ordered = idx[np.argsort(((idx + 1) * 1103515245 + 12345) % (2 ** 31), kind='stable')]
        folds[ordered] = np.arange(len(ordered)) % n_folds
    return folds


def legacy_cv(source, target, y, use_cca=True):
    folds = original_folds(y)
    return np.mean([transfer(source, target, y, use_cca, train=np.flatnonzero(folds != f),
                             test=np.flatnonzero(folds == f))['accuracy'] for f in range(5)])


def block_shuffle(F, y, rng, fraction=.1):
    out, records = F.copy(), []
    for c in np.unique(y):
        rows = np.flatnonzero(y == c)
        size = max(1, int(np.floor(len(rows) * fraction)))
        n = len(rows) // size
        perm = rng.permutation(n)
        take = np.concatenate([rows[p * size:(p + 1) * size] for p in perm])
        out[rows[:n * size]] = F[take]
        records.append(dict(task=TASKS[c - 1], block_samples=size, n_blocks=n,
                            tail_samples=len(rows) - n * size, permutation=perm.tolist()))
    return out, records


def task_pair_matrix(source, target, y):
    count = min(np.sum(y == c) for c in np.unique(y))
    matrix = np.zeros((3, 3))
    for i in range(3):
        S = source[np.flatnonzero(y == i + 1)[:count]]
        for j in range(3):
            T = target[np.flatnonzero(y == j + 1)[:count]]
            matrix[i, j] = np.mean(cca_fit(S, T)['r'][:3])
    return matrix


def load_saved_dataset(mat_path, key):
    with h5py.File(mat_path, 'r') as f:
        group = f['datasets']
        def get(name, i):
            return f[group[name][()].ravel()[i]][()].T
        def string(name, i):
            return ''.join(chr(int(v)) for v in get(name, i).ravel())
        for i in range(group['angle'].size):
            identity = string('subject', i), string('location', i), int(get('angle', i).item())
            if identity == tuple(key):
                return {name: get(name, i) for name in ['features', 'X', 'coeff', 'explained', 'y']}
    raise KeyError(key)


def compare_saved(features, pca, saved):
    reference = saved['features']
    if reference.shape != features['F'].shape:
        raise ValueError(f'Feature shape differs: {features["F"].shape} vs {reference.shape}')
    if not np.array_equal(features['y'], saved['y'].ravel()):
        raise ValueError('Saved task labels differ')
    n = pca['X'].shape[1]
    if saved['X'].shape[1] != n:
        raise ValueError('Retained PCA dimensions differ')
    # Signs are arbitrary. Used for comparison only; never used to tune target alignment.
    signs = np.sign(np.sum(pca['coeff'][:, :n] * saved['coeff'][:, :n], axis=0))
    signs[signs == 0] = 1
    return dict(feature_max_abs_error=float(np.max(np.abs(features['F'] - reference))),
                variance_max_abs_error=float(np.max(np.abs(pca['explained'] - saved['explained'].ravel()))),
                sign_adjusted_score_max_abs_error=float(np.max(np.abs(pca['X'] * signs - saved['X']))),
                pca_signs=signs.tolist())
