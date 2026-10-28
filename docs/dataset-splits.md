# NOVA AI Trainer — Dataset Validation & Stratified Splits

## 1. Split Philosophy

To prevent evaluation bias and data leakage:
1. Every training job records its exact image split manifest in `job_config.json`.
2. No image ever appears in more than one split partition (train, val, or test).
3. Evaluation on the test set is kept strictly separate from validation during training.

## 2. Stratified Partitioning

For single-label image classification, simple random splitting can accidentally leave minority classes underrepresented in the validation set.

The `ClassificationDatasetAdapter` groups valid annotated samples by class label and splits each class independently according to the specified split ratios:

$$\text{Train Count}_c = N_c - \text{Val Count}_c - \text{Test Count}_c$$

Where:
$$\text{Val Count}_c = \max\left(1, \operatorname{round}(N_c \times \text{val\_ratio})\right)$$

This guarantees that:
* Every class has representation in both training and validation sets as long as $N_c \ge 2$.
* Reproducibility is maintained across runs through a configurable random seed (default: `42`).
