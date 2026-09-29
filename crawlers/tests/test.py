import pandas as pd

file = pd.read_csv('./data/ats_career_page_urls.csv')

sample_sizes = {
    "Greenhouse": 20,
    "Ashby": 20,
    "Lever": 10,
}

parts = []

for provider,n in sample_sizes.items():
    subset = file[file["ats_platform"] == provider].sample(
        n=min(n, len(file[file["ats_platform"] == provider])),
        random_state=42
    )

    parts.append(subset)

starter = pd.concat(parts, ignore_index=True)


starter.to_csv("starter_sources.csv", index=False)

print(starter)
print(starter["ats_platform"].value_counts())