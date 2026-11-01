# Superseded bank-isolation implementation and test contracts

These are complete byte-for-byte snapshots taken before the user-authorized
shared-project refactor on 26 October 2026. They are not the current candidate.
The three test snapshots were compared with the live files using SHA-256 before
any test migration; each pair matched:

- test_phase1_safety.py: d0a6299783dbb80dad9c746562ef58a35a5ccab4d160eea11da7f179840d7f24
- test_reaudit_abi.py: 72568c8ed48cafa0c6ca809066016f6b1ae359b922bdbe3693e68118f3c794b7
- test_projects_and_mode.py: cc706d283ac639720663d40951743293dc2dceccf482e3845575c2d775732b1a

The old contracts required separate banks, dirty tracking, deferred Load/Save
callbacks and disabled Load containment. The user removed those requirements.
Current tests must instead require zero project I/O on toggle, unchanged project
bytes and metadata, stock storage/project code, both project pages, stopped/held
guards, sample muting and unchanged MIDI behavior. Existing relevant grid, ABI,
heap, binary transport and MIDI recorder regressions remain active.

Historical successes must not be counted as current candidate acceptance.
