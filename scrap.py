import pandas
from cleaning import build_dcm_data_frames

paths_dict = {'dixon': {'inPhase': ['temp\\inPhase(1)'], 'outPhase': ['temp\\outPhase(1)'], 'fat': ['temp\\fat(1)'], 'water': ['temp\\water(1)']}, 'diffusion': {'b50': ['temp\\b50(1)'], 'b600': ['temp\\b600(1)'], 'b900': ['temp\\b900(1)'], 'adc': ['temp\\adc(1)'], 'bvals': []}}

paths_list = []
for g, group in enumerate(paths_dict):
    paths_list.append([])
    for series in paths_dict[group]:
        for item in paths_dict[group][series]:
            paths_list[g].append(item)

output = build_dcm_data_frames(paths_list)


