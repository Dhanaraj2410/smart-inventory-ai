# Machine-learning workflow

The application can use trained model artifacts for stockout-risk and demand
predictions, with rule-based fallbacks for runtime predictions. The training
scripts share feature engineering in `ml/preprocessing/` so training and
prediction use the same feature definitions.

## Generate local sample data

```sh
python ml/data/generate_sample_data.py
```

This writes `sample_products.csv` and `sample_sales.csv` under `ml/data/`.
Those generated CSVs are ignored by Git. The dataset is for local exploration,
not a substitute for a business's historical sales data.

## Train models

For a standalone CSV-based run, generate the sample data first, then invoke:

```sh
python -m ml.training.train_stockout_model
python -m ml.training.train_demand_model
```

For training from the application's database, apply migrations and load or
import sales data, then run:

```sh
python manage.py train_models
```

The management command trains both models and records evaluation metrics in
the database. The scripts compare candidate estimators, save model artifacts
under `ml/models/`, and print the evaluation results. Generated artifacts are
ignored by Git; retrain them in each environment where they are needed.

Use representative, validated sales data before relying on model quality.
Check the model-performance page after training and compare the metrics with
business expectations before deployment.
