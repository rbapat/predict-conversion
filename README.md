In order to run this, the following configs need to be created:

- config.yaml
  - `seed`: what seed to initialize all random generators to
- logging/CONFIG_NAME.yaml
  - `ckpt_folder`: the folder where model weights will be stored
  - `result_folder`: the folder where resulting predictions will be stored
  - `log_epochs`: whether or not to print every epoch
- task/TASK.yaml
  - For train tasks:
    - `dataset`
      - `dataset_cfg`
        - `task`: what task we are training for, `DatasetTask` enum
        - `mode`: what mode we are loading data in, `DataMode` enum
        - `split_type`: what type of data splits we are training with, `SplitTypes` class
        - `scan_paths`: path to MRI scans
        - `embedding_paths`: _optional_ path to embeddings. Not always needed, but will throw and exception if needed and doesn't exist
        - `batch_size`: batch size to load data in
        - `cohorts`: optional list of cohorts to use in classification task (CN, MCI, Dementia). Defaults to all if not included
        - `ni_vars`: optional list of nonimaging variables to use for training, defaults to none
        - `load_embeddings`: whether or not we should load embeddings for longitudinal task. If false, MRI scans will be loaded
        - `num_seq_visits`: number of sequential visits that we search for in the longitudinal task
        - `seq_visit_delta`: number of months between sequential visits that we search for in longitudinal task
        - `progression_window`: how many months after baseline visit that we look for conversions for in longitudinal task
        - `tolerance`: how many months plus/minus the `baseline_visit + progression_window` we consider for conversions
    - `train_cfg`
      - `model_cls`: type of model to create for training
      - `model_weights`: _optional_ path to pre-trained model weights
      - `optim`: optimizer to use for training
      - `loss_function`: criterion used for training
      - `num_epochs`: number of epochs to train for
    - `model`
      - `...` whatever model parameters you need
