# MergeGuard AI — Technical Interview Handbook

This guide contains core technical interview questions and grounded explanations you can use to defend the engineering decisions behind MergeGuard AI.

---

### Q1: What problem does MergeGuard AI solve, and why Just-In-Time (JIT) defect prediction?
**Answer:**  
*"Traditional software quality tools either perform static analysis (which catches syntax and lint errors but misses semantic logic flaws) or file-level defect prediction (which flags entire files after a release is deployed). By that point, bug triage is costly.*  
*MergeGuard AI implements **Just-In-Time (JIT) defect prediction**, evaluating risk at the exact moment a developer submits a commit or opens a Merge Request. By predicting defect probability based on code churn, entropy, and historical developer familiarity, we provide immediate review interventions while the code context is still fresh in the developer's mind."*

---

### Q2: Why is raw Accuracy a dangerous metric for defect prediction?
**Answer:**  
*"In real-world software development, defects are rare events—in our 3-year test set of 30,111 commits, only 19.3% introduced defects. If a naive model simply predicts 'Not Buggy' 100% of the time, it achieves 80.7% accuracy while missing every single production defect!*  
*Therefore, we rely on **Recall** (catching over 81% of buggy changes), **Precision**, **ROC-AUC** (0.803), and **PR-AUC** (0.500 vs 0.193 baseline), which evaluate the true discriminative power of the classifier on the minority defect class."*

---

### Q3: Why did you use a Temporal Train/Test Split instead of standard Random K-Fold Cross Validation?
**Answer:**  
*"Software repositories evolve over time. If you use random k-fold splitting, commits from 2019 could appear in the training set while commits from 2012 appear in the test set. This creates severe **data leakage** because the model learns from future repository states, author habits, and file architectures that didn't exist when the past commit was written.*  
*To simulate production reality, we strictly trained on 14 years of historical commits (2003–2016) and evaluated on an independent holdout set of the subsequent 3 years (2017–2020)."*

---

### Q4: Why did you exclude the `fix` and `commit_id` columns from the input features?
**Answer:**  
*"1. `commit_id` is an arbitrary SHA hash with high cardinality and zero generalizable predictive signal—a model would only memorize hashes.*  
*2. `fix` was generated during the SZZ dataset construction by matching Jira bug reports. For non-buggy commits, it was synthetically set to False. Furthermore, on arbitrary new Merge Requests, whether a PR is a bug fix isn't consistently verified. Using `fix` directly would introduce synthetic target leakage, so we deliberately excluded it."*

---

### Q5: How does the system compute Change Entropy (`ent`)?
**Answer:**  
*"Change entropy measures how dispersed a modification is across files using Shannon Entropy:*  
$$H = - \sum_{i=1}^{n} p_i \log_2(p_i)$$  
*where $p_i$ is the churn of file $i$ divided by total churn. If 1,000 lines are changed entirely in one file, entropy is $0.0$. If 1,000 lines are split equally across 10 files, entropy is high. Empirical software engineering research shows high entropy commits have higher cognitive complexity and are significantly more prone to regression defects."*

---

### Q6: How do you bridge a commit-level ML model with GitLab Merge Requests?
**Answer:**  
*"A Merge Request is a set of commits and file diffs between two branches. We built a `gitlab_extractor` that parses the unified git diff from the GitLab REST API, calculates additions, deletions, directory distribution, test file modifications, and Shannon entropy, and maps them to our model's feature space. We also explicitly clarify to reviewers that while the model was trained on historical commit data, it acts as an evidence-grounded risk signal for Merge Requests, supplemented by explicit test-modification detection and critical module flags."*
