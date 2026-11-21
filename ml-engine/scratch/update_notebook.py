"""
Script to update 01_merge_request_risk_analysis.ipynb with complete Phase 2-8 analysis.
"""
import json
from pathlib import Path

notebook_path = Path("/Volumes/nvme/projects/ml-projects/mergeguard-ai/ml-engine/01_merge_request_risk_analysis.ipynb")
with open(notebook_path, "r") as f:
    nb = json.load(f)

new_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Phase 2: Target Variable Distribution & Investigation\n",
            "\n",
            "We analyze the distribution of `buggy` across the training, test, and total datasets to identify class imbalance and dataset construction characteristics."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "print('--- Training Set Target Distribution ---')\n",
            "print(train_df['buggy'].value_counts())\n",
            "print(train_df['buggy'].value_counts(normalize=True) * 100)\n",
            "\n",
            "print('\\n--- Test Set Target Distribution (Temporal Real-World) ---')\n",
            "print(test_df['buggy'].value_counts())\n",
            "print(test_df['buggy'].value_counts(normalize=True) * 100)\n",
            "\n",
            "print('\\n--- Total Dataset Target Distribution ---')\n",
            "print(total_df['buggy'].value_counts())\n",
            "print(total_df['buggy'].value_counts(normalize=True) * 100)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Investigation of the `fix` Column\n",
            "`fix` indicates whether a commit was identified as fixing a bug (via Jira mining).\n",
            "Notice how many commits that fixed a bug ALSO introduced another bug (regression defects)!"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "print('Fix column distribution in train_df:')\n",
            "print(train_df['fix'].value_counts())\n",
            "\n",
            "print('\\nCrosstab: Buggy vs Fix (Train):')\n",
            "print(pd.crosstab(train_df['buggy'], train_df['fix'], margins=True))\n",
            "\n",
            "# Why we exclude 'fix' from features: in clean commits, fix was filled with False by definition,\n",
            "# and in real-time PR review, whether a PR fixes a bug is not consistently known without external linking."
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Phase 3: Exploratory Data Analysis (EDA)\n",
            "\n",
            "We explore numeric distributions, correlations, and how churn relates to defect risk."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "\n",
            "# Target distribution visualization\n",
            "fig, axes = plt.subplots(1, 2, figsize=(12, 4))\n",
            "train_df['buggy'].value_counts().plot(kind='bar', ax=axes[0], color=['#3b82f6', '#ef4444'], title='Train Set: Artificially Balanced (50/50)')\n",
            "axes[0].set_xticklabels(['False', 'True'], rotation=0)\n",
            "axes[0].set_ylabel('Commits')\n",
            "\n",
            "test_df['buggy'].value_counts().plot(kind='bar', ax=axes[1], color=['#3b82f6', '#ef4444'], title='Test Set: Real-World Distribution (~19% Buggy)')\n",
            "axes[1].set_xticklabels(['False', 'True'], rotation=0)\n",
            "axes[1].set_ylabel('Commits')\n",
            "plt.tight_layout()\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Churn vs Buggy status (Log-scale to handle skew)\n",
            "train_df['total_churn'] = train_df['la'] + train_df['ld']\n",
            "\n",
            "plt.figure(figsize=(8, 4))\n",
            "sns.boxplot(x='buggy', y=np.log1p(train_df['total_churn']), data=train_df, palette='Set2')\n",
            "plt.title('Log(Total Churn) by Buggy Status')\n",
            "plt.xlabel('Buggy Commit')\n",
            "plt.ylabel('log1p(la + ld)')\n",
            "plt.show()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## Phase 4 & 6-8: Training Baseline & Advanced Models via MergeGuard Pipeline\n",
            "\n",
            "We run our reproducible training pipeline and inspect benchmark results."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "from src.train import run_training_pipeline\n",
            "results = run_training_pipeline()"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "### Verify Model Predictions & Explainable Risk Scoring\n",
            "\n",
            "Load the serialized model artifact and test sample Merge Requests."
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import joblib\n",
            "from src.risk_engine import RiskEngine\n",
            "\n",
            "artifact = joblib.load('models/mergeguard_model.joblib')\n",
            "engine = RiskEngine(artifact['pipeline'], artifact['baseline_means'])\n",
            "\n",
            "# Evaluate an illustrative large PR\n",
            "mr_sample = {\n",
            "    'la': 940, 'ld': 230, 'nf': 28, 'nd': 7, 'ns': 3,\n",
            "    'ent': 3.6, 'ndev': 6, 'age': 120, 'nuc': 30,\n",
            "    'aexp': 50, 'arexp': 40, 'asexp': 3\n",
            "}\n",
            "analysis = engine.analyze(mr_sample, tests_modified=False, critical_modules=True)\n",
            "print(f'Risk Score: {analysis.risk_score}/100 [{analysis.risk_level}]')\n",
            "print(f'Defect Probability: {analysis.defect_probability:.2%}')\n",
            "print('\\nTop Risk Factors:')\n",
            "for f in analysis.top_risk_factors:\n",
            "    print(f\"  - {f['label']}: {f['value']} ({f['description']})\")\n",
            "print('\\nRecommendations:')\n",
            "for r in analysis.recommendations:\n",
            "    print(f'  - {r}')"
        ]
    }
]

nb["cells"].extend(new_cells)
with open(notebook_path, "w") as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully!")
