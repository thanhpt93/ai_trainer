# NOVA AI Trainer — Training Configuration & Hyperparameters

## 1. Hyperparameter Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `model_architecture` | string | `resnet18` | Backbone architecture from Model Catalog (`resnet18`, `mobilenet_v3_small`, `resnet50`, etc.). |
| `pretrained` | boolean | `true` | When true, loads ImageNet pretrained weights and replaces the classification head. |
| `device` | string | `auto` | Training hardware target: `auto`, `cuda`, or `cpu`. |
| `input_size` | integer | `224` | Input image resolution (width & height in pixels). |
| `batch_size` | integer | `16` | Number of image samples per optimization step. |
| `epochs` | integer | `10` | Maximum number of training epochs to execute. |
| `learning_rate` | float | `0.001` | Initial optimizer learning rate. |
| `optimizer` | string | `AdamW` | Gradient optimization algorithm (`AdamW` or `SGD`). |
| `weight_decay` | float | `0.0001` | L2 regularization penalty on network weights. |
| `momentum` | float | `0.9` | Momentum factor for SGD optimizer. |
| `scheduler` | string | `step` | Learning rate schedule policy: `step`, `cosine`, or `none`. |
| `early_stopping` | boolean | `false` | Halt training early if validation metric fails to improve. |
| `patience` | integer | `5` | Number of epochs with no improvement before early termination. |

## 2. Data Augmentation Options

* **Random Horizontal Flip**: Flips images horizontally with $p = 0.5$ (enabled by default).
* **Random Rotation**: Applies small random degree rotations (default $\pm 10^\circ$).
* **Color Jitter**: Applies random perturbations to brightness and contrast.
