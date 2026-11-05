# Road conflict screening summary

## Coverage

- Sources: sumo-control-42
- Track observations: 3750
- Road-user observations by group: {'pedestrian': 2020, 'vehicle': 1730}
- Unique road users: 22
- Observed time span: 174.80 seconds
- Candidate events: 3

## Ranked hotspots

1. Metric grid cell (29, 18): 3 candidate event(s); minimum indicator 1.06 s; rate per 1,000 users 136.36363636363637; main pattern other; pair pedestrian / pedestrian; coverage flags none.

## Conflict patterns

- Other: 3

## Validation summary

- Seed/reference event count: 3
- SUMO SSM encounters available: 0
- TTC/PET agreement summary: {'TTC': None, 'PET': None}

## Engineering review prompts

Review crossing visibility, signal phasing, refuge provision, and approach-speed management where the mapped data and local context support it.


## Method and limitations

TTC is estimated from observed positions using a short constant-velocity prediction and buffered road-user footprints. Results are screening indicators for engineering review, not crash probabilities or legal findings.

Coordinates are assumed to be calibrated metres in one shared road-plane coordinate system. Hotspots are metric grid cells and are not yet snapped to road segments. Data gaps, detector errors, and incomplete observation coverage can hide conflicts; ‘none observed’ does not mean a location is safe.
Threshold defaults are TTC < 3 s, PET < 2 s, and DRAC > 3 m/s², following [SUMO SSM defaults](https://sumo.dlr.de/docs/Simulation/Output/SSM_Device.html). Treat these as configurable screening values, not universal cutoffs.
