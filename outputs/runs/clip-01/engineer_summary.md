# Road conflict screening summary

## Coverage

- Sources: clip-01
- Track observations: 8654
- Road-user observations by group: {'pedestrian': 285, 'vehicle': 8369}
- Unique road users: 678
- Observed time span: 20.26 seconds
- Candidate events: 0

## Ranked hotspots

No candidate events were observed in the supplied tracks.

## Conflict patterns

No candidate conflict patterns were observed.

## Validation summary

- Seed/reference event count: 0
- video: recall None; spurious events 0
- SUMO SSM encounters available: 0
- TTC/PET agreement summary: {'TTC': None, 'PET': None}

## Engineering review prompts

Review crossing visibility, signal phasing, refuge provision, and approach-speed management where the mapped data and local context support it.


## Method and limitations

TTC is estimated from observed positions using a short constant-velocity prediction and buffered road-user footprints. Results are screening indicators for engineering review, not crash probabilities or legal findings.

Coordinates are assumed to be calibrated metres in one shared road-plane coordinate system. Hotspots are metric grid cells and are not yet snapped to road segments. Data gaps, detector errors, and incomplete observation coverage can hide conflicts; ‘none observed’ does not mean a location is safe.
Threshold defaults are TTC < 3 s, PET < 2 s, and DRAC > 3 m/s², following [SUMO SSM defaults](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html). Treat these as configurable screening values, not universal cutoffs.
