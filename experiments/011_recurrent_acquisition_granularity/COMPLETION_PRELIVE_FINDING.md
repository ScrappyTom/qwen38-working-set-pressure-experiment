# Experiment 011 completion supplement prelive finding

## Disposition

The one-cell completion supplement is mechanically qualified and ready for exact owner authorization. No model, endpoint, GPU, or server activity occurred during preparation.

## Frozen identities

- Prior partial response seal: `39d58e0b55c949609ad4c33ad0034219fdf7f35352fda29f4f043d4eb8f75d96`.
- Prior partial aggregate: `2a8151a7e00410d37e57c1cf3fd4a9717eb009dffef55c8eff0d5cac152b2008`.
- Completion executable closure: `4fcc51fed2322dc683213505c7596eab286a881438e49b9563084d847f0bd045`, 26 files.
- Bank: `E7BANK-5f8c1c1f65d87406492a60309def12553297642a5885d1009c8924eaf4e57949`.
- Package: `E11PKG-026094deade0c03fd028e3a921634563b104c416cda12b6b31fda2a67a945736`.
- Missing cell: ordinal 4, `E11-OBS-KAPPA`, seed 223607.
- Frozen branch order: `T25-L0`, then `T25-L1`.
- Output root: `C:\e11-completion`.
- Dedicated port: 18114.

## Qualification

Both L0 and L1 were executed mechanically through the full two-boundary KAPPA/223607 path. Each scripted path reached the known-good terminal candidate and passed hidden grading. The first and second 25k boundaries were authentic, the execution package reproduced, the prior partial seal verified file by file, and the new output root remained absent.

The project test suite contains 41 tests after adding the completion-boundary regression; the recurrent subset passes 14/14.

## Lifecycle hardening

The exact launcher starts the Python runner as a hidden detached Windows process and writes independent stdout, stderr, and PID custody outside the experiment output root. The model-facing runner and all imported project Python sources remain frozen by the executable closure. The launcher source is separately hash-bound by the authorization.

The runner catches `BaseException` when Python receives a catchable interruption. A non-catchable external process kill can still exist in principle, but the detached process no longer shares the interactive command session's lifetime.

## Scope

The authorization may permit exactly one new shared prefix and the two missing branches. It does not resume the old prefix, rerun cells 1–3, rewrite prior evidence, or authorize an automatic successor.
